"""Voice samples for picking: same sentence, several Kokoro voices -> samples/<voice>.m4a"""
import subprocess
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
OUT.mkdir(exist_ok=True)
TEXT = "Hey there, it's Jarvis. On it, one second. Done, it's on your list. Anything else?"
VOICES = ["af_heart", "af_bella", "am_michael", "bf_isabella", "bf_emma",
          "am_adam", "bm_george", "bm_fable", "am_eric"]

k = Kokoro(str(ROOT / "models/kokoro-v1.0.onnx"), str(ROOT / "models/voices-v1.0.bin"))
for v in VOICES:
    lang = "en-gb" if v.startswith("b") else "en-us"
    audio, sr = k.create(TEXT, voice=v, speed=1.0, lang=lang)
    wav = OUT / f"{v}.wav"
    sf.write(wav, audio, sr)
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-c:a", "aac", "-b:a", "96k", str(OUT / f"{v}.m4a")], check=True)
    wav.unlink()
    print(v, f"{len(audio)/sr:.1f}s")
