"""Builds the test set: real clips from public datasets, noisy copies, and long clips.

Output: data/audio/*.wav (16 kHz mono) and data/manifest.csv
"""
import csv
import io
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from datasets import Audio, load_dataset

SR = 16000
OUT = Path("data/audio")
OUT.mkdir(parents=True, exist_ok=True)
rows = []


def load_audio(audio):
    data, sr = sf.read(io.BytesIO(audio["bytes"]), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SR:
        data = librosa.resample(data, orig_sr=sr, target_sr=SR)
    return data


def save(clip_id, audio, group, condition, reference, language, speaker="", accent=""):
    path = OUT / f"{clip_id}.wav"
    sf.write(path, audio, SR)
    rows.append(dict(id=clip_id, group=group, condition=condition, path=str(path),
                     duration=round(len(audio) / SR, 2), reference=reference,
                     language=language, speaker=speaker, accent=accent))


def stream(name, config, split):
    ds = load_dataset(name, config, split=split, streaming=True)
    return iter(ds.cast_column("audio", Audio(decode=False)))


# different speakers, clean and harder recordings: one utterance per speaker, 3-20 s
for config in ["clean", "other"]:
    seen = set()
    for row in stream("openslr/librispeech_asr", config, "test"):
        audio = load_audio(row["audio"])
        if row["speaker_id"] in seen or not 3 <= len(audio) / SR <= 20:
            continue
        seen.add(row["speaker_id"])
        save(f"libri_{config}_{len(seen):02d}", audio, f"librispeech_{config}", config,
             row["text"], "English", speaker=row["speaker_id"])
        if len(seen) == 10:
            break

# accents: one utterance per accent, 3-20 s and at least 6 words
seen = set()
for row in stream("edinburghcstr/edacc", None, "test"):
    if row["accent"] in seen or len(row["text"].split()) < 6:
        continue
    audio = load_audio(row["audio"])
    if not 3 <= len(audio) / SR <= 20:
        continue
    seen.add(row["accent"])
    save(f"edacc_{len(seen):02d}", audio, "edacc_accents", "conversational", row["text"], "English",
         speaker=row["speaker"], accent=row["accent"])
    if len(seen) == 12:
        break

# Arabic and English read speech from FLEURS
for config, language in [("ar_eg", "Arabic"), ("en_us", "English")]:
    count = 0
    for row in stream("google/fleurs", config, "test"):
        audio = load_audio(row["audio"])
        if not 3 <= len(audio) / SR <= 20:
            continue
        count += 1
        save(f"fleurs_{config}_{count:02d}", audio, f"fleurs_{config}", "read", row["transcription"], language,
             speaker=f"gender{row['gender']}")
        if count == 8:
            break

# recording conditions: white noise added to five clean clips at fixed signal-to-noise ratios
rng = np.random.default_rng(0)
clean_rows = [r for r in rows if r["group"] == "librispeech_clean"][:5]
for r in clean_rows:
    audio, _ = sf.read(r["path"], dtype="float32")
    signal_power = np.mean(audio ** 2)
    for snr in [20, 10, 5, 0]:
        noise = rng.normal(0, np.sqrt(signal_power / 10 ** (snr / 10)), len(audio)).astype("float32")
        noisy = np.clip(audio + noise, -1, 1)
        save(f"{r['id']}_snr{snr}", noisy, "noise", f"snr{snr}dB", r["reference"], "English", speaker=r["speaker"])

# durations: consecutive test-clean utterances joined into long clips with 0.3 s gaps
targets = [30, 60, 120, 300]
pieces, texts, total = [], [], 0.0
gap = np.zeros(int(0.3 * SR), dtype="float32")
for row in stream("openslr/librispeech_asr", "clean", "test"):
    audio = load_audio(row["audio"])
    pieces += [audio, gap]
    texts.append(row["text"])
    total += len(audio) / SR + 0.3
    if total >= targets[0]:
        save(f"long_{targets[0]}s", np.concatenate(pieces), "duration", f"{targets[0]}s", " ".join(texts), "English")
        targets.pop(0)
        if not targets:
            break

with open("data/manifest.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved {len(rows)} clips")
for group in dict.fromkeys(r["group"] for r in rows):
    items = [r for r in rows if r["group"] == group]
    print(f"  {group}: {len(items)} clips, {sum(r['duration'] for r in items):.0f} s")
