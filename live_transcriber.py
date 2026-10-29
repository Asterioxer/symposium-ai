"""
Live Streaming Audio Transcriber for Symposium AI.
Captures continuous microphone audio, performs real-time VAD (Voice Activity Detection),
and emits interim (italicized) and finalized (regular) transcription events.
"""

import time
import queue
import threading
import numpy as np
import sounddevice as sd

from stt_engine import SpeechToTextEngine


class LiveTranscriber:
    def __init__(
        self,
        stt_engine: SpeechToTextEngine,
        sample_rate: int = 16000,
        event_queue: queue.Queue = None,
        silence_timeout: float = 0.9,
        speech_threshold: float = 0.010,
    ):
        self.stt_engine = stt_engine
        self.sample_rate = sample_rate
        self.event_queue = event_queue or queue.Queue()
        self.silence_timeout = silence_timeout
        self.speech_threshold = speech_threshold

        self.stream = None
        self.is_running = False
        self._lock = threading.Lock()

        self.raw_queue = queue.Queue()
        self.current_level = 0.0
        self.worker_thread = None

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_running:
            return

        chunk = indata[:, 0].copy() if indata.ndim > 1 else indata.flatten().copy()
        self.raw_queue.put(chunk)

        # Update smoothed RMS volume level
        rms = float(np.sqrt(np.mean(chunk**2) + 1e-12))
        scaled = min(1.0, rms * 25.0)
        self.current_level = 0.25 * self.current_level + 0.75 * scaled

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self.current_level = 0.0
        while not self.raw_queue.empty():
            try:
                self.raw_queue.get_nowait()
            except queue.Empty:
                break

        try:
            dev_info = sd.query_devices(kind="input")
            max_ch = dev_info.get("max_input_channels", 1)
            use_channels = 1 if max_ch >= 1 else 1
        except Exception:
            use_channels = 1

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=use_channels,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=1600,  # 100ms blocks
        )
        self.stream.start()

        self.worker_thread = threading.Thread(target=self._process_stream, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.is_running = False
        self.current_level = 0.0

        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def get_level(self) -> float:
        return self.current_level if self.is_running else 0.0

    def _process_stream(self):
        utterance_chunks = []
        is_speaking = False
        last_speech_time = 0.0
        last_interim_transcribe_time = 0.0

        while self.is_running:
            try:
                chunk = self.raw_queue.get(timeout=0.1)
                has_chunk = True
            except queue.Empty:
                chunk = None
                has_chunk = False

            now = time.time()

            if has_chunk:
                rms = float(np.sqrt(np.mean(chunk**2) + 1e-12))
                if rms >= self.speech_threshold:
                    is_speaking = True
                    last_speech_time = now
                    utterance_chunks.append(chunk)

                    # Periodically transcribe interim partial audio while speaking (every ~350ms)
                    total_samples = sum(len(c) for c in utterance_chunks)
                    if (
                        total_samples >= 6400  # >= 0.4s audio
                        and (now - last_interim_transcribe_time) >= 0.35
                    ):
                        last_interim_transcribe_time = now
                        audio_arr = np.concatenate(utterance_chunks)
                        try:
                            interim_text = self.stt_engine.transcribe(audio_arr)
                            if interim_text:
                                self.event_queue.put(("stt_interim", interim_text))
                        except Exception:
                            pass
                elif is_speaking:
                    # In between words
                    utterance_chunks.append(chunk)

            # Check for silence timeout to finalize
            if is_speaking and (now - last_speech_time) >= self.silence_timeout:
                if utterance_chunks:
                    audio_arr = np.concatenate(utterance_chunks)
                    utterance_chunks.clear()
                    is_speaking = False

                    if len(audio_arr) >= 6400:
                        try:
                            final_text = self.stt_engine.transcribe(audio_arr)
                            if final_text:
                                self.event_queue.put(("stt_final", final_text))
                            else:
                                self.event_queue.put(("stt_interim_clear", ""))
                        except Exception:
                            self.event_queue.put(("stt_interim_clear", ""))
                    else:
                        self.event_queue.put(("stt_interim_clear", ""))
                else:
                    is_speaking = False

        # On shutdown, finalize any pending speech
        if utterance_chunks:
            audio_arr = np.concatenate(utterance_chunks)
            if len(audio_arr) >= 6400:
                try:
                    final_text = self.stt_engine.transcribe(audio_arr)
                    if final_text:
                        self.event_queue.put(("stt_final", final_text))
                except Exception:
                    pass
