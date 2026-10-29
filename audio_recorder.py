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
        if not self.is_recording:
            return

        if indata.ndim > 1:
            chunk = indata[:, 0].copy()
        else:
            chunk = indata.flatten().copy()

        with self._lock:
            self.audio_chunks.append(chunk)

        # Calculate volume level for the mic meter
        rms = float(np.sqrt(np.mean(chunk**2) + 1e-12))
        scaled_level = min(1.0, rms * 25.0)
        self.current_level = 0.25 * self.current_level + 0.75 * scaled_level

    def start(self):
        with self._lock:
            self.audio_chunks.clear()
            self.is_recording = True
            self.current_level = 0.0

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
        return self.current_level if self.is_recording else 0.0


if __name__ == "__main__":
    import time
    recorder = AudioRecorder()
    recorder.start()
    time.sleep(1)
    data = recorder.stop()
    print(f"Recorded {len(data)} samples ({len(data)/16000:.2f}s)")
