"""Build a labelled demo from pyannote's bundled sample: data/demo/{enroll.wav,demo.wav,labels.csv}.

Usage: uv run python make_demo.py
Spliced from a 2-speaker phone call, so it shows the pipeline works, not how accurate it is.
"""
import csv
import subprocess
from pathlib import Path

import numpy as np
from pyannote.audio.sample import SAMPLE_FILE

SR = 16000
GAP_S = 7.0  # longer than the pipeline's merge gap, so each scene stays its own event
OUT = Path("data/demo")


def write_wav(path, samples):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                    "-i", "pipe:0", str(path)], input=samples.astype(np.float32).tobytes(), check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wave = SAMPLE_FILE["waveform"][0].numpy()
    cut = lambda start, end: wave[round(start * SR):round(end * SR)]

    # Enrollment turns are kept apart from the turns used in the session.
    enroll = np.concatenate([cut(8.35, 9.9), cut(18.6, 21.45), cut(28.5, 30.0)])
    # Only clean turns: speaker90 starts at 10.57 s but speaker91 talks over it until 11.03 s.
    candidate, other, other_long = cut(11.05, 14.45), cut(14.75, 17.9), cut(21.8, 27.8)
    silence = np.zeros(round(SR))
    n = min(len(candidate), len(other))
    scenes = [
        ("candidate", candidate),
        ("other", other),
        ("alternating", np.concatenate([candidate, silence, other_long])),
        ("overlap", candidate[:n] + other[:n]),
        ("short_other", cut(7.55, 8.3)),
        ("quiet", candidate * 10 ** (-30 / 20)),
        ("candidate", candidate),
    ]

    gap = np.zeros(round(GAP_S * SR))
    parts, labels, now = [gap], [], GAP_S
    for label, audio in scenes:
        end = now + len(audio) / SR
        labels.append({"start": round(now, 2), "end": round(end, 2), "label": label})
        parts += [audio, gap]
        now = end + GAP_S
    session = np.concatenate(parts)
    session += np.random.default_rng(0).normal(0, 10 ** (-65 / 20), len(session))  # real rooms are never digital zero

    write_wav(OUT / "enroll.wav", enroll)
    write_wav(OUT / "demo.wav", session)
    with open(OUT / "labels.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start", "end", "label"])
        writer.writeheader()
        writer.writerows(labels)
    print(f"{len(enroll) / SR:.1f}s enrollment, {len(session) / SR:.0f}s session -> {OUT}")


if __name__ == "__main__":
    main()
