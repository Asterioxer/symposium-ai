import os
import sys
import logging
import numpy as np

# Add PyTorch's lib folder to DLL search path on Windows so CTranslate2 can load cuBLAS
try:
    import torch
    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if hasattr(os, "add_dll_directory") and os.path.exists(torch_lib):
        os.add_dll_directory(torch_lib)
    os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class SpeechToTextEngine:
    def __init__(self, model_size: str = "tiny.en", prefer_cuda: bool = True):
        self.model_size = model_size
        self.prefer_cuda = prefer_cuda
        self.model = None
        self.device = "cpu"
        self.compute_type = "int8"
        self._load_model()

    def _load_model(self):
        dummy_audio = np.zeros(16000, dtype=np.float32)

        if self.prefer_cuda:
            try:
                # Test encode immediately to make sure cuBLAS DLLs are actually loadable
                model_cuda = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                segs, _ = model_cuda.transcribe(dummy_audio)
                list(segs)

                self.model = model_cuda
                self.device = "cuda"
                self.compute_type = "float16"
                return
            except Exception as e:
                logger.warning(f"CUDA failed ({e}), falling back to CPU.")

        # Fallback to CPU int8
        try:
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            segs, _ = self.model.transcribe(dummy_audio)
            list(segs)
            self.device = "cpu"
            self.compute_type = "int8"
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def get_device_info(self) -> str:
        return f"Whisper {self.model_size} ({self.device.upper()} {self.compute_type})"

    def transcribe(self, audio: np.ndarray) -> str:
        if self.model is None:
            raise RuntimeError("Whisper model is not initialized.")

        if audio is None or len(audio) < 1600:
            return ""

        audio = audio.astype(np.float32)

        # Normalize gain so low-volume laptop mics can be transcribed reliably
        max_amp = np.max(np.abs(audio))
        if max_amp > 1e-4:
            scale = min(100.0, 0.85 / max_amp)
            audio = audio * scale

        # First pass with voice activity detection
        try:
            segments, _ = self.model.transcribe(
                audio,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
                language="en" if self.model_size.endswith(".en") else None,
            )
            texts = [s.text.strip() for s in segments if s.text.strip()]
            transcription = " ".join(texts).strip()
            if transcription:
                return transcription
        except Exception:
            pass

        # Fallback pass without VAD if audio was quiet or filtered out
        try:
            segments, _ = self.model.transcribe(
                audio,
                beam_size=5,
                vad_filter=False,
                language="en" if self.model_size.endswith(".en") else None,
            )
            texts = [s.text.strip() for s in segments if s.text.strip()]
            return " ".join(texts).strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise


if __name__ == "__main__":
    engine = SpeechToTextEngine("tiny.en")
    print("STT Engine:", engine.get_device_info())
