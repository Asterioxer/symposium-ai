# Symposium AI - Real-Time Voice Intelligence Copilot

A private, high-performance Windows desktop application designed for live meetings, interviews, and intellectual discourse. Built from the ground up to operate **100% locally** on your machine with low latency, local Speech-to-Text (STT), and progressive streaming AI answer generation.

---

## ✨ Features

- **🎙️ Real-Time Audio Capture**: Microphone capture with responsive live volume metering.
- **⚡ 100% Local Speech-to-Text**: Powered by `faster-whisper` (`tiny.en` / `base.en`) with automatic NVIDIA CUDA acceleration and CPU fallback.
- **💬 Progressive Streaming LLM Answers**: Real-time token-by-token streaming via local **Ollama** (`dolphinlabs/llama3.2-3b-uncensored`, `qwen3.5:4b`, etc.).
- **🎨 Modern Dark Windows UI**: Built with `CustomTkinter` and `Pillow`, featuring a branded soundwave-nexus emblem, dark-mode styling, and status indicators.
- **🛡️ Asynchronous & Thread-Safe**: Background worker threads ensure the desktop interface stays responsive during recording, transcription, and answer generation.
- **💡 Sample Prompts & Clipboard Integration**: Quick test buttons and one-click answer copying.

---

## 📁 Project Structure

```
PK_Lacritz/
├── assets/
│   ├── icon.png          # High-resolution application logo
│   └── icon.ico          # Windows multi-size taskbar & titlebar icon
├── app.py                # Main desktop application & CustomTkinter GUI
├── audio_recorder.py     # Audio capture module with live RMS level meter
├── stt_engine.py         # Local faster-whisper STT engine (CUDA / CPU)
├── llm_engine.py         # Local Ollama client with token streaming generator
├── create_logo.py        # Brand logo generator script
├── requirements.txt      # Python dependencies
├── run.bat               # Windows 1-click batch launcher
├── run.ps1               # PowerShell launcher
├── test_pipeline.py      # Automated self-test script
└── README.md             # Documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites

1. **Python 3.10+** (tested on Python 3.12 with CUDA).
2. **Ollama**: Download from [ollama.com](https://ollama.com).
3. Ensure at least one model is pulled in Ollama (e.g. `llama3.2:3b`):
   ```powershell
   ollama pull dolphinlabs/llama3.2-3b-uncensored
   ```

### 2. Launch the Application

Double-click [`run.bat`](file:///c:/Users/soham/Desktop/PK_Lacritz/run.bat) or run in PowerShell:

```powershell
python app.py
```

---

## 📖 How to Use

1. **Record Audio**:
   - Click **Start Recording** and speak your question into your microphone.
   - The **Mic Level** progress bar reflects incoming volume.
2. **Stop & Transcribe**:
   - Click **Stop Recording**.
   - Local Whisper transcribes speech into the **Transcribed Question** box in sub-second time.
   - *(Optional)* Edit or refine the text if needed.
3. **Generate Answer**:
   - Click **Suggest Answer**.
   - Watch the answer stream progressively into the **AI Suggested Answer** box.
   - Click **Copy Answer** to copy to clipboard.
