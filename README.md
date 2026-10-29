# Symposium AI

Symposium AI is a lightweight desktop assistant for Windows that captures microphone audio, transcribes it locally using Whisper, and generates suggested answers in real time using a local Ollama model.

All speech recognition and LLM inference run entirely offline on your machine.

## Features

- Side-by-side desktop interface: live voice transcription on the left, streaming AI answer on the right.
- Single voice box button for live continuous listening (inspired by ChatGPT and Claude voice mode).
- Real-time transcription: words appear live in italics while speaking, and automatically convert into regular text upon conversational pauses.
- Local speech-to-text powered by `faster-whisper` (runs on CUDA with automatic CPU fallback).
- Progressive token streaming from local Ollama models directly side-by-side.
- Dynamic audio level meter and silence-detection VAD.
- Automatic model detection from your local Ollama installation.
- 100% offline and local execution; no audio data or prompts leave your machine.

## Project Structure

```
.
├── assets/
│   ├── icon.png                  # App branding icon
│   ├── icon.ico                  # Windows title bar icon
│   ├── mic_idle.png              # Voice box idle state icon
│   └── mic_active.png            # Voice box active state icon
├── app.py                        # Main side-by-side CustomTkinter desktop application
├── live_transcriber.py           # Real-time microphone capture and streaming STT engine
├── audio_recorder.py             # Audio device helpers and recording routines
├── stt_engine.py                 # Whisper STT wrapper with CUDA DLL auto-discovery
├── llm_engine.py                 # Ollama streaming client with bounded context
├── requirements.txt              # Python dependencies
├── run.bat                       # Windows batch launcher (starts Ollama if needed)
├── run.ps1                       # PowerShell launcher
├── test_pipeline.py              # Automated pipeline verification script
└── Symposium_AI_Project_Report.pdf # Comprehensive engineering report
```

## Requirements

- Windows 10/11
- Python 3.10+
- [Ollama](https://ollama.com) running locally (`http://localhost:11434`)
- At least one model pulled in Ollama (e.g. `llama3.2:3b` or `qwen3.5:4b`):

```bash
ollama pull dolphinlabs/llama3.2-3b-uncensored
```

## Setup

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

2. Make sure Ollama is running:

```bash
ollama list
```

## Running the App

Launch via Python:

```bash
python app.py
```

Or double-click `run.bat`.

## Usage

1. Click the circular **Microphone / Voice Box** button on the bottom left to begin listening.
2. Speak naturally. Your words will be transcribed continuously in real time: in-progress phrases appear in italics, and automatically morph into regular font as you pause.
3. Click the voice box again (or let silence finalize) when you are done speaking.
4. Click **Suggest Answer**. The answer will stream progressively in the right panel.
5. Click **Copy** in the top right of the answer panel to copy the response to your clipboard.

You can also edit the transcription directly, or click **Try Sample** to test answering with a preloaded prompt.
