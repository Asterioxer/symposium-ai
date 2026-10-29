"""
Audio Recorder Module for Parakeet AI Prototype.
Captures microphone audio using sounddevice and provides live audio level updates.
"""

import threading
import numpy as np
import sounddevice as sd


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream = None
        self.audio_chunks = []
        self.is_recording = False
        self._lock = threading.Lock()
        self.current_level = 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invoked by PortAudio for each incoming audio block."""
        if not self.is_recording:
            return

        # Take channel 0 if multiple channels were captured
        if indata.ndim > 1:
            chunk = indata[:, 0].copy()
        else:
            chunk = indata.flatten().copy()

        with self._lock:
            self.audio_chunks.append(chunk)

        # Compute Root Mean Square (RMS) for the volume meter
        rms = float(np.sqrt(np.mean(chunk**2) + 1e-12))
        # Responsive scaling for visual meter
        scaled_level = min(1.0, rms * 25.0)
        self.current_level = 0.25 * self.current_level + 0.75 * scaled_level

    def start(self):
        """Starts recording audio from default input device."""
        with self._lock:
            self.audio_chunks.clear()
            self.is_recording = True
            self.current_level = 0.0

        # Query default input device channels
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
            blocksize=1024,
        )
        self.stream.start()

    def stop(self) -> np.ndarray:
        """Stops recording and returns the concatenated 1D float32 numpy audio array."""
        self.is_recording = False
        self.current_level = 0.0

        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        with self._lock:
            if not self.audio_chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self.audio_chunks, axis=0).flatten().astype(np.float32)
            self.audio_chunks.clear()
            return audio

    def get_level(self) -> float:
        """Returns the current smoothed audio volume level (0.0 to 1.0)."""
        return self.current_level if self.is_recording else 0.0


if __name__ == "__main__":
    import time
    print("Testing AudioRecorder for 1 second...")
    recorder = AudioRecorder()
    recorder.start()
    for _ in range(5):
        time.sleep(0.2)
        print(f"Level: {recorder.get_level():.4f}")
    data = recorder.stop()
    print(f"Recorded samples: {len(data)}, duration: {len(data)/16000:.2f}s")
