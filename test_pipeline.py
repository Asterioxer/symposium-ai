import os
import sys

# Ensure torch lib DLLs are in PATH for CUDA support
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if hasattr(os, "add_dll_directory") and os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
    os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

import scipy.io.wavfile as wavfile
import numpy as np
from audio_recorder import AudioRecorder
from stt_engine import SpeechToTextEngine
from llm_engine import LLMEngine

print("Testing audio recorder...")
rec = AudioRecorder()
print("Audio recorder ready.")

print("\nTesting Whisper STT...")
stt = SpeechToTextEngine("tiny.en")
print(f"STT engine ready: {stt.get_device_info()}")

if os.path.exists("test_speech.wav"):
    sr, raw = wavfile.read("test_speech.wav")
    audio = raw.astype(np.float32) / 32768.0
    if sr != 16000:
        import scipy.signal
        num_samples = int(len(audio) * 16000 / sr)
        audio = scipy.signal.resample(audio, num_samples).astype(np.float32)
    result = stt.transcribe(audio)
    print(f"Sample transcription: '{result}'")

print("\nTesting local Ollama...")
llm = LLMEngine()
if llm.is_available():
    models = llm.get_available_models()
    print("Available models:", models)
    if models:
        top_model = models[0]
        print(f"Testing stream with {top_model}...")
        for kind, text in llm.stream_answer("What is Python in 5 words?", model=top_model):
            print(text, end="", flush=True)
        print()
else:
    print("Ollama is not running.")

print("\nPipeline test complete.")
