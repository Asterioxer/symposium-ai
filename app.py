import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk

# Add torch lib to DLL directory on Windows so CTranslate2 can load CUDA cublas DLLs
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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SymposiumApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Symposium AI")
        self.geometry("940x820")
        self.minsize(800, 680)

        # Set taskbar icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.audio_recorder = AudioRecorder(sample_rate=16000)
        self.llm_engine = LLMEngine()
        self.stt_engine = None

        self.is_recording = False
        self.is_transcribing = False
        self.is_generating = False
        self.llm_stop_event = threading.Event()
        self.record_start_time = 0.0

        # Queue for thread-safe UI updates
        self.ui_queue = queue.Queue()

        self._build_ui()

        # Start UI queue polling and mic level updates
        self.after(30, self._process_ui_queue)
        self.after(50, self._update_audio_meter)

        # Initialize Whisper and Ollama in a background thread to keep startup snappy
        threading.Thread(target=self._init_background_services, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(4, weight=2)

        # Header
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#141824", border_width=1, border_color="#1e293b")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        logo_png = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(logo_png):
            try:
                pil_img = Image.open(logo_png)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(36, 36))
                logo_label = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
                logo_label.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        text_block = ctk.CTkFrame(brand_frame, fg_color="transparent")
        text_block.pack(side="left")

        title_label = ctk.CTkLabel(
            text_block,
            text="Symposium AI",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            text_block,
            text="Local Voice Assistant",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        subtitle_label.pack(anchor="w")

        self.status_pill = ctk.CTkLabel(
            header_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1e2535",
            text_color="#f59e0b",
            corner_radius=14,
            padx=12,
            pady=5,
        )
        self.status_pill.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        # Controls & settings
        control_card = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        control_card.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        control_card.grid_columnconfigure(3, weight=1)

        self.start_btn = ctk.CTkButton(
            control_card,
            text="Start Recording",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#10b981",
            text_color="white",
            height=38,
            width=150,
            corner_radius=6,
            command=self.on_start_recording,
        )
        self.start_btn.grid(row=0, column=0, padx=(15, 8), pady=12)

        self.stop_btn = ctk.CTkButton(
            control_card,
            text="Stop Recording",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#dc2626",
            hover_color="#ef4444",
            text_color="white",
            height=38,
            width=150,
            corner_radius=6,
            state="disabled",
            command=self.on_stop_recording,
        )
        self.stop_btn.grid(row=0, column=1, padx=8, pady=12)

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
            height=10,
            corner_radius=5,
            progress_color="#10b981",
            fg_color="#334155",
        )
        self.audio_meter.set(0.0)
        self.audio_meter.pack(side="left")

        # Model selection
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

        # Question area
        q_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        q_frame.grid(row=2, column=0, padx=20, pady=8, sticky="nsew")
        q_frame.grid_columnconfigure(0, weight=1)
        q_frame.grid_rowconfigure(1, weight=1)

        q_header = ctk.CTkFrame(q_frame, fg_color="transparent")
        q_header.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="ew")
        q_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            q_header,
            text="Transcribed Question",
            font=ctk.CTkFont(size=13, weight="bold"),
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

        self.question_box = ctk.CTkTextbox(
            q_frame,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=6,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.question_box.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.question_box.insert(
            "1.0",
            "Click Start Recording and speak into your microphone, or type a question here directly.",
        )

        # Action bar
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.grid(row=3, column=0, padx=20, pady=4, sticky="ew")
        action_bar.grid_columnconfigure(0, weight=1)

        action_inner = ctk.CTkFrame(action_bar, fg_color="transparent")
        action_inner.grid(row=0, column=0)

        self.suggest_btn = ctk.CTkButton(
            action_inner,
            text="Suggest Answer",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#3b82f6",
            height=40,
            width=180,
            corner_radius=6,
            command=self.on_suggest_answer,
        )
        self.suggest_btn.pack(side="left", padx=8)

        self.cancel_gen_btn = ctk.CTkButton(
            action_inner,
            text="Stop Generating",
            font=ctk.CTkFont(size=12),
            fg_color="#475569",
            hover_color="#64748b",
            height=40,
            width=130,
            corner_radius=6,
            state="disabled",
            command=self.on_stop_generating,
        )
        self.cancel_gen_btn.pack(side="left", padx=8)

        # Answer area
        a_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        a_frame.grid(row=4, column=0, padx=20, pady=8, sticky="nsew")
        a_frame.grid_columnconfigure(0, weight=1)
        a_frame.grid_rowconfigure(1, weight=1)

        a_header = ctk.CTkFrame(a_frame, fg_color="transparent")
        a_header.grid(row=0, column=0, padx=15, pady=(10, 4), sticky="ew")
        a_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            a_header,
            text="Suggested Answer",
            font=ctk.CTkFont(size=13, weight="bold"),
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

        self.answer_box = ctk.CTkTextbox(
            a_frame,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=6,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.answer_box.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.answer_box.insert("1.0", "Suggested answer will appear here.")

        # Footer
        footer = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#0f172a")
        footer.grid(row=5, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        self.footer_stt_label = ctk.CTkLabel(
            footer,
            text="STT: Initializing...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_stt_label.grid(row=0, column=0, padx=15, pady=3, sticky="w")

        self.footer_llm_label = ctk.CTkLabel(
            footer,
            text="Ollama: Connecting...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_llm_label.grid(row=0, column=2, padx=15, pady=3, sticky="e")

    def _init_background_services(self):
        try:
            self._set_status("Initializing STT...", "#f59e0b")
            self.stt_engine = SpeechToTextEngine(model_size="tiny.en", prefer_cuda=True)
            device_info = self.stt_engine.get_device_info()
            self.ui_queue.put(("footer_stt", device_info))
        except Exception as e:
            self.ui_queue.put(("footer_stt", f"STT error: {e}"))

        self._refresh_models()
        self._set_status("Ready", "#10b981")

    def _refresh_models(self):
        def fetch():
            if self.llm_engine.is_available():
                models = self.llm_engine.get_available_models()
                if models:
                    self.ui_queue.put(("models_loaded", models))
                    self.ui_queue.put(("footer_llm", f"Ollama: Connected ({len(models)} models)"))
                else:
                    self.ui_queue.put(("models_empty", "No models found"))
                    self.ui_queue.put(("footer_llm", "Ollama: Connected (no models pulled)"))
            else:
                self.ui_queue.put(("models_error", "Ollama offline"))
                self.ui_queue.put(("footer_llm", "Ollama: Offline (http://localhost:11434)"))

        threading.Thread(target=fetch, daemon=True).start()

    def on_start_recording(self):
        if self.is_recording:
            return

        try:
            self.audio_recorder.start()
            self.is_recording = True
            self.record_start_time = time.time()

            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.suggest_btn.configure(state="disabled")

            self.question_box.delete("1.0", "end")
            self.question_box.insert("1.0", "Recording... Click Stop Recording when finished speaking.")

            self._set_status("Recording...", "#ef4444")
        except Exception as e:
            self._set_status("Mic error", "#ef4444")
            self.question_box.delete("1.0", "end")
            self.question_box.insert("1.0", f"Microphone error: {e}")

    def on_stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False
        self.stop_btn.configure(state="disabled")
        self.audio_meter.set(0.0)

        duration = time.time() - self.record_start_time
        self._set_status("Transcribing...", "#38bdf8")
        self.question_box.delete("1.0", "end")
        self.question_box.insert("1.0", f"Transcribing {duration:.1f}s of audio...")

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

    def on_suggest_answer(self):
        question = self.question_box.get("1.0", "end").strip()

        # Handle empty or prompt placeholder text
        if not question or "speak into your microphone" in question.lower() or "click start recording" in question.lower():
            self._insert_sample_question()
            question = self.question_box.get("1.0", "end").strip()

        selected_model = self.model_dropdown.get()
        if not selected_model or "Discovering" in selected_model or "offline" in selected_model:
            models = self.llm_engine.get_available_models()
            if models:
                selected_model = models[0]
                self.model_dropdown.set(selected_model)
            else:
                self._set_status("Ollama offline", "#ef4444")
                self.answer_box.delete("1.0", "end")
                self.answer_box.insert(
                    "1.0",
                    "Error: Ollama is offline. Make sure Ollama is running at http://localhost:11434.",
                )
                return

        self.is_generating = True
        self.llm_stop_event.clear()

        self.suggest_btn.configure(state="disabled")
        self.cancel_gen_btn.configure(state="normal")
        self.start_btn.configure(state="disabled")

        self.answer_box.delete("1.0", "end")
        self._set_status("Generating...", "#a855f7")

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
        if self.is_generating:
            self.llm_stop_event.set()
            self._set_status("Stopped", "#f59e0b")

    def _process_ui_queue(self):
        try:
            while True:
                msg_type, payload = self.ui_queue.get_nowait()

                if msg_type == "llm_thinking_start":
                    self._set_status("Thinking...", "#f59e0b")
                    self.answer_box.insert("end", "[Thinking]\n")
                    self.answer_box.see("end")

                elif msg_type == "llm_thinking_token":
                    self.answer_box.insert("end", payload)
                    self.answer_box.see("end")

                elif msg_type == "llm_content_start":
                    self._set_status("Generating...", "#a855f7")
                    self.answer_box.insert("end", "\n\n[Answer]\n")
                    self.answer_box.see("end")

                elif msg_type == "llm_token":
                    self.answer_box.insert("end", payload)
                    self.answer_box.see("end")

                elif msg_type == "llm_done":
                    self.is_generating = False
                    self.suggest_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self.start_btn.configure(state="normal")
                    self._set_status(f"Done ({payload:.1f}s)", "#10b981")

                elif msg_type == "llm_error":
                    self.is_generating = False
                    self.suggest_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self.start_btn.configure(state="normal")
                    self.answer_box.insert("end", f"\nError: {payload}")
                    self._set_status("Error", "#ef4444")

                elif msg_type == "transcription_done":
                    transcription, duration = payload
                    self.is_transcribing = False
                    self.start_btn.configure(state="normal")
                    self.suggest_btn.configure(state="normal")

                    self.question_box.delete("1.0", "end")
                    if transcription:
                        self.question_box.insert("1.0", transcription)
                        self._set_status(f"Transcribed ({duration:.1f}s)", "#10b981")
                    else:
                        self.question_box.insert(
                            "1.0",
                            "No speech detected. Please speak closer to the microphone or type here.",
                        )
                        self._set_status("No speech detected", "#f59e0b")

                elif msg_type == "transcription_error":
                    self.is_transcribing = False
                    self.start_btn.configure(state="normal")
                    self.suggest_btn.configure(state="normal")
                    self.question_box.delete("1.0", "end")
                    self.question_box.insert("1.0", f"Transcription error: {payload}")
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

    def _set_status(self, text: str, color: str):
        self.status_pill.configure(text=text, text_color=color)

    def _copy_answer_to_clipboard(self):
        text = self.answer_box.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied to clipboard", "#38bdf8")
            self.after(2000, lambda: self._set_status("Ready", "#10b981"))

    def _insert_sample_question(self):
        samples = [
            "What is the difference between a process and a thread?",
            "How does dependency injection work and why is it useful?",
            "Explain how database indexes and B-trees work.",
            "How would you design a simple rate limiter for an API?",
            "What are the main differences between SQL and NoSQL databases?",
        ]
        import random
        choice = random.choice(samples)
        self.question_box.delete("1.0", "end")
        self.question_box.insert("1.0", choice)
        self.suggest_btn.configure(state="normal")
        self._set_status("Sample loaded", "#38bdf8")

    def _on_closing(self):
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
