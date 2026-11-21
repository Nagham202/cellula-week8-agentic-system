"""Turns results/*.csv into summary tables (results/summary.md) and the report figure (figures/results.png)."""
import csv
import re
from pathlib import Path

import jiwer
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from transformers import WhisperTokenizer
from transformers.models.whisper.english_normalizer import BasicTextNormalizer

english_normalizer = WhisperTokenizer.from_pretrained("openai/whisper-tiny")
basic_normalizer = BasicTextNormalizer(remove_diacritics=True)


def normalize(text, language):
    # drop non-speech tags in the references, e.g. <LAUGH>, <DTMF>
    text = re.sub(r"<[^>]*>", " ", text)
    if language == "English":
        return english_normalizer.normalize(text)
    return " ".join(basic_normalizer(text).split())


RUNS = {"Qwen3-ASR-1.7B (MPS)": "results/qwen17_mps.csv",
        "Qwen3-ASR-0.6B (MPS)": "results/qwen06_mps.csv",
        "Whisper-v3-turbo (CPU)": "results/whisper_turbo_cpu.csv",
        "Qwen3-ASR-1.7B (CPU)": "results/qwen17_cpu.csv"}
GROUPS = ["librispeech_clean", "librispeech_other", "fleurs_en_us", "edacc_accents", "fleurs_ar_eg",
          "noise", "duration"]
runs = {name: list(csv.DictReader(open(path, encoding="utf-8"))) for name, path in RUNS.items() if Path(path).exists()}


def corpus(rows):
    refs = [normalize(r["reference"], r["language"]) for r in rows]
    hyps = [normalize(r["hypothesis"], r["language"]) for r in rows]
    audio = sum(float(r["duration"]) for r in rows)
    seconds = sum(float(r["seconds"]) for r in rows)
    return 100 * jiwer.wer(refs, hyps), 100 * jiwer.cer(refs, hyps), seconds / audio


lines = ["# Results", "", "## WER / CER (%) per group", ""]
lines.append("| Group | " + " | ".join(runs) + " |")
lines.append("|---|" + "---|" * len(runs))
for group in GROUPS:
    cells = []
    for rows in runs.values():
        subset = [r for r in rows if r["group"] == group]
        cells.append("{:.2f} / {:.2f}".format(*corpus(subset)[:2]) if subset else "-")
    lines.append(f"| {group} | " + " | ".join(cells) + " |")

lines += ["", "## Speed (all clips each run covered)", "", "| Run | Clips | Audio (s) | Time (s) | RTF | Info |",
          "|---|---|---|---|---|---|"]
for name, rows in runs.items():
    _, _, rtf = corpus(rows)
    info = Path(RUNS[name]).with_suffix(".info.txt").read_text().replace("\n", "; ")
    lines.append(f"| {name} | {len(rows)} | {sum(float(r['duration']) for r in rows):.0f} | "
                 f"{sum(float(r['seconds']) for r in rows):.1f} | {rtf:.3f} | {info} |")

lines += ["", "## Noise (WER % by SNR)", ""]
snrs = ["snr20dB", "snr10dB", "snr5dB", "snr0dB"]
lines.append("| Run | clean | " + " | ".join(snrs) + " |")
lines.append("|---|---|" + "---|" * len(snrs))
noise_wer = {}
for name, rows in runs.items():
    clean_ids = {r["id"].split("_snr")[0] for r in rows if r["group"] == "noise"}
    clean = [r for r in rows if r["id"] in clean_ids]
    values = [corpus(clean)[0] if clean else None] + \
             [corpus([r for r in rows if r["condition"] == s])[0] if any(r["condition"] == s for r in rows) else None
              for s in snrs]
    noise_wer[name] = values
    lines.append(f"| {name} | " + " | ".join("-" if v is None else f"{v:.2f}" for v in values) + " |")

lines += ["", "## Long clips", "", "| Run | Clip | Duration (s) | Time (s) | RTF | WER % |", "|---|---|---|---|---|---|"]
for name, rows in runs.items():
    for r in rows:
        if r["group"] == "duration":
            lines.append(f"| {name} | {r['id']} | {r['duration']} | {r['seconds']} | {r['rtf']} | "
                         f"{corpus([r])[0]:.2f} |")

lines += ["", "## Language identification", ""]
for name, rows in runs.items():
    correct = sum(r["detected"].lower().startswith(r["language"].lower()[:2]) for r in rows)
    lines.append(f"- {name}: {correct}/{len(rows)} clips detected as the right language")

lines += ["", "## Accents (WER % per clip)", "", "| Accent | " + " | ".join(runs) + " |", "|---|" + "---|" * len(runs)]
first = next(iter(runs.values()))
for r in [r for r in first if r["group"] == "edacc_accents"]:
    cells = []
    for rows in runs.values():
        match = [x for x in rows if x["id"] == r["id"]]
        cells.append(f"{corpus(match)[0]:.1f}" if match else "-")
    lines.append(f"| {r['accent']} | " + " | ".join(cells) + " |")

Path("results/summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

# figure: WER vs SNR (left) and processing time vs audio length (right)
Path("figures").mkdir(exist_ok=True)
fig, (left, right) = plt.subplots(1, 2, figsize=(7, 2.6))
x_labels = ["clean", "20", "10", "5", "0"]
for name, values in noise_wer.items():
    if all(v is not None for v in values):
        left.plot(x_labels, values, marker="o", label=name.replace(" (MPS)", "").replace(" (CPU)", ""))
left.set_xlabel("SNR (dB)")
left.set_ylabel("WER (%)")
left.set_title("Added white noise")
left.legend(fontsize=7)
left.grid(alpha=0.3)
for name, rows in runs.items():
    long_rows = sorted([r for r in rows if r["group"] == "duration"], key=lambda r: float(r["duration"]))
    if long_rows:
        right.plot([float(r["duration"]) for r in long_rows], [float(r["seconds"]) for r in long_rows],
                   marker="o", label=name)
right.set_xlabel("Audio length (s)")
right.set_ylabel("Processing time (s)")
right.set_title("Long recordings")
right.legend(fontsize=7)
right.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("figures/results.pdf")
fig.savefig("figures/results.png", dpi=200)
print("Saved figures/results.pdf")
