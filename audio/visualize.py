"""Write report.html: a self-contained timeline with playable audio, viewed locally."""
import base64
import json
import subprocess
from pathlib import Path

import numpy as np

SR = 16000
N_PEAKS = 1000


def ffmpeg_stdout(*args):
    return subprocess.run(["ffmpeg", "-loglevel", "error", *args], check=True, capture_output=True).stdout


def peaks(wav):
    samples = np.frombuffer(ffmpeg_stdout("-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"),
                            dtype=np.float32)
    bins = np.array_split(np.abs(samples), N_PEAKS)
    return [round(float(b.max()), 3) if len(b) else 0.0 for b in bins], len(samples) / SR


def write_report(out, wav, name, regions, events, scores, t_high, t_low, stats, labels=None, metrics=None, note=None):
    wave, seconds = peaks(wav)
    mp3 = ffmpeg_stdout("-i", str(wav), "-ac", "1", "-b:a", "64k", "-f", "mp3", "pipe:1")
    data = {"name": name, "seconds": seconds, "peaks": wave, "regions": regions, "events": events,
            "scores": scores, "tHigh": t_high, "tLow": t_low, "stats": stats,
            "labels": labels, "metrics": metrics, "note": note}
    template = (Path(__file__).parent / "report_template.html").read_text()
    html = (template.replace("__NAME__", name)
            .replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
            .replace("__AUDIO__", base64.b64encode(mp3).decode()))
    (out / "report.html").write_text(html)
