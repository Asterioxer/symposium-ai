# Symposium AI

Symposium AI is a lightweight desktop assistant for Windows that captures microphone audio, transcribes it locally using Whisper, and generates suggested answers in real time using a local Ollama model.

All speech recognition and LLM inference run entirely offline on your machine.

## Features

- Local microphone capture with a live volume meter.
- Local speech-to-text using `faster-whisper` (runs on CUDA with automatic CPU fallback).
- Progressive token streaming from local Ollama models.
- Automatic model detection from your local Ollama installation.
- Clean desktop interface built with CustomTkinter.
- Editable transcription box and one-click answer copying.

## Project Structure

```
.
├── assets/
│   ├── icon.png          # App icon
│   └── icon.ico          # Windows icon
├── app.py                # Main application UI and controller
├── audio_recorder.py     # Microphone recording via sounddevice
├── stt_engine.py         # Whisper STT wrapper
├── llm_engine.py         # Ollama streaming client
├── requirements.txt      # Python dependencies
├── run.bat               # Windows batch launcher
├── run.ps1               # PowerShell launcher
└── test_pipeline.py      # Environment and pipeline test script
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

1. Click **Start Recording** and speak into your microphone.
2. Click **Stop Recording**. The transcription will appear in the top text box within a second.
3. Click **Suggest Answer**. The answer will stream into the bottom text box as it is generated.
4. Click **Copy Answer** to copy the text to your clipboard.

You can also type or paste any question directly into the top box, or click **Try Sample Question** to test answer generation immediately.
