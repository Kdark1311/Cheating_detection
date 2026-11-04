"""Offline audio check: enrollment file + exam session file -> events.csv + clips.

Usage: uv run python pipeline.py --enroll data/enroll.wav --session data/session.wav
Baseline is segmentation + speaker verification, not a real TS-VAD network.
"""
import argparse
import csv
import math
import resource
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import torch
from pyannote.audio import Audio, Inference, Model
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio.utils.signal import Binarize
from pyannote.core import Segment, SlidingWindowFeature

SR = 16000
SEG_STEP_S = 1.0
EMBED_HOP_S = 5.0  # chunks overlap, so embedding every chunk mostly repeats work on CPU
TARGET, OTHER, UNKNOWN = 0, 1, 2

# Starting values, to be calibrated on real recordings (step 5).
MIN_CLEAN_S = 1.0  # embeddings on less clean speech are unreliable
MIN_OTHER_S = 0.3
MAX_UNKNOWN_S = 0.5
MERGE_GAP_S = 5.0


def normalize(src, dst):
    # No trimming: timestamps must stay those of the original recording.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-ac", "1", "-ar", str(SR), str(dst)], check=True)


def timeline(scores, frames):
    """Aggregate per-chunk (chunks, frames, 1) scores into merged time regions."""
    aggregated = Inference.aggregate(scores, frames, missing=0.0)
    return Binarize(onset=0.5)(aggregated).get_timeline().support()


def detect(seg, frames):
    """Speech and overlap regions from one segmentation pass."""
    any_speaker = seg.data.max(axis=-1, keepdims=True)
    two_speakers = (seg.data.sum(axis=-1, keepdims=True) >= 2).astype(float)
    return (timeline(SlidingWindowFeature(any_speaker, seg.sliding_window), frames),
            timeline(SlidingWindowFeature(two_speakers, seg.sliding_window), frames))


def cosine(a, b):
    a, b = a.ravel(), b.ravel()
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def label_speakers(seg, waveform, embed, enroll, t_high, t_low):
    """Compare local speakers with the enrollment, skipping inactive ones.

    Returns votes (chunks, frames, 3) indexed by TARGET/OTHER/UNKNOWN, with NaN on
    skipped chunks, and one score row per chunk/speaker for threshold calibration.
    """
    window = seg.sliding_window
    n_chunks, n_frames, n_speakers = seg.data.shape
    votes = np.full((n_chunks, n_frames, 3), np.nan)
    overlap = seg.data.sum(axis=-1) >= 2
    n_samples = round(window.duration * SR)
    stride = max(1, round(EMBED_HOP_S / window.step))
    rows = []

    for c in sorted({*range(0, n_chunks, stride), n_chunks - 1}):
        votes[c] = 0.0
        start = window[c].start
        for s in range(n_speakers):
            active = seg.data[c, :, s] > 0
            if not active.any():
                continue
            clean = active & ~overlap[c]
            clean_s = clean.mean() * window.duration
            score = math.nan
            label = UNKNOWN
            if clean_s >= MIN_CLEAN_S:
                begin = round(start * SR)
                wave = waveform[:, begin:begin + n_samples]
                wave = torch.nn.functional.pad(wave, (0, n_samples - wave.shape[1]))
                mask = torch.from_numpy(clean.astype(np.float32))[None]
                score = cosine(embed(wave[None], masks=mask), enroll)
                label = TARGET if score >= t_high else OTHER if score < t_low else UNKNOWN
            votes[c, active, label] = 1.0
            rows.append({"chunk_start": round(start, 2), "local_speaker": s,
                         "clean_s": round(float(clean_s), 2), "cosine": round(score, 3)})
    return votes, rows


def merge_regions(regions, gap):
    """Group sorted (start, end) regions separated by at most `gap` seconds."""
    groups = []
    for region in regions:
        if groups and region[0] - groups[-1][-1][1] <= gap:
            groups[-1].append(region)
        else:
            groups.append([region])
    return groups


