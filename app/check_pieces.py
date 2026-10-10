"""A1 check: Kokoro speaks, Whisper hears it back. Each piece alone, with timings."""
import re
import resource
import time
from pathlib import Path

import mlx_whisper
import numpy as np
import soundfile as sf
import soxr
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
OUT = ROOT / "samples"
OUT.mkdir(exist_ok=True)

WHISPER = "mlx-community/whisper-large-v3-turbo"
TEXT = ("Good morning. Today you have one work block, a call with a client, "
        "and a short walk after lunch. Recovery comes first, the rest fits around it.")


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", "", s.lower()).split())


def peak_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9  # bytes on macOS


def transcribe(audio16: np.ndarray) -> str:
    return mlx_whisper.transcribe(audio16, path_or_hf_repo=WHISPER, language="en")["text"].strip()


def main():
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    kokoro.create("Warm up.", voice="af_heart", speed=1.0, lang="en-us")
    t = time.perf_counter()
    audio, sr = kokoro.create(TEXT, voice="af_heart", speed=1.0, lang="en-us")
    tts_s = time.perf_counter() - t
    dur = len(audio) / sr
    wav = OUT / "_check.wav"
    sf.write(wav, audio, sr)
    print(f"Kokoro said: {TEXT}")
    print(f"Kokoro: {dur:.1f}s audio in {tts_s:.2f}s -> {tts_s / dur:.3f} s compute per s audio (warm)")

    a16 = soxr.resample(audio.astype(np.float32), sr, 16000)
    clip = a16[: 5 * 16000]  # ~5 s clip for the latency number
    t = time.perf_counter(); transcribe(clip); cold = time.perf_counter() - t
    t = time.perf_counter(); transcribe(clip); warm = time.perf_counter() - t
    print(f"Whisper 5 s clip: first run {cold:.2f}s (includes model load), second (warm) run {warm:.2f}s")

    t = time.perf_counter(); heard = transcribe(a16); full = time.perf_counter() - t
    print(f"Whisper heard ({dur:.1f}s audio, {full:.2f}s): {heard}")
    ok = norm(heard) == norm(TEXT)
    print(f"Match (ignoring case/punctuation): {ok}")
    print(f"Peak memory of this process: {peak_gb():.2f} GB")


if __name__ == "__main__":
    main()
