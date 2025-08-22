import torchaudio as ta
import torch
from chatterbox.tts import ChatterboxTTS
import time
from better_profanity import profanity



# Automatically detect the best available device
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Using device: {device}")

def run_with_audio_in(input,AUDIO_PROMPT_PATH):
    model = ChatterboxTTS.from_pretrained(device=device)

    text = input
    text = profanity.censor(text)
    print(text)

    # If you want to synthesize with a different voice, specify the audio prompt
    #AUDIO_PROMPT_PATH = "C:/Users/user/Desktop/X_XaDi-liwLMIono2uDm0Q.wav"
    wav = model.generate(text, audio_prompt_path=AUDIO_PROMPT_PATH)
    ta.save(".../out.wav", wav, model.sr) #put in the dir where you want to save the audio file make sure it is seperate from the recording dir


def run(input):
    model = ChatterboxTTS.from_pretrained(device=device)

    text = input
    text = profanity.censor(text)
    print(text)

    wav = model.generate(text)
    ta.save(".../out.wav", wav, model.sr) #put in the dir where you want to save the audio file make sure it is seperate from the recording dir

