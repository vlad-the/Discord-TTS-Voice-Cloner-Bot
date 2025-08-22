import discord
from discord.ext import commands
from discord import app_commands
import sys
import os
from discord.ext.voice_recv import VoiceRecvClient, AudioSink
import wave
import AI


#bot setup
class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}')

        try:
            guild = discord.Object(id=1408083190735704124)
            synced = await self.tree.sync(guild=guild)
            print(f'synced {len(synced)} commands to guild {guild.id}!')
        except Exception as e:
            print(f'Error syncing commands: {e}')
    



intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)


GUILD_ID = discord.Object(id=1408083190735704124)

#setting up command for tts
@client.tree.command(name="say", description="Says something in VC", guild=GUILD_ID)
async def enter_voice(interaction: discord.Interaction, say: str):
    if not interaction.user.voice:#check if user is in vc
        return await interaction.response.send_message(
            "You need to be in a voice channel to use this command."
        )

    channel = interaction.user.voice.channel

    await interaction.response.send_message("Generating, please wait...")
    AI.run(say) #generating the audio
    source = discord.FFmpegPCMAudio('.../out.wav')#please give it the same dir as the output in AI.py

    #connecting to vc or changing vc
    vc = interaction.guild.voice_client
    if vc is None:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    # Now play the audio
    if vc.is_playing():
        vc.stop()  # stop current audio if it's playing
    
    vc.play(source, after=lambda e: print(f"Player error: {e}") if e else print('playing'))
    await interaction.followup.send("Now playing")


#setting up command for tts with using a pre recorded clip of someone
@client.tree.command(name="say_with_custom_voice", description="Says somthing in VC with a voice from VC", guild=GUILD_ID)
async def enter_voice(interaction: discord.Interaction, say: str):
    if not interaction.user.voice:
        return await interaction.response.send_message(
            "You need to be in a voice channel to use this command."
        )
    



    #stting up the dropdown menu to select a wav file that has already been recorded
    directory_path = "..." #please put in dir for the recordings in a seprate file

    options = []
    file_names = []
    #gathering all the files in the dir where the recorded audio is saved
    for entry in os.listdir(directory_path):
        full_path = os.path.join(directory_path, entry)
        if os.path.isfile(full_path):
            file_names.append(entry)

    for name in file_names: #putting the file names into a list to be made into a drop down in discord
        options.append(discord.SelectOption(label=name, description=name))

    #menu setup
    class Menu(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="choose an option:", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            self.disabled = True
    
            await interaction.response.edit_message(
                content=f"✅ Selected: **{self.values[0]}**", 
                view=self.view
            )
            #take which file the user selected and send it to the tts with the prompt
            AUDIO_PROMPT_PATH = f'.../{self.values[0]}'#keep the self.values as is and add the recordings dir
            await interaction.followup.send("Generating, please wait...")
            AI.run_with_audio_in(say,AUDIO_PROMPT_PATH) 
            await interaction.followup.send("Now playing")
            #setup for audio playback 
            source = discord.FFmpegPCMAudio('.../out.wav')#keep out.wav as is and add the output from AI.py

            channel = interaction.user.voice.channel

            #connect or swtch vc
            vc = interaction.guild.voice_client
            if vc is None:
                vc = await channel.connect()
            elif vc.channel != channel:
                await vc.move_to(channel)

            # Now play the audio
            if vc.is_playing():
                vc.stop()  # stop current audio if it's playing
            
            vc.play(source, after=lambda e: print(f"Player error: {e}") if e else print('playing'))
    #more menu setup
    class MenuView(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.add_item(Menu())

    await interaction.response.send_message("Select an audio file:", view=MenuView(), ephemeral=True)

#setup command for leaving vc
@client.tree.command(name="leave_vc",description="leaves VC",guild=GUILD_ID)
async def leave(interaction: discord.Interaction):

    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect(force=True)
        await interaction.response.send_message("Left the voice channel.")

    else:
        await interaction.response.send_message('needs to be in a voice channel to use this command.')


#some setup to record audio from vc
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

RECORDINGS_DIR = "..."#dir for the recording
os.makedirs(RECORDINGS_DIR, exist_ok=True)

#records audio in raw format then converts to wav to be used in the tts model
class WavSink(AudioSink):
    def __init__(self):
        super().__init__()
        self.files = {}

    def wants_opus(self) -> bool:
        return False  # request PCM frames

    def write(self, user: discord.Member, data): #audio gets saved with each persons username
        if user.bot:
            return

        if user.id not in self.files:
            safe_name = "".join(c for c in user.name if c.isalnum() or c in ("-", "_"))
            filename = os.path.join(RECORDINGS_DIR, f"{safe_name}.wav")
            wf = wave.open(filename, "wb")
            wf.setnchannels(2)       # stereo
            wf.setsampwidth(2)       # 16-bit
            wf.setframerate(48000)   # 48 kHz
            self.files[user.id] = wf

        self.files[user.id].writeframes(data.pcm)

    def cleanup(self):
        # avoid RuntimeError by iterating over a copy
        for wf in list(self.files.values()):
            try:
                wf.close()
            except Exception:
                pass
        self.files.clear()


#command setup to record audio of people in vc to use for tts
#this records seprate files for each user in vc making it simpler to put in tts
@client.tree.command(name="record", description="Join VC and record everyone separately to wav",guild=GUILD_ID)
async def record(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("You must be in a voice channel to start recording.")

    channel = interaction.user.voice.channel

    #setup to join vc and start recording
    vc = interaction.guild.voice_client
    if vc is None:
        # Connect as a VoiceRecvClient
        vc: VoiceRecvClient = await channel.connect(cls=VoiceRecvClient)

        # Create and attach sink
        sink = WavSink()
        vc.listen(sink) #record
        vc._wav_sink = sink  # store sink on the voice client

        await interaction.response.send_message("Recording started. Use /stoprecord to stop.")

    elif vc.channel != channel:
        await vc.disconnect(force=True)
        vc: VoiceRecvClient = await channel.connect(cls=VoiceRecvClient)

        # Create and attach sink
        sink = WavSink()
        vc.listen(sink) #record
        vc._wav_sink = sink  # store sink on the voice client

        await interaction.response.send_message("Recording started. Use /stoprecord to stop.")

    else:
        await interaction.response.send_message("Already recording.")



#setting up command for stopping the recording
@client.tree.command(name="stoprecord", description="Stop recording and save files",guild=GUILD_ID)
async def stoprecord(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and isinstance(vc, VoiceRecvClient) and hasattr(vc, "_wav_sink"):
        vc.stop_listening()
        vc._wav_sink.cleanup()
        del vc._wav_sink
        await interaction.response.send_message("Recording stopped. WAV files saved")
        await vc.disconnect(force=True)
    else:
        await interaction.response.send_message("Not currently recording.")






client.run("")#add bot key