def decide(target_s, other_s, unknown_s, overlap_s, rms_db, quiet_db):
    """Skip only when sure it is the candidate alone; anything doubtful gets a human."""
    if other_s >= MIN_OTHER_S:
        return "flag", "alternating" if target_s >= MIN_OTHER_S else "other_speaker"
    if overlap_s > 0:
        return "review", "overlap"
    if rms_db < quiet_db:
        return "review", "quiet"
    if unknown_s > MAX_UNKNOWN_S or target_s == 0:
        return "review", "unclear_speaker"
    return "ignore", "candidate_only"


def rms_db(wave):
    return 20 * math.log10(float(wave.square().mean().sqrt()) + 1e-9)


def build_events(speech, overlap, votes, seg, frames, waveform, quiet_db):
    aggregated = Inference.aggregate(SlidingWindowFeature(votes, seg.sliding_window),
                                     frames, missing=0.0)
    events = []
    for group in merge_regions([(r.start, r.end) for r in speech], MERGE_GAP_S):
        decided = np.zeros((0, 3))
        loudness = []
        for start, end in group:
            decided = np.vstack([decided, aggregated.crop(Segment(start, end)) >= 0.5])
            loudness.append(rms_db(waveform[:, round(start * SR):round(end * SR)]))
        target_s, other_s = decided[:, [TARGET, OTHER]].sum(axis=0) * frames.step
        unknown_s = (~decided[:, [TARGET, OTHER]].any(axis=1)).sum() * frames.step
        span = Segment(group[0][0], group[-1][1])
        overlap_s = overlap.crop(span, mode="intersection").duration()
        # The quietest turn decides: a whisper must not be averaged away by louder speech.
        decision, reason = decide(target_s, other_s, unknown_s, overlap_s, min(loudness), quiet_db)
        events.append({"start": round(span.start, 2), "end": round(span.end, 2),
                       "decision": decision, "reason": reason, "clip": ""})
    return events


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enroll", required=True, type=Path)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--t-high", type=float, default=0.65, help="cosine >= this: candidate")
    parser.add_argument("--t-low", type=float, default=0.5, help="cosine < this: someone else")
    parser.add_argument("--quiet-db", type=float, default=-45.0)
    args = parser.parse_args()
    out = args.out or Path("outputs") / args.session.stem
    (out / "clips").mkdir(parents=True, exist_ok=True)

    began = time.perf_counter()
    torch.set_num_threads(4)  # physical cores
    audio = Audio(sample_rate=SR, mono="downmix")
    embed = PretrainedSpeakerEmbedding("pyannote/wespeaker-voxceleb-resnet34-LM",
                                       device=torch.device("cpu"))
    model = Model.from_pretrained("pyannote/segmentation-3.0", token=True)

    with tempfile.TemporaryDirectory() as tmp:
        enroll_wav, session_wav = Path(tmp, "enroll.wav"), Path(tmp, "session.wav")
        normalize(args.enroll, enroll_wav)
        normalize(args.session, session_wav)

        enroll = embed(audio(enroll_wav)[0][None])
        # shortcut: whole session stays in RAM (~690 MB for 3 h), read by window if files get longer.
        waveform = audio(session_wav)[0]
        seconds = waveform.shape[1] / SR

        seg = Inference(model, step=SEG_STEP_S, skip_aggregation=True)(
            {"waveform": waveform, "sample_rate": SR})
        frames = model.receptive_field
        speech, overlap = detect(seg, frames)
        votes, rows = label_speakers(seg, waveform, embed, enroll, args.t_high, args.t_low)
        events = build_events(speech, overlap, votes, seg, frames, waveform, args.quiet_db)

        for i, event in enumerate(e for e in events if e["decision"] != "ignore"):
            event["clip"] = f"clips/{i:04d}_{event['decision']}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(event["start"]),
                            "-to", str(event["end"]), "-i", str(session_wav),
                            str(out / event["clip"])], check=True)

    write_csv(out / "events.csv", events, ["start", "end", "decision", "reason", "clip"])
    write_csv(out / "scores.csv", rows, ["chunk_start", "local_speaker", "clean_s", "cosine"])

    elapsed = time.perf_counter() - began
    peak_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2
    print(f"{seconds:.0f}s audio in {elapsed:.0f}s ({elapsed / seconds:.2f}x), "
          f"peak RAM {peak_gb:.2f} GB, {len(events)} events -> {out}")


if __name__ == "__main__":
    main()
