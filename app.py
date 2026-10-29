import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk

# Ensure CUDA and cuBLAS DLLs from torch are discoverable on Windows
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if hasattr(os, "add_dll_directory") and os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
    os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from stt_engine import SpeechToTextEngine
from llm_engine import LLMEngine
from live_transcriber import LiveTranscriber

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SymposiumApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Symposium AI")
        self.geometry("1080x720")
        self.minsize(920, 600)

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.stt_engine = None
        self.llm_engine = LLMEngine()
        self.live_transcriber = None

        self.is_listening = False
        self.is_generating = False
        self.llm_stop_event = threading.Event()

        # Transcript text state
        self.finalized_transcript = ""
        self.interim_transcript = ""

        # UI event queue
        self.ui_queue = queue.Queue()

        self._load_icons()
        self._build_ui()

        # Polling loops
        self.after(30, self._process_ui_queue)
        self.after(50, self._update_mic_meter)

        # Background initialization
        threading.Thread(target=self._init_background_services, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _load_icons(self):
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.logo_ctk = None
        self.mic_idle_ctk = None
        self.mic_active_ctk = None

        logo_path = os.path.join(assets_dir, "icon.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                self.logo_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
            except Exception:
                pass

        idle_path = os.path.join(assets_dir, "mic_idle.png")
        if os.path.exists(idle_path):
            try:
                img = Image.open(idle_path)
                self.mic_idle_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
            except Exception:
                pass

        active_path = os.path.join(assets_dir, "mic_active.png")
        if os.path.exists(active_path):
            try:
                img = Image.open(active_path)
                self.mic_active_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
            except Exception:
                pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Side-by-side main area

        # -------------------------------------------------------------
        # 1. Top Bar
        # -------------------------------------------------------------
        top_bar = ctk.CTkFrame(self, height=54, corner_radius=8, fg_color="#141824", border_width=1, border_color="#1e293b")
        top_bar.grid(row=0, column=0, padx=16, pady=(12, 8), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)

        brand_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=14, pady=8, sticky="w")

        if self.logo_ctk:
            logo_lbl = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
            logo_lbl.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            brand_frame,
            text="Symposium AI",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8",
        ).pack(side="left")

        ctk.CTkLabel(
            brand_frame,
            text="Live Copilot",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        ).pack(side="left", padx=(8, 0))

        # Model selector & Status
        top_right = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_right.grid(row=0, column=2, padx=14, pady=8, sticky="e")

        ctk.CTkLabel(
            top_right,
            text="Model:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(side="left", padx=(0, 6))

        self.model_dropdown = ctk.CTkOptionMenu(
            top_right,
            values=["Discovering models..."],
            width=210,
            height=28,
            corner_radius=6,
            fg_color="#334155",
            button_color="#475569",
        )
        self.model_dropdown.pack(side="left", padx=(0, 6))

        refresh_btn = ctk.CTkButton(
            top_right,
            text="Refresh",
            width=58,
            height=28,
            corner_radius=6,
            fg_color="#334155",
            hover_color="#475569",
            command=self._refresh_models,
        )
        refresh_btn.pack(side="left", padx=(0, 12))

        self.status_pill = ctk.CTkLabel(
            top_right,
            text="Initializing...",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e2535",
            text_color="#f59e0b",
            corner_radius=12,
            padx=10,
            pady=4,
        )
        self.status_pill.pack(side="left")

        # -------------------------------------------------------------
        # 2. Side-by-Side Main Container
        # -------------------------------------------------------------
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.grid(row=1, column=0, padx=16, pady=4, sticky="nsew")
        main_split.grid_columnconfigure(0, weight=1)  # Left: Voice Transcription
        main_split.grid_columnconfigure(1, weight=1)  # Right: AI Answer
        main_split.grid_rowconfigure(0, weight=1)

        # ---------------- Left Panel: Voice Transcription ----------------
        left_panel = ctk.CTkFrame(main_split, corner_radius=10, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        left_panel.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        # Left Header
        left_header = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_header.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
        left_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_header,
            text="Voice Transcription (Live)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0",
        ).grid(row=0, column=0, sticky="w")

        sample_btn = ctk.CTkButton(
            left_header,
            text="Try Sample",
            font=ctk.CTkFont(size=11),
            height=24,
            width=75,
            fg_color="#334155",
            hover_color="#475569",
            command=self._insert_sample_question,
        )
        sample_btn.grid(row=0, column=1, padx=(0, 6), sticky="e")

        clear_q_btn = ctk.CTkButton(
            left_header,
            text="Clear",
            font=ctk.CTkFont(size=11),
            height=24,
            width=46,
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_transcription,
        )
        clear_q_btn.grid(row=0, column=2, sticky="e")

        # Left Transcription Text Area
        self.transcription_box = ctk.CTkTextbox(
            left_panel,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=6,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.transcription_box.grid(row=1, column=0, padx=14, pady=(0, 8), sticky="nsew")

        # Configure tags for italic-to-normal animation
        self.transcription_box._textbox.tag_configure("final", font=("Segoe UI", 12, "normal"), foreground="#f8fafc")
        self.transcription_box._textbox.tag_configure("interim", font=("Segoe UI", 12, "italic"), foreground="#38bdf8")

        self.transcription_box.insert("1.0", "Click the microphone button below to start live voice transcription.")

        # Left Bottom Controls (Voice Box & Send)
        left_controls = ctk.CTkFrame(left_panel, fg_color="transparent")
        left_controls.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")
        left_controls.grid_columnconfigure(2, weight=1)

        # Voice Box Button (small circular toggle icon)
        self.voice_btn = ctk.CTkButton(
            left_controls,
            text="",
            image=self.mic_idle_ctk,
            width=42,
            height=42,
            corner_radius=21,
            fg_color="#334155",
            hover_color="#475569",
            command=self.toggle_voice_listening,
        )
        self.voice_btn.grid(row=0, column=0, padx=(0, 10))

        # Mic state label & level meter
        mic_info = ctk.CTkFrame(left_controls, fg_color="transparent")
        mic_info.grid(row=0, column=1, sticky="w")

        self.mic_state_lbl = ctk.CTkLabel(
            mic_info,
            text="Mic: Idle (Click to speak)",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.mic_state_lbl.pack(anchor="w")

        self.audio_meter = ctk.CTkProgressBar(
            mic_info,
            width=130,
            height=8,
            corner_radius=4,
            progress_color="#10b981",
            fg_color="#334155",
        )
        self.audio_meter.set(0.0)
        self.audio_meter.pack(anchor="w", pady=(2, 0))

        # Send / Suggest Answer Button
        self.send_btn = ctk.CTkButton(
            left_controls,
            text="Suggest Answer",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#3b82f6",
            height=38,
            width=140,
            corner_radius=6,
            command=self.on_suggest_answer,
        )
        self.send_btn.grid(row=0, column=3, sticky="e")

        # ---------------- Right Panel: AI Answer ----------------
        right_panel = ctk.CTkFrame(main_split, corner_radius=10, fg_color="#1a202c", border_width=1, border_color="#2d3748")
        right_panel.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        # Right Header
        right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_header.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
        right_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right_header,
            text="AI Suggested Answer (Streaming)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8",
        ).grid(row=0, column=0, sticky="w")

        copy_btn = ctk.CTkButton(
            right_header,
            text="Copy",
            font=ctk.CTkFont(size=11),
            height=24,
            width=50,
            fg_color="#334155",
            hover_color="#475569",
            command=self._copy_answer,
        )
        copy_btn.grid(row=0, column=1, padx=(0, 6), sticky="e")

        clear_a_btn = ctk.CTkButton(
            right_header,
            text="Clear",
            font=ctk.CTkFont(size=11),
            height=24,
            width=46,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.answer_box.delete("1.0", "end"),
        )
        clear_a_btn.grid(row=0, column=2, sticky="e")

        # Right Answer Text Area
        self.answer_box = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=6,
            fg_color="#10141e",
            text_color="#f8fafc",
            border_width=1,
            border_color="#334155",
        )
        self.answer_box.grid(row=1, column=0, padx=14, pady=(0, 8), sticky="nsew")
        self.answer_box.insert("1.0", "Suggested answer will stream side-by-side here.")

        # Right Bottom Controls (Stop Generating)
        right_controls = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_controls.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")

        self.cancel_gen_btn = ctk.CTkButton(
            right_controls,
            text="Stop Generating",
            font=ctk.CTkFont(size=12),
            fg_color="#475569",
            hover_color="#64748b",
            height=38,
            width=120,
            corner_radius=6,
            state="disabled",
            command=self.on_stop_generating,
        )
        self.cancel_gen_btn.pack(side="right")

        # -------------------------------------------------------------
        # 3. Footer Bar
        # -------------------------------------------------------------
        footer = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#0f172a")
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        self.footer_stt_label = ctk.CTkLabel(
            footer,
            text="STT: Initializing Whisper...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_stt_label.grid(row=0, column=0, padx=16, pady=2, sticky="w")

        self.footer_llm_label = ctk.CTkLabel(
            footer,
            text="Ollama: Connecting...",
            font=ctk.CTkFont(size=11),
            text_color="#64748b",
        )
        self.footer_llm_label.grid(row=0, column=2, padx=16, pady=2, sticky="e")

    # -----------------------------------------------------------------
    # Background Initialization
    # -----------------------------------------------------------------
    def _init_background_services(self):
        try:
            self._set_status("Loading STT...", "#f59e0b")
            self.stt_engine = SpeechToTextEngine(model_size="tiny.en", prefer_cuda=True)
            self.live_transcriber = LiveTranscriber(
                stt_engine=self.stt_engine,
                event_queue=self.ui_queue,
            )
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

    # -----------------------------------------------------------------
    # Live Voice Toggle (ChatGPT / Claude style Voice Box)
    # -----------------------------------------------------------------
    def toggle_voice_listening(self):
        if not self.live_transcriber:
            messagebox.showwarning("STT Loading", "Whisper STT is still loading. Please wait a moment.")
            return

        if not self.is_listening:
            # Start Live Voice Listening
            self.is_listening = True
            self.voice_btn.configure(
                image=self.mic_active_ctk or self.mic_idle_ctk,
                fg_color="#059669",
                hover_color="#10b981",
            )
            self.mic_state_lbl.configure(text="Mic: Active (Listening live...)", text_color="#10b981")
            self._set_status("Listening live...", "#10b981")

            # Clear starter placeholder text if present
            current = self.transcription_box.get("1.0", "end").strip()
            if "Click the microphone button" in current:
                self.transcription_box.delete("1.0", "end")
                self.finalized_transcript = ""
                self.interim_transcript = ""

            self.live_transcriber.start()

        else:
            # Stop Live Voice Listening
            self.is_listening = False
            self.voice_btn.configure(
                image=self.mic_idle_ctk,
                fg_color="#334155",
                hover_color="#475569",
            )
            self.mic_state_lbl.configure(text="Mic: Idle (Click to speak)", text_color="#94a3b8")
            self.audio_meter.set(0.0)
            self._set_status("Ready", "#10b981")

            self.live_transcriber.stop()

            # Finalize any pending interim text into normal font
            if self.interim_transcript:
                if self.finalized_transcript:
                    self.finalized_transcript += " " + self.interim_transcript
                else:
                    self.finalized_transcript = self.interim_transcript
                self.interim_transcript = ""
                self._render_transcription()

    # -----------------------------------------------------------------
    # Live Italic-to-Normal Transcription Renderer
    # -----------------------------------------------------------------
    def _render_transcription(self):
        """Renders finalized text in regular font and interim text in italic font."""
        self.transcription_box.configure(state="normal")
        self.transcription_box.delete("1.0", "end")

        if self.finalized_transcript:
            self.transcription_box._textbox.insert("end", self.finalized_transcript + " ", "final")

        if self.interim_transcript:
            self.transcription_box._textbox.insert("end", self.interim_transcript, "interim")

        self.transcription_box.see("end")

    def _clear_transcription(self):
        self.finalized_transcript = ""
        self.interim_transcript = ""
        self.transcription_box.delete("1.0", "end")

    # -----------------------------------------------------------------
    # AI Answer Streaming Handlers
    # -----------------------------------------------------------------
    def on_suggest_answer(self):
        # Sync with any manual typing edits in textbox
        full_text = self.transcription_box.get("1.0", "end").strip()
        if "Click the microphone button" in full_text:
            full_text = ""

        if not full_text:
            self._insert_sample_question()
            full_text = self.transcription_box.get("1.0", "end").strip()

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

        self.send_btn.configure(state="disabled")
        self.cancel_gen_btn.configure(state="normal")

        self.answer_box.delete("1.0", "end")
        self._set_status("Generating...", "#a855f7")

        def run_stream():
            start_time = time.time()
            is_thinking = False
            has_started_content = False

            try:
                stream = self.llm_engine.stream_answer(
                    question=full_text,
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

        threading.Thread(target=run_stream, daemon=True).start()

    def on_stop_generating(self):
        if self.is_generating:
            self.llm_stop_event.set()
            self._set_status("Stopped", "#f59e0b")

    # -----------------------------------------------------------------
    # UI Queue Processor
    # -----------------------------------------------------------------
    def _process_ui_queue(self):
        try:
            while True:
                msg_type, payload = self.ui_queue.get_nowait()

                # Live STT Events: Interim (Italics) vs Final (Regular)
                if msg_type == "stt_interim":
                    self.interim_transcript = payload
                    self._render_transcription()
                    self._set_status("Transcribing...", "#38bdf8")

                elif msg_type == "stt_final":
                    new_text = payload.strip()
                    if new_text:
                        if self.finalized_transcript:
                            self.finalized_transcript += " " + new_text
                        else:
                            self.finalized_transcript = new_text
                    self.interim_transcript = ""
                    self._render_transcription()
                    self._set_status("Listening live...", "#10b981")

                elif msg_type == "stt_interim_clear":
                    self.interim_transcript = ""
                    self._render_transcription()

                # LLM Events
                elif msg_type == "llm_thinking_start":
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
                    self.send_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self._set_status(f"Done ({payload:.1f}s)", "#10b981")

                elif msg_type == "llm_error":
                    self.is_generating = False
                    self.send_btn.configure(state="normal")
                    self.cancel_gen_btn.configure(state="disabled")
                    self.answer_box.insert("end", f"\nError: {payload}")
                    self._set_status("Error", "#ef4444")

                # System & Model Events
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

                elif msg_type == "set_status":
                    text, color = payload
                    self.status_pill.configure(text=text, text_color=color)

                elif msg_type == "footer_stt":
                    self.footer_stt_label.configure(text=f"STT: {payload}")

                elif msg_type == "footer_llm":
                    self.footer_llm_label.configure(text=payload)

        except queue.Empty:
            pass

        self.after(30, self._process_ui_queue)

    def _update_mic_meter(self):
        if self.is_listening and self.live_transcriber:
            level = self.live_transcriber.get_level()
            self.audio_meter.set(level)
            if level > 0.6:
                self.audio_meter.configure(progress_color="#ef4444")
            elif level > 0.15:
                self.audio_meter.configure(progress_color="#10b981")
            else:
                self.audio_meter.configure(progress_color="#38bdf8")
        else:
            self.audio_meter.set(0.0)

        self.after(50, self._update_mic_meter)

    def _set_status(self, text: str, color: str):
        if threading.current_thread() is threading.main_thread():
            try:
                self.status_pill.configure(text=text, text_color=color)
            except Exception:
                pass
        else:
            self.ui_queue.put(("set_status", (text, color)))

    def _copy_answer(self):
        text = self.answer_box.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied", "#38bdf8")
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
        self.finalized_transcript = choice
        self.interim_transcript = ""
        self._render_transcription()
        self._set_status("Sample loaded", "#38bdf8")

    def _on_closing(self):
        self.llm_stop_event.set()
        if self.live_transcriber:
            self.live_transcriber.stop()
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = SymposiumApp()
    app.mainloop()
