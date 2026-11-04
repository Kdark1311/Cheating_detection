"""Model-free checks. Run: uv run python test_pipeline.py"""
import numpy as np
import torch
from pyannote.core import SlidingWindow, SlidingWindowFeature

from evaluate import score
from pipeline import OTHER, SR, TARGET, UNKNOWN, build_events, decide, detect, label_speakers, merge_regions, split_turns

Q = -45.0
# Every row of the plan's decision table, plus the doubtful cases around it.
assert decide(10, 0, 0, 0, -20, Q) == ("ignore", "candidate_only")
assert decide(0, 3, 0, 0, -20, Q) == ("flag", "other_speaker")
assert decide(5, 3, 0, 0, -20, Q) == ("flag", "alternating")
assert decide(5, 3, 0, 1, -20, Q) == ("flag", "alternating")
assert decide(5, 0, 0, 1, -20, Q) == ("review", "overlap")
assert decide(5, 0, 0, 0, -60, Q) == ("review", "quiet")
assert decide(5, 0, 2, 0, -20, Q) == ("review", "unclear_speaker")
assert decide(0, 3, 0, 0, -60, Q) == ("review", "quiet")  # too quiet to trust the voice match
assert decide(0, 0, 0.4, 0, -20, Q) == ("review", "unclear_speaker")  # short prompt is never skipped

assert merge_regions([], 5) == []
assert merge_regions([(0, 1), (4, 5), (11, 12)], 5) == [[(0, 1), (4, 5)], [(11, 12)]]
assert merge_regions([(0, 1), (6, 7)], 5) == [[(0, 1), (6, 7)]]  # exactly at the gap

assert [list(t) for t in split_turns(np.array([1, 1, 0, 1, 0, 0, 0, 1], bool), 2)] == [[0, 1, 3], [7]]

# 30 s session: candidate 2-8 s, someone else 14-18 s.
frames = SlidingWindow(start=0.0, duration=0.0619, step=0.0169)
n_frames = 589
window = SlidingWindow(start=0.0, duration=10.0, step=1.0)
n_chunks = 21
data = np.zeros((n_chunks, n_frames, 3))
for c in range(n_chunks):
    t = window[c].start + np.arange(n_frames) * frames.step
    data[c, :, 0] = (t >= 2) & (t < 8)
    data[c, :, 1] = (t >= 14) & (t < 18)
seg = SlidingWindowFeature(data, window)

# Fake embedder: speaker comes from the waveform sign, so no model is needed.
waveform = torch.full((1, 30 * SR), 0.1)
waveform[:, 12 * SR:] = -0.1
calls = []


def embed(wave, masks):
    assert wave.shape == (1, 1, 10 * SR) and masks.shape == (1, n_frames)
    calls.append(1)
    middle = wave[0, 0, torch.nonzero(masks[0])[0].item() * 270]
    return np.array([[1.0, 0.0]]) if middle > 0 else np.array([[0.0, 1.0]])


votes, rows = label_speakers(seg, waveform, embed, np.array([[1.0, 0.0]]), 0.5, 0.25)
assert np.isnan(votes[1]).all() and not np.isnan(votes[0]).any()  # skipped vs processed chunk
assert not np.isnan(votes[-1]).any()  # last chunk is always processed
assert 0 < len(calls) <= len(rows) < n_chunks * 3  # inactive speakers cost nothing
assert votes[0, :, TARGET].sum() > 0 and votes[10, :, OTHER].sum() > 0

speech, overlap = detect(seg, frames)
assert [round(r.start) for r in speech] == [2, 14] and not list(overlap)
events = build_events(speech, overlap, votes, seg, frames, waveform, Q)
assert [(e["decision"], e["reason"]) for e in events] == [("ignore", "candidate_only"), ("flag", "other_speaker")]

# Overlap and a speaker with too little clean speech go to a human, not to "skip".
data2 = data.copy()
for c in range(n_chunks):
    t = window[c].start + np.arange(n_frames) * frames.step
    data2[c, :, 2] = (t >= 3) & (t < 4)
seg2 = SlidingWindowFeature(data2, window)
speech2, overlap2 = detect(seg2, frames)
assert list(overlap2) and round(list(overlap2)[0].start) == 3
votes2, _ = label_speakers(seg2, waveform, embed, np.array([[1.0, 0.0]]), 0.5, 0.25)
assert np.nansum(votes2[:, :, UNKNOWN]) > 0
assert build_events(speech2, overlap2, votes2, seg2, frames, waveform, Q)[0]["reason"] == "overlap"

# One local speaker ID covering two people across a pause must not blend their voices.
mixed = np.zeros((1, n_frames, 3))
t = np.arange(n_frames) * frames.step
mixed[0, :, 0] = ((t >= 0) & (t < 2)) | ((t >= 7) & (t < 9.9))
mixed_seg = SlidingWindowFeature(mixed, SlidingWindow(start=6.0, duration=10.0, step=1.0))
mixed_votes, mixed_rows = label_speakers(mixed_seg, waveform, embed, np.array([[1.0, 0.0]]), 0.5, 0.25)
assert len(mixed_rows) == 2
assert mixed_votes[0, 50, TARGET] == 1 and mixed_votes[0, 500, OTHER] == 1

result = score(
    [{"start": 0, "end": 5, "decision": "ignore"}, {"start": 10, "end": 12, "decision": "flag"},
     {"start": 20, "end": 21, "decision": "review"}],
    [{"start": 0, "end": 5, "label": "candidate"}, {"start": 10, "end": 12, "label": "other"},
     {"start": 20, "end": 21, "label": "other"}, {"start": 30, "end": 31, "label": "other"}])
assert result["correctly_skipped"] == 1.0
assert result["caught_flag"] == "1/3" and result["caught_flag_or_review"] == "2/3"
assert result["caught_short"] == "1/2" and result["review_events"] == 1

print("ok")
