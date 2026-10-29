"""
Symposium AI - Local Real-Time Voice Intelligence Copilot
A high-performance Windows desktop application for local voice capture,
speech-to-text transcription, and progressive streaming answer generation.
"""

import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk

# Ensure CUDA and cuBLAS DLLs from torch are discoverable
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if hasattr(os, "add_dll_directory") and os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
    os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from audio_recorder import AudioRecorder
from stt_engine import SpeechToTextEngine
from llm_engine import LLMEngine

# Set theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SymposiumApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Symposium AI - Real-Time Voice Intelligence")
        self.geometry("940x820")
        self.minsize(800, 680)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Initialize core components
        self.audio_recorder = AudioRecorder(sample_rate=16000)
        self.llm_engine = LLMEngine()
        self.stt_engine = None

        # State flags
        self.is_recording = False
        self.is_transcribing = False
        self.is_generating = False
        self.llm_stop_event = threading.Event()
        self.record_start_time = 0.0

        # UI queue for thread-safe mainloop updates
        self.ui_queue = queue.Queue()

        # Build interface
        self._build_ui()

        # Polling loops
        self.after(30, self._process_ui_queue)
        self.after(50, self._update_audio_meter)

        # Background engine initialization
        threading.Thread(target=self._init_background_services, daemon=True).start()

        # Window closing handler
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Question Box
        self.grid_rowconfigure(4, weight=2)  # Answer Box

        # -------------------------------------------------------------
        # 1. Header Frame with Redesigned Logo & Branding
        # -------------------------------------------------------------
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#141824", border_width=1, border_color="#1e293b")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        # Load logo image
        logo_png = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(logo_png):
            try:
                pil_img = Image.open(logo_png)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(38, 38))
                logo_label = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
                logo_label.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        # Title text block
        text_block = ctk.CTkFrame(brand_frame, fg_color="transparent")
        text_block.pack(side="left")

        title_row = ctk.CTkFrame(text_block, fg_color="transparent")
        title_row.pack(anchor="w")

        title_label = ctk.CTkLabel(
            title_row,
            text="SYMPOSIUM AI",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color="#38bdf8",
        )
        title_label.pack(side="left")

        badge_label = ctk.CTkLabel(
            title_row,
            text="VOICE INTELLIGENCE",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1e293b",
            corner_radius=6,
            text_color="#94a3b8",
            padx=8,
            pady=2,
        )
        badge_label.pack(side="left", padx=(10, 0))

        subtitle_label = ctk.CTkLabel(
            text_block,
            text="Real-Time Speech & Discussion Copilot",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        subtitle_label.pack(anchor="w")

        # Status Pill
        self.status_pill = ctk.CTkLabel(
            header_frame,
            text="[Initializing engines...]",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1e2535",
            text_color="#f59e0b",
            corner_radius=15,
            padx=14,
            pady=6,
        )
        self.status_pill.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        # -------------------------------------------------------------
        # 2. Control & Settings Bar
        # -------------------------------------------------------------
        control_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        control_card.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        control_card.grid_columnconfigure(3, weight=1)

        # Start Recording Button
        self.start_btn = ctk.CTkButton(
            control_card,
            text="Start Recording",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#059669",
            hover_color="#10b981",
            text_color="white",
            height=42,
            width=165,
            corner_radius=8,
            command=self.on_start_recording,
        )
        self.start_btn.grid(row=0, column=0, padx=(15, 8), pady=12)

        # Stop Recording Button
        self.stop_btn = ctk.CTkButton(
            control_card,
            text="Stop Recording",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#dc2626",
            hover_color="#ef4444",
            text_color="white",
            height=42,
            width=165,
            corner_radius=8,
            state="disabled",
            command=self.on_stop_recording,
        )
        self.stop_btn.grid(row=0, column=1, padx=8, pady=12)

        # Live Volume Meter
        meter_container = ctk.CTkFrame(control_card, fg_color="transparent")
        meter_container.grid(row=0, column=2, padx=15, pady=12, sticky="w")

        self.meter_label = ctk.CTkLabel(
            meter_container,
            text="Mic Level:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        )
        self.meter_label.pack(side="left", padx=(0, 8))

        self.audio_meter = ctk.CTkProgressBar(
            meter_container,
            width=120,
            height=12,
            corner_radius=6,
            progress_color="#10b981",
            fg_color="#334155",
        )
        self.audio_meter.set(0.0)
        self.audio_meter.pack(side="left")

        # Model Selector on right
        model_container = ctk.CTkFrame(control_card, fg_color="transparent")
        model_container.grid(row=0, column=3, padx=15, pady=12, sticky="e")

        ctk.CTkLabel(
            model_container,
            text="Model:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(side="left", padx=(0, 6))

        self.model_dropdown = ctk.CTkOptionMenu(
            model_container,
            values=["Discovering models..."],
            width=230,
            height=32,
            corner_radius=6,
            fg_color="#334155",
            button_color="#475569",
        )
        self.model_dropdown.pack(side="left", padx=(0, 6))

        refresh_btn = ctk.CTkButton(
            model_container,
            text="Refresh",
            width=65,
            height=32,
            corner_radius=6,
            fg_color="#334155",
            hover_color="#475569",
            command=self._refresh_models,
        )
        refresh_btn.pack(side="left")

        # -------------------------------------------------------------
        # 3. Transcribed Question Section
        # -------------------------------------------------------------
        q_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        q_frame.grid(row=2, column=0, padx=20, pady=8, sticky="nsew")
        q_frame.grid_columnconfigure(0, weight=1)
        q_frame.grid_rowconfigure(1, weight=1)

        # Question header
        q_header = ctk.CTkFrame(q_frame, fg_color="transparent")
        q_header.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="ew")
        q_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            q_header,
            text="1. Transcribed Question / Input",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0",
        ).grid(row=0, column=0, sticky="w")

        sample_btn = ctk.CTkButton(
            q_header,
            text="Try Sample Question",
            font=ctk.CTkFont(size=11),
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._insert_sample_question,
        )
        sample_btn.grid(row=0, column=1, padx=(0, 8), sticky="e")

        clear_q_btn = ctk.CTkButton(
            q_header,
            text="Clear",
            font=ctk.CTkFont(size=11),
            width=50,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.question_box.delete("1.0", "end"),
        )
        clear_q_btn.grid(row=0, column=2, sticky="e")

        # Question Box
        self.question_box = ctk.CTkTextbox(
            q_frame,
            font=ctk.CTkFont(size=14),
            wrap="word",
            corner_radius=8,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.question_box.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.question_box.insert(
            "1.0",
            "Click 'Start Recording' and speak into your microphone, then click 'Stop Recording' to transcribe.\n"
            "(Or type your question directly here and click 'Suggest Answer')",
        )

        # -------------------------------------------------------------
        # 4. Action Bar (Suggest Answer)
        # -------------------------------------------------------------
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=20, pady=4, sticky="ew")
        action_bar.grid_columnconfigure(0, weight=1)

        action_inner = ctk.CTkFrame(action_bar, fg_color="transparent")
        action_inner.grid(row=0, column=0)

        self.suggest_btn = ctk.CTkButton(
            action_inner,
            text="Suggest Answer",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#2563eb",
            hover_color="#3b82f6",
            height=44,
            width=220,
            corner_radius=8,
            command=self.on_suggest_answer,
        )
        self.suggest_btn.pack(side="left", padx=8)

        self.cancel_gen_btn = ctk.CTkButton(
            action_inner,
            text="Stop Generating",
            font=ctk.CTkFont(size=13),
            fg_color="#475569",
            hover_color="#64748b",
            height=44,
            width=140,
            corner_radius=8,
            state="disabled",
            command=self.on_stop_generating,
        )
        self.cancel_gen_btn.pack(side="left", padx=8)

        # -------------------------------------------------------------
        # 5. AI Suggested Answer Section
        # -------------------------------------------------------------
        a_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        a_frame.grid(row=4, column=0, padx=20, pady=8, sticky="nsew")
        a_frame.grid_columnconfigure(0, weight=1)
        a_frame.grid_rowconfigure(1, weight=1)

        # Answer header
        a_header = ctk.CTkFrame(a_frame, fg_color="transparent")
        a_header.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="ew")
        a_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            a_header,
            text="2. AI Suggested Answer (Streaming Real-Time)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        ).grid(row=0, column=0, sticky="w")

        copy_btn = ctk.CTkButton(
            a_header,
            text="Copy Answer",
            font=ctk.CTkFont(size=11),
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self._copy_answer_to_clipboard,
        )
        copy_btn.grid(row=0, column=1, padx=(0, 8), sticky="e")

        clear_a_btn = ctk.CTkButton(
            a_header,
            text="Clear",
            font=ctk.CTkFont(size=11),
            width=50,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.answer_box.delete("1.0", "end"),
        )
        clear_a_btn.grid(row=0, column=2, sticky="e")

        # Answer Box
        self.answer_box = ctk.CTkTextbox(
            a_frame,
            font=ctk.CTkFont(size=14),
            wrap="word",
            corner_radius=8,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.answer_box.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.answer_box.insert("1.0", "Suggested answer will stream progressively here...")

        # -------------------------------------------------------------
        # 6. Status Bar / Footer
        # -------------------------------------------------------------
        footer = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color="#0f172a")
        footer.grid(row=5, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        self.footer_stt_label = ctk.CTkLabel(
            footer,
            text="STT: Initializing Whisper...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_stt_label.grid(row=0, column=0, padx=15, pady=4, sticky="w")

        self.footer_llm_label = ctk.CTkLabel(
            footer,
            text="Ollama: Connecting...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_llm_label.grid(row=0, column=2, padx=15, pady=4, sticky="e")

    # -----------------------------------------------------------------
    # Background Service Initialization
    # -----------------------------------------------------------------
    def _init_background_services(self):
        """Initializes Whisper model and discovers Ollama models in background."""
        try:
            self._set_status("Initializing Whisper STT...", "#f59e0b")
            self.stt_engine = SpeechToTextEngine(model_size="tiny.en", prefer_cuda=True)
            device_info = self.stt_engine.get_device_info()
            self.ui_queue.put(("footer_stt", device_info))
        except Exception as e:
            self.ui_queue.put(("footer_stt", f"Whisper error: {e}"))

        self._refresh_models()
        self._set_status("Ready", "#10b981")

    def _refresh_models(self):
        """Discovers installed Ollama models and updates the dropdown."""
        def fetch():
            if self.llm_engine.is_available():
                models = self.llm_engine.get_available_models()
                if models:
                    self.ui_queue.put(("models_loaded", models))
                    self.ui_queue.put(("footer_llm", f"Ollama: Connected ({len(models)} models)"))
                else:
                    self.ui_queue.put(("models_empty", "No models found in Ollama"))
                    self.ui_queue.put(("footer_llm", "Ollama: Connected (No models pulled)"))
            else:
                self.ui_queue.put(("models_error", "Ollama not running"))
                self.ui_queue.put(("footer_llm", "Ollama: Offline (http://localhost:11434)"))

        threading.Thread(target=fetch, daemon=True).start()

    # -----------------------------------------------------------------
    # Recording Handlers
    # -----------------------------------------------------------------
    def on_start_recording(self):
        """Start capturing audio from the microphone."""
        if self.is_recording:
            return

        try:
            self.audio_recorder.start()
            self.is_recording = True
            self.record_start_time = time.time()

            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.suggest_btn.configure(state="disabled")

            # Clear question box for recording
            self.question_box.delete("1.0", "end")
            self.question_box.insert("1.0", "[Recording in progress... speak now... Click 'Stop Recording' when finished]")

            self._set_status("Recording audio...", "#ef4444")
        except Exception as e:
            self._set_status("Mic Error", "#ef4444")
            self.question_box.delete("1.0", "end")
            self.question_box.insert("1.0", f"[Microphone Access Error: {e}]\nPlease check your microphone settings.")

    def on_stop_recording(self):
        """Stop capturing audio and trigger local speech-to-text."""
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_btn.configure(state="disabled")
        self.audio_meter.set(0.0)

        duration = time.time() - self.record_start_time
        self._set_status("Transcribing audio...", "#38bdf8")
        self.question_box.delete("1.0", "end")
        self.question_box.insert("1.0", f"[Processing {duration:.1f}s of audio with local Whisper...]")

        def run_stt():
            try:
                audio_data = self.audio_recorder.stop()
                if self.stt_engine is None:
                    time.sleep(1.0)
                transcription = self.stt_engine.transcribe(audio_data) if self.stt_engine else ""
                self.ui_queue.put(("transcription_done", (transcription, duration)))
            except Exception as e:
                self.ui_queue.put(("transcription_error", str(e)))

        threading.Thread(target=run_stt, daemon=True).start()

    # -----------------------------------------------------------------
    # LLM Answer Generation Handlers
    # -----------------------------------------------------------------
    def on_suggest_answer(self):
        """Trigger local LLM answer generation and stream tokens to UI."""
        question = self.question_box.get("1.0", "end").strip()
        # Clean up any bracketed system notes
        if question.startswith("[") and question.endswith("]"):
            question = ""

        if not question or "speak into your microphone" in question.lower():
            self._insert_sample_question()
            question = self.question_box.get("1.0", "end").strip()

        selected_model = self.model_dropdown.get()
        if not selected_model or "Discovering" in selected_model or "No models" in selected_model or "offline" in selected_model:
            models = self.llm_engine.get_available_models()
            if models:
                selected_model = models[0]
                self.model_dropdown.set(selected_model)
            else:
                self._set_status("Ollama offline", "#ef4444")
                self.answer_box.delete("1.0", "end")
                self.answer_box.insert(
                    "1.0",
                    "[Error: Ollama is offline]\nPlease ensure Ollama is running on your machine (http://localhost:11434).",
                )
                return

        self.is_generating = True
        self.llm_stop_event.clear()

        # Update button states
        self.suggest_btn.configure(state="disabled")
        self.cancel_gen_btn.configure(state="normal")
        self.start_btn.configure(state="disabled")

        # Clear answer box and show status
        self.answer_box.delete("1.0", "end")
        self._set_status(f"Generating ({selected_model})...", "#a855f7")

        def run_llm_stream():
            start_time = time.time()
            is_thinking = False
            has_started_content = False

            try:
                stream = self.llm_engine.stream_answer(
                    question=question,
                    model=selected_model,
                    stop_event=self.llm_stop_event,
                )

                for kind, text in stream:
                    if self.llm_stop_event.is_set():
                        break

                    if kind == "thinking":
                        if not is_thinking:
                            is_thinking = True
                            self.ui_queue.put(("llm_thinking_start", ""))
                        self.ui_queue.put(("llm_thinking_token", text))

                    elif kind == "content":
                        if is_thinking and not has_started_content:
                            has_started_content = True
                            is_thinking = False
                            self.ui_queue.put(("llm_content_start", ""))
                        self.ui_queue.put(("llm_token", text))

                elapsed = time.time() - start_time
                self.ui_queue.put(("llm_done", elapsed))
            except Exception as e:
                self.ui_queue.put(("llm_error", str(e)))

        threading.Thread(target=run_llm_stream, daemon=True).start()

    def on_stop_generating(self):
        """User clicked stop generating button."""
        if self.is_generating:
            self.llm_stop_event.set()
            self._set_status("Generation stopped", "#f59e0b")

    # -----------------------------------------------------------------
    # Queue Processing & UI Animation
    # -----------------------------------------------------------------
    def _process_ui_queue(self):
        """Polls the thread-safe queue to update the UI on the main thread."""
        try:
            while True:
                msg_type, payload = self.ui_queue.get_nowait()

                if msg_type == "llm_thinking_start":
                    self._set_status("Thinking...", "#f59e0b")
                    self.answer_box.insert("end", "[Reasoning / Thinking...]\n")
                    self.answer_box.see("end")

                elif msg_type == "llm_thinking_token":
                    self.answer_box.insert("end", payload)
                    self.answer_box.see("end")

                elif msg_type == "llm_content_start":
                    self._set_status("Generating answer...", "#a855f7")
                    self.answer_box.insert("end", "\n\n[Suggested Answer]\n")
                    self.answer_box.see("end")

                elif msg_type == "llm_token":
                    self.answer_box.insert("end", payload)
                    self.answer_box.see("end")

                elif msg_type == "llm_done":
                    self.is_generating = False
                    self.suggest_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self.start_btn.configure(state="normal")
                    self._set_status(f"Answer complete ({payload:.1f}s)", "#10b981")

                elif msg_type == "llm_error":
                    self.is_generating = False
                    self.suggest_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self.start_btn.configure(state="normal")
                    self.answer_box.insert("end", f"\n[Error: {payload}]")
                    self._set_status("Error in generation", "#ef4444")

                elif msg_type == "transcription_done":
                    transcription, duration = payload
                    self.is_transcribing = False
                    self.start_btn.configure(state="normal")
                    self.suggest_btn.configure(state="normal")

                    self.question_box.delete("1.0", "end")
                    if transcription:
                        self.question_box.insert("1.0", transcription)
                        self._set_status(f"Transcribed ({duration:.1f}s audio)", "#10b981")
                    else:
                        self.question_box.insert(
                            "1.0",
                            "[No speech detected on microphone. You can type here directly or try speaking louder.]",
                        )
                        self._set_status("No speech detected", "#f59e0b")

                elif msg_type == "transcription_error":
                    self.is_transcribing = False
                    self.start_btn.configure(state="normal")
                    self.suggest_btn.configure(state="normal")
                    self.question_box.delete("1.0", "end")
                    self.question_box.insert("1.0", f"[Transcription Error: {payload}]")
                    self._set_status("Transcription error", "#ef4444")

                elif msg_type == "models_loaded":
                    models = payload
                    self.model_dropdown.configure(values=models)
                    if models:
                        self.model_dropdown.set(models[0])

                elif msg_type == "models_empty":
                    self.model_dropdown.configure(values=["No models found"])
                    self.model_dropdown.set("No models found")

                elif msg_type == "models_error":
                    self.model_dropdown.configure(values=["Ollama offline"])
                    self.model_dropdown.set("Ollama offline")

                elif msg_type == "footer_stt":
                    self.footer_stt_label.configure(text=f"STT: {payload}")

                elif msg_type == "footer_llm":
                    self.footer_llm_label.configure(text=payload)

        except queue.Empty:
            pass

        self.after(30, self._process_ui_queue)

    def _update_audio_meter(self):
        """Updates the microphone audio level progress bar during recording."""
        if self.is_recording:
            level = self.audio_recorder.get_level()
            self.audio_meter.set(level)
            if level > 0.6:
                self.audio_meter.configure(progress_color="#ef4444")
            elif level > 0.15:
                self.audio_meter.configure(progress_color="#10b981")
            else:
                self.audio_meter.configure(progress_color="#38bdf8")
        self.after(50, self._update_audio_meter)

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _set_status(self, text: str, color: str):
        """Helper to update the top status pill badge."""
        self.status_pill.configure(text=text, text_color=color)

    def _copy_answer_to_clipboard(self):
        """Copies the contents of the AI answer box to the clipboard."""
        text = self.answer_box.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied to clipboard!", "#38bdf8")
            self.after(2000, lambda: self._set_status("Ready", "#10b981"))

    def _insert_sample_question(self):
        """Populates sample interview/technical questions for fast testing."""
        samples = [
            "Can you explain the difference between processes and threads, and when you would use each?",
            "What is dependency injection and what are the main benefits of using it?",
            "How does database indexing work, and what are B-trees?",
            "Describe how you would design a rate limiter for a REST API.",
            "What are the trade-offs between SQL and NoSQL databases?",
        ]
        import random
        choice = random.choice(samples)
        self.question_box.delete("1.0", "end")
        self.question_box.insert("1.0", choice)
        self.suggest_btn.configure(state="normal")
        self._set_status("Sample question loaded", "#38bdf8")

    def _on_closing(self):
        """Gracefully handle window close event."""
        self.llm_stop_event.set()
        if self.is_recording:
            try:
                self.audio_recorder.stop()
            except Exception:
                pass
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = SymposiumApp()
    app.mainloop()
