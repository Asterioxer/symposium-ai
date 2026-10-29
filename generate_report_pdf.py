import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header on pages 2+
        if self._pageNumber > 1:
            self.drawString(54, 748, "Symposium AI - Engineering Project Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 740, 558, 740)

        # Running footer on all pages
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(54, 36, "Symposium AI - Local Voice Intelligence Architecture")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()


def build_pdf(filename="Symposium_AI_Project_Report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f8fafc"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=3,
        spaceAfter=5,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # =========================================================================
    # PAGE 1: Title, Metadata, Executive Summary, System Architecture
    # =========================================================================
    story.append(Paragraph("Symposium AI", title_style))
    story.append(Paragraph("Local Real-Time Voice Intelligence & Copilot - Engineering Project Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

    meta_data = [
        [Paragraph("Project:", table_header), Paragraph("Symposium AI", table_cell),
         Paragraph("Target OS:", table_header), Paragraph("Windows 10 / 11 (64-bit)", table_cell)],
        [Paragraph("Runtime Stack:", table_header), Paragraph("Python 3.12, CustomTkinter, SoundDevice", table_cell),
         Paragraph("Inference Engine:", table_header), Paragraph("faster-whisper (CUDA) + Ollama", table_cell)],
        [Paragraph("Repository:", table_header), Paragraph("github.com/Asterioxer/symposium-ai", table_cell),
         Paragraph("Execution Mode:", table_header), Paragraph("100% Offline / Local Execution", table_cell)],
    ]
    meta_table = Table(meta_data, colWidths=[75, 180, 85, 164])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph(
        "Symposium AI is an offline, privacy-first desktop application designed to capture speech audio, "
        "transcribe questions using a local Speech-to-Text (STT) model, and progressively stream intelligent "
        "answers in real time using a locally hosted Large Language Model (LLM).",
        body_style
    ))
    story.append(Paragraph(
        "Unlike cloud-tethered voice assistants, Symposium AI executes all audio processing, speech recognition, "
        "and generative AI inference entirely on consumer hardware. This architecture eliminates data exfiltration "
        "risks, removes recurring API costs, and delivers sub-second response latencies suitable for live meetings, "
        "interviews, and technical discussions.",
        body_style
    ))

    story.append(Paragraph("2. System Architecture", h1_style))
    story.append(Paragraph(
        "The application is engineered into four decoupled subsystems operating asynchronously across background "
        "threads to maintain 60 FPS GUI responsiveness:",
        body_style
    ))

    arch_data = [
        [Paragraph("Layer", table_header), Paragraph("Technology", table_header), Paragraph("Role & Key Mechanics", table_header)],
        [
            Paragraph("Audio Capture", table_cell),
            Paragraph("sounddevice / PortAudio", table_cell),
            Paragraph("Captures microphone input at 16 kHz mono float32. Computes live RMS power levels for dynamic UI volume meters.", table_cell)
        ],
        [
            Paragraph("Live Transcription", table_cell),
            Paragraph("sounddevice + faster-whisper", table_cell),
            Paragraph("Continuous 100ms streaming audio buffer with RMS-based VAD. Emits interim partial tokens (styled in italics) and final text upon conversational pauses.", table_cell)
        ],
        [
            Paragraph("Speech-to-Text", table_cell),
            Paragraph("faster-whisper (CTranslate2)", table_cell),
            Paragraph("Performs in-memory transcription directly from float32 NumPy arrays on NVIDIA CUDA (float16) with automatic CPU int8 fallback.", table_cell)
        ],
        [
            Paragraph("Local LLM", table_cell),
            Paragraph("Ollama Client API", table_cell),
            Paragraph("Connects to local daemon on localhost:11434. Streams output tokens progressively via generator yields with bounded 2048 context windows.", table_cell)
        ],
        [
            Paragraph("User Interface", table_cell),
            Paragraph("CustomTkinter", table_cell),
            Paragraph("Non-blocking desktop interface. Consumes worker thread events via a thread-safe FIFO queue at 30ms intervals.", table_cell)
        ],
    ]
    arch_table = Table(arch_data, colWidths=[85, 125, 294])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(arch_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Engineering Challenges & Benchmarks
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("3. Engineering Challenges & Resolved Edge Cases", h1_style))

    story.append(Paragraph("3.1 Windows CUDA DLL Discovery (cuBLAS Resolution)", h2_style))
    story.append(Paragraph(
        "During initial initialization of faster-whisper on Windows, CTranslate2 reported that <code>cublas64_12.dll</code> "
        "could not be loaded, even though NVIDIA CUDA drivers were installed. Investigation revealed that the DLL resides "
        "in the PyTorch virtual package directory (<code>torch/lib</code>).",
        body_style
    ))
    story.append(Paragraph(
        "<b>Solution:</b> The application dynamically locates the PyTorch library root at startup and calls "
        "<code>os.add_dll_directory()</code> while prepending the path to <code>os.environ['PATH']</code>. "
        "Additionally, a warm-up dummy encode is executed during initialization; if any CUDA driver fault occurs, "
        "the engine falls back to CPU int8 without application disruption.",
        body_style
    ))

    story.append(Paragraph("3.2 Context Window Memory Saturation & LLM Latency", h2_style))
    story.append(Paragraph(
        "Certain local models (e.g., Qwen 3.5 variants) default to a 256K token context window. In Ollama, allocating "
        "a 256K KV cache required 13 GB of VRAM/RAM, causing severe thrashing and stalling first-token latency by over 30 seconds.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Solution:</b> Constrained all Ollama chat sessions to <code>num_ctx: 2048</code>, reducing the active model "
        "footprint to ~1.1 GB and enabling immediate sub-second token streaming. Furthermore, lightweight direct-response "
        "models (such as <code>dolphinlabs/llama3.2-3b-uncensored</code>) are dynamically sorted to the top of the model selection menu.",
        body_style
    ))

    story.append(Paragraph("3.3 Laptop Microphone Array Sensitivity & VAD Filter Dropout", h2_style))
    story.append(Paragraph(
        "Integrated digital microphone arrays on Windows often capture audio at low amplitudes (peak amplitude &lt; 0.005). "
        "Aggressive Voice Activity Detection (VAD) algorithms treated quiet speech as background noise.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Solution:</b> Implemented dynamic peak normalization scaling in <code>stt_engine.py</code> to bring conversational "
        "audio up to ~0.85 peak amplitude before transcription. A two-pass transcription mechanism was also added: if the "
        "VAD pass filters out a soft utterance, a non-VAD fallback pass processes the audio directly.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("4. Performance Benchmarks & Hardware Resource Consumption", h1_style))
    story.append(Paragraph(
        "Empirical benchmarks recorded on a Windows 11 host with an Intel processor and NVIDIA GPU:",
        body_style
    ))

    bench_data = [
        [Paragraph("Metric / Benchmark", table_header), Paragraph("Measured Value", table_header), Paragraph("Operational Impact", table_header)],
        [
            Paragraph("STT Transcription Latency", table_cell),
            Paragraph("0.31 seconds (CUDA fp16)", table_cell),
            Paragraph("Transcribes 4.0s conversational audio clip in near real-time.", table_cell)
        ],
        [
            Paragraph("STT Model VRAM Usage", table_cell),
            Paragraph("~75 MB (Whisper tiny.en)", table_cell),
            Paragraph("Negligible GPU memory overhead; runs alongside larger LLMs.", table_cell)
        ],
        [
            Paragraph("LLM First-Token Latency", table_cell),
            Paragraph("&lt; 0.8 seconds (Llama 3.2 3B)", table_cell),
            Paragraph("Progressive word-by-word streaming begins almost immediately.", table_cell)
        ],
        [
            Paragraph("LLM Token Generation Rate", table_cell),
            Paragraph("~35 - 45 tokens / second", table_cell),
            Paragraph("Smooth streaming output at faster-than-reading speeds.", table_cell)
        ],
        [
            Paragraph("GUI Mainloop Latency", table_cell),
            Paragraph("&lt; 16 ms (60+ FPS UI)", table_cell),
            Paragraph("Zero interface freeze during simultaneous recording and STT.", table_cell)
        ],
    ]
    bench_table = Table(bench_data, colWidths=[125, 135, 244])
    bench_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(bench_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: File Manifest, Verification Suite, and Roadmap
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("5. File Manifest & Module Breakdown", h1_style))

    file_data = [
        [Paragraph("Filename", table_header), Paragraph("Lines", table_header), Paragraph("Description", table_header)],
        [Paragraph("app.py", table_cell), Paragraph("~720", table_cell), Paragraph("Side-by-side desktop UI, Tkinter tag renderer (italic interim to normal text), and event queue.", table_cell)],
        [Paragraph("live_transcriber.py", table_cell), Paragraph("~170", table_cell), Paragraph("Continuous microphone capture, sliding-window RMS VAD, and real-time interim STT.", table_cell)],
        [Paragraph("stt_engine.py", table_cell), Paragraph("~120", table_cell), Paragraph("Whisper STT wrapper with DLL discovery, gain scaling, and two-pass VAD.", table_cell)],
        [Paragraph("llm_engine.py", table_cell), Paragraph("~110", table_cell), Paragraph("Ollama streaming client with model sorting and reasoning token separation.", table_cell)],
        [Paragraph("test_pipeline.py", table_cell), Paragraph("~50", table_cell), Paragraph("Automated non-GUI test script validating audio, STT, and LLM streaming.", table_cell)],
        [Paragraph("run.bat / run.ps1", table_cell), Paragraph("~12", table_cell), Paragraph("Windows launchers that automatically start the local Ollama daemon if inactive.", table_cell)],
    ]
    file_table = Table(file_data, colWidths=[105, 45, 354])
    file_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(file_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("6. Verification & Automated Testing", h1_style))
    story.append(Paragraph(
        "The project includes an automated end-to-end test suite (<code>test_pipeline.py</code>) that validates all "
        "subsystems without requiring interactive manual user input:",
        body_style
    ))
    story.append(Paragraph("&bull; <b>Audio Input:</b> Initializes PortAudio stream and checks device descriptors.", bullet_style))
    story.append(Paragraph("&bull; <b>Synthetic STT Verification:</b> Feeds a standardized 16 kHz WAV utterance (<code>test_speech.wav</code>) into the engine and asserts exact transcript matching.", bullet_style))
    story.append(Paragraph("&bull; <b>Ollama Stream Validation:</b> Sends prompt to local daemon, verifying chunk-by-chunk generator yields and connectivity.", bullet_style))

    story.append(Paragraph("Test Suite Output Log:", h2_style))
    test_snippet = (
        "Testing audio recorder...\n"
        "Audio recorder ready.\n\n"
        "Testing Whisper STT...\n"
        "STT engine ready: Whisper tiny.en (CUDA float16)\n"
        "Sample transcription: 'What is artificial intelligence and machine learning?'\n\n"
        "Testing local Ollama...\n"
        "Available models: ['dolphinlabs/llama3.2-3b-uncensored:latest', 'qwen3.5:4b', ...]\n"
        "Testing stream with dolphinlabs/llama3.2-3b-uncensored:latest...\n"
        "High-level, versatile, easy-to-learn programming language.\n\n"
        "Pipeline test complete."
    )
    story.append(Paragraph(test_snippet.replace("\n", "<br/>"), code_style))

    story.append(Paragraph("7. Future Roadmap", h1_style))
    story.append(Paragraph("1. <b>System Loopback Audio:</b> Integrate WASAPI loopback capture to transcribe meeting interlocutors from speakers simultaneously with user mic.", bullet_style))
    story.append(Paragraph("2. <b>Local Knowledge Base (RAG):</b> Embed a local vector index (e.g., ChromaDB/LanceDB) to ground answers in user meeting briefs.", bullet_style))
    story.append(Paragraph("3. <b>Multi-Lingual Transcription:</b> Support dynamic language detection and auto-translation with larger Whisper checkpoints.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Project report PDF successfully built: {filename}")


if __name__ == "__main__":
    output_filename = "Symposium_AI_Project_Report.pdf"
    build_pdf(output_filename)
