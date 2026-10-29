"""
Local Speech-to-Text (STT) Engine for Parakeet AI Prototype.
Powered by faster-whisper with automatic GPU (CUDA) DLL discovery and CPU fallback.
"""

import os
import sys
import logging
import numpy as np

# Ensure Windows finds cuBLAS and CUDA DLLs from PyTorch / NVIDIA wheels
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
        """Loads the faster-whisper model and verifies encode functionality."""
        dummy_audio = np.zeros(16000, dtype=np.float32)

        if self.prefer_cuda:
            try:
                # Attempt to initialize and test encode on CUDA
                model_cuda = WhisperModel(self.model_size, device="cuda", compute_type="float16")
                # Test encode immediately to verify cuBLAS DLL availability
                segs, _ = model_cuda.transcribe(dummy_audio)
                list(segs)

                self.model = model_cuda
                self.device = "cuda"
                self.compute_type = "float16"
                logger.info(f"Initialized {self.model_size} successfully on CUDA float16.")
                return
            except Exception as e:
                logger.warning(f"CUDA initialization or cuBLAS test failed ({e}). Falling back to CPU int8...")

        # Fallback to CPU int8
        try:
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            # Quick verification
            segs, _ = self.model.transcribe(dummy_audio)
            list(segs)
            self.device = "cpu"
            self.compute_type = "int8"
            logger.info(f"Initialized {self.model_size} on CPU int8.")
        except Exception as e:
            logger.error(f"Failed to load Whisper on CPU: {e}")
            raise

    def get_device_info(self) -> str:
        """Returns human-readable engine status string."""
        dev_upper = self.device.upper()
        return f"Whisper {self.model_size} ({dev_upper} - {self.compute_type})"

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribes a 1D float32 numpy audio array at 16000Hz.
        Applies volume normalization and VAD with fallback.
        """
        if self.model is None:
            raise RuntimeError("Whisper model is not initialized.")

        if audio is None or len(audio) < 1600:  # Less than 0.1s
            return ""

        # Ensure float32
        audio = audio.astype(np.float32)

        # Normalize audio volume: boost quiet microphone signals
        max_amp = np.max(np.abs(audio))
        if max_amp > 1e-4:
            # Scale audio so peak is around 0.85 (boost quiet voices without clipping)
            scale = min(100.0, 0.85 / max_amp)
            audio = audio * scale

        # First pass: try with Voice Activity Detection (VAD)
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
        except Exception as e:
            logger.warning(f"VAD transcription pass failed ({e}), falling back to direct pass...")

        # Second pass fallback: without VAD filter in case speech was quiet or soft
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
            logger.error(f"Fallback transcription error: {e}")
            raise


if __name__ == "__main__":
    print("Testing upgraded SpeechToTextEngine...")
    engine = SpeechToTextEngine("tiny.en")
    print("Device Info:", engine.get_device_info())
    print("STT Engine initialized and verified successfully!")
