# Nagham Taweel – Week 8 Individual Work

My individual tasks for Week 8 of the Cellula Technologies NLP & AI internship.
The team work (Tasks 5 and 6) is in the main project folders (`src/`, `api/`, `infra/`).

| Task | Topic | Folder | Status |
|---|---|---|---|
| 0 | Kimi K2 architecture analysis (IEEE paper) | [task0_kimi_k2/](task0_kimi_k2/) | Done |
| 1 | Qwen2.5-72B architecture analysis (IEEE paper) | [task1_qwen25/](task1_qwen25/) | Done |
| 2 | Qwen3-ASR-1.7B for speech-to-text (IEEE report with experiments) | [task2_qwen3_asr/](task2_qwen3_asr/) | Done |
| 3 | Generative Adversarial Networks (IEEE report) | [task3_gans/](task3_gans/) | Not started |
| 4 | Updated CV | [task4_cv/](task4_cv/) | Not started |

## Task 0: Kimi K2 Architecture Analysis

A three-page IEEE two-column paper on the architecture of Kimi K2 (Moonshot AI): the Mixture-of-Experts design,
Multi-head Latent Attention, MuonClip training, inference cost, benchmarks, and a comparison with DeepSeek-V3.

| File | What it is |
|---|---|
| [Kimi_K2_Architecture_Analysis.pdf](task0_kimi_k2/Kimi_K2_Architecture_Analysis.pdf) | The final paper |
| [main.tex](task0_kimi_k2/main.tex) | LaTeX source (IEEEtran conference template, figure drawn with TikZ) |
| [references.bib](task0_kimi_k2/references.bib) | BibTeX references, IEEE style |

Built in Overleaf. Main source: the Kimi K2 technical report (arXiv:2507.20534).

## Task 1: Qwen2.5-72B Architecture Analysis

A three-page IEEE two-column paper on Qwen2.5-72B (Qwen Team, Alibaba): the decoder architecture, grouped query
attention, RoPE and long-context extension (YaRN, DCA), the SwiGLU FFN, tokenization, training and post-training
(SFT, DPO, GRPO), inference cost, and benchmarks against Qwen2-72B and Llama-3.1-405B.

| File | What it is |
|---|---|
| [Qwen2_5_72B_Architecture_Analysis.pdf](task1_qwen25/Qwen2_5_72B_Architecture_Analysis.pdf) | The final paper |
| [main.tex](task1_qwen25/main.tex) | LaTeX source (IEEEtran conference template, figure drawn with TikZ) |
| [references.bib](task1_qwen25/references.bib) | BibTeX references, IEEE style |

Built in Overleaf. Main source: the Qwen2.5 technical report (arXiv:2412.15115).

## Task 2: Qwen3-ASR-1.7B for Speech-to-Text

A three-page IEEE report on Qwen3-ASR-1.7B with experiments actually run on an Apple M4 Pro laptop: 72 clips
(different speakers, 12 accents, Egyptian Arabic, added noise, recordings up to 5 minutes), WER/CER, speed and
memory, compared with Qwen3-ASR-0.6B and Whisper large-v3-turbo.

| File | What it is |
|---|---|
| [Qwen3_ASR_Report.pdf](task2_qwen3_asr/Qwen3_ASR_Report.pdf) | The final report |
| [README.md](task2_qwen3_asr/README.md) | Results summary, scripts, and how to reproduce the experiments |
| [results/summary.md](task2_qwen3_asr/results/summary.md) | All measured tables |
