"""Baseline: Whisper large-v3-turbo (faster-whisper, CPU int8) on the same clips, scored the same way.

Usage: python run_whisper.py results/whisper_turbo_cpu.csv
"""
import csv
import re
import sys
import time
from pathlib import Path

import jiwer
import psutil
import soundfile as sf
from faster_whisper import WhisperModel
from transformers import WhisperTokenizer
from transformers.models.whisper.english_normalizer import BasicTextNormalizer

output = Path(sys.argv[1])
english_normalizer = WhisperTokenizer.from_pretrained("openai/whisper-tiny")
basic_normalizer = BasicTextNormalizer(remove_diacritics=True)


def normalize(text, language):
    # drop non-speech tags in the references, e.g. <LAUGH>, <DTMF>
    text = re.sub(r"<[^>]*>", " ", text)
    if language == "English":
        return english_normalizer.normalize(text)
    return " ".join(basic_normalizer(text).split())


clips = list(csv.DictReader(open("data/manifest.csv", encoding="utf-8")))
start = time.perf_counter()
model = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")
load_time = time.perf_counter() - start
list(model.transcribe(sf.read(clips[0]["path"], dtype="float32")[0])[0])

process = psutil.Process()
peak_rss = 0
results = []
for clip in clips:
    start = time.perf_counter()
    segments, info = model.transcribe(sf.read(clip["path"], dtype="float32")[0], beam_size=1)
    text = " ".join(s.text.strip() for s in segments)
    seconds = time.perf_counter() - start
    peak_rss = max(peak_rss, process.memory_info().rss)

    reference = normalize(clip["reference"], clip["language"])
    hypothesis = normalize(text, clip["language"])
    duration = float(clip["duration"])
    row = dict(id=clip["id"], group=clip["group"], condition=clip["condition"], accent=clip["accent"],
               language=clip["language"], detected=info.language, duration=duration,
               seconds=round(seconds, 3), rtf=round(seconds / duration, 4),
               wer=round(jiwer.wer(reference, hypothesis), 4), cer=round(jiwer.cer(reference, hypothesis), 4),
               ref_words=len(reference.split()), reference=clip["reference"], hypothesis=text)
    results.append(row)
    print(f"{clip['id']:<24} {duration:6.1f} s  time {seconds:6.2f} s  WER {row['wer']}")

output.parent.mkdir(exist_ok=True)
with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)
with open(output.with_suffix(".info.txt"), "w") as f:
    f.write(f"model=faster-whisper-large-v3-turbo\ndevice=cpu\ncompute_type=int8\n"
            f"load_seconds={load_time:.1f}\npeak_process_rss_gb={peak_rss / 1e9:.2f}\n")
print(f"Saved {output}  (peak RAM {peak_rss / 1e9:.2f} GB)")
