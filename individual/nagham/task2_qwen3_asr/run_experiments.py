"""Runs Qwen3-ASR on every clip in data/manifest.csv and saves one result row per clip.

Usage: python run_experiments.py MODEL DEVICE OUTPUT.csv [GROUP ...]
Example: python run_experiments.py Qwen/Qwen3-ASR-1.7B mps results/qwen17_mps.csv
"""
import csv
import re
import sys
import time
from pathlib import Path

import jiwer
import psutil
import torch
from qwen_asr import Qwen3ASRModel
from transformers import WhisperTokenizer
from transformers.models.whisper.english_normalizer import BasicTextNormalizer

model_name, device, output = sys.argv[1], sys.argv[2], Path(sys.argv[3])
groups = set(sys.argv[4:])
dtype = torch.float32 if device == "cpu" else torch.bfloat16

english_normalizer = WhisperTokenizer.from_pretrained("openai/whisper-tiny")
basic_normalizer = BasicTextNormalizer(remove_diacritics=True)


def normalize(text, language):
    # drop non-speech tags in the references, e.g. <LAUGH>, <DTMF>
    text = re.sub(r"<[^>]*>", " ", text)
    if language == "English":
        return english_normalizer.normalize(text)
    return " ".join(basic_normalizer(text).split())


def sync():
    if device == "mps":
        torch.mps.synchronize()


clips = [r for r in csv.DictReader(open("data/manifest.csv", encoding="utf-8"))
         if not groups or r["group"] in groups]
process = psutil.Process()

start = time.perf_counter()
model = Qwen3ASRModel.from_pretrained(model_name, dtype=dtype, device_map=device,
                                      max_inference_batch_size=1, max_new_tokens=2048)
load_time = time.perf_counter() - start
print(f"{model_name} on {device}: loaded in {load_time:.1f} s, {len(clips)} clips")

# one warm-up run so the first timed clip doesn't include one-time setup
model.transcribe(audio=clips[0]["path"], language=None)

peak_rss = 0
results = []
for clip in clips:
    sync()
    start = time.perf_counter()
    result = model.transcribe(audio=clip["path"], language=None)[0]
    sync()
    seconds = time.perf_counter() - start
    peak_rss = max(peak_rss, process.memory_info().rss)

    reference = normalize(clip["reference"], clip["language"])
    hypothesis = normalize(result.text, clip["language"])
    duration = float(clip["duration"])
    row = dict(id=clip["id"], group=clip["group"], condition=clip["condition"], accent=clip["accent"],
               language=clip["language"], detected=result.language, duration=duration,
               seconds=round(seconds, 3), rtf=round(seconds / duration, 4),
               wer=round(jiwer.wer(reference, hypothesis), 4) if reference else "",
               cer=round(jiwer.cer(reference, hypothesis), 4) if reference else "",
               ref_words=len(reference.split()), reference=clip["reference"], hypothesis=result.text)
    results.append(row)
    print(f"{clip['id']:<24} {duration:6.1f} s  time {seconds:6.2f} s  WER {row['wer']}")

output.parent.mkdir(exist_ok=True)
with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

gpu_memory = torch.mps.driver_allocated_memory() / 1e9 if device == "mps" else 0
with open(output.with_suffix(".info.txt"), "w") as f:
    f.write(f"model={model_name}\ndevice={device}\ndtype={dtype}\nload_seconds={load_time:.1f}\n"
            f"peak_process_rss_gb={peak_rss / 1e9:.2f}\nmps_driver_allocated_gb={gpu_memory:.2f}\n")
print(f"Saved {output}  (peak RAM {peak_rss / 1e9:.2f} GB, MPS {gpu_memory:.2f} GB)")
