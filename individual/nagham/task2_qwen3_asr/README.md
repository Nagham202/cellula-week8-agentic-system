# Task 2: Qwen3-ASR-1.7B for Speech-to-Text

A three-page IEEE report on Qwen3-ASR-1.7B: architecture analysis plus experiments run on an Apple M4 Pro laptop
(26 GB unified memory). All results in the report come from the scripts and result files in this folder.

## Results in short

| Test | Qwen3-ASR-1.7B | Qwen3-ASR-0.6B | Whisper large-v3-turbo |
|---|---|---|---|
| LibriSpeech clean, WER | 1.23% | 1.65% | 0.82% |
| EdAcc accents (12), WER | 10.59% | 10.00% | 12.94% |
| FLEURS Arabic, WER / CER | 10.76% / 2.65% | 16.46% / 3.75% | 12.03% / 3.53% |
| White noise at 0 dB, WER | 7.26% | 12.10% | 13.71% |
| Speed (RTF, lower is faster) | 0.101 (Apple GPU) | 0.063 (Apple GPU) | 0.658 (CPU) |

Full tables: [results/summary.md](results/summary.md). Per-clip transcripts: `results/*.csv`.

## Files

| File | What it does |
|---|---|
| `Qwen3_ASR_Report.pdf` | The final report |
| `main.tex`, `references.bib`, `figures/results.pdf` | LaTeX source of the report |
| `smoke_test.py` | First check that the model loads and transcribes |
| `prepare_data.py` | Builds the 72-clip test set from LibriSpeech, EdAcc and FLEURS, adds noise and long clips |
| `run_experiments.py` | Runs Qwen3-ASR on every clip and records WER, CER, time and memory |
| `run_whisper.py` | Same test with Whisper large-v3-turbo (faster-whisper) as a baseline |
| `summarize.py` | Makes `results/summary.md` and `figures/results.pdf` |
| `results/` | Raw results and run info for each model and device |

## Reproduce

```bash
cd individual/nagham/task2_qwen3_asr
python3.12 -m venv .venv
.venv/bin/pip install -U qwen-asr jiwer soundfile datasets psutil faster-whisper matplotlib
export SSL_CERT_FILE=$(.venv/bin/python -m certifi)   # needed with python.org Python on macOS

.venv/bin/python prepare_data.py                      # downloads the clips into data/ (git-ignored)
.venv/bin/python run_experiments.py Qwen/Qwen3-ASR-1.7B mps results/qwen17_mps.csv
.venv/bin/python run_experiments.py Qwen/Qwen3-ASR-0.6B mps results/qwen06_mps.csv
.venv/bin/python run_whisper.py results/whisper_turbo_cpu.csv
.venv/bin/python run_experiments.py Qwen/Qwen3-ASR-1.7B cpu results/qwen17_cpu.csv librispeech_clean
.venv/bin/python summarize.py
```

The audio clips are not stored in git; `prepare_data.py` downloads them again from the public datasets.
