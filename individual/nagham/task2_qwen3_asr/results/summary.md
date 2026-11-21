# Results

## WER / CER (%) per group

| Group | Qwen3-ASR-1.7B (MPS) | Qwen3-ASR-0.6B (MPS) | Whisper-v3-turbo (CPU) | Qwen3-ASR-1.7B (CPU) |
|---|---|---|---|---|
| librispeech_clean | 1.23 / 0.45 | 1.65 / 0.53 | 0.82 / 0.30 | 1.23 / 0.45 |
| librispeech_other | 0.69 / 0.13 | 0.69 / 0.33 | 1.04 / 0.47 | - |
| fleurs_en_us | 2.56 / 0.77 | 3.85 / 1.54 | 4.49 / 1.43 | - |
| edacc_accents | 10.59 / 7.41 | 10.00 / 8.06 | 12.94 / 9.36 | - |
| fleurs_ar_eg | 10.76 / 2.65 | 16.46 / 3.75 | 12.03 / 3.53 | - |
| noise | 3.63 / 1.87 | 6.05 / 3.60 | 5.04 / 2.72 | - |
| duration | 3.54 / 1.68 | 7.42 / 3.68 | 1.77 / 0.67 | - |

## Speed (all clips each run covered)

| Run | Clips | Audio (s) | Time (s) | RTF | Info |
|---|---|---|---|---|---|
| Qwen3-ASR-1.7B (MPS) | 72 | 1181 | 119.6 | 0.101 | model=Qwen/Qwen3-ASR-1.7B; device=mps; dtype=torch.bfloat16; load_seconds=7.4; peak_process_rss_gb=1.03; mps_driver_allocated_gb=9.00;  |
| Qwen3-ASR-0.6B (MPS) | 72 | 1181 | 74.3 | 0.063 | model=Qwen/Qwen3-ASR-0.6B; device=mps; dtype=torch.bfloat16; load_seconds=138.0; peak_process_rss_gb=2.10; mps_driver_allocated_gb=6.34;  |
| Whisper-v3-turbo (CPU) | 72 | 1181 | 778.0 | 0.658 | model=faster-whisper-large-v3-turbo; device=cpu; compute_type=int8; load_seconds=1.3; peak_process_rss_gb=2.92;  |
| Qwen3-ASR-1.7B (CPU) | 10 | 92 | 22.2 | 0.241 | model=Qwen/Qwen3-ASR-1.7B; device=cpu; dtype=torch.float32; load_seconds=10.0; peak_process_rss_gb=9.38; mps_driver_allocated_gb=0.00;  |

## Noise (WER % by SNR)

| Run | clean | snr20dB | snr10dB | snr5dB | snr0dB |
|---|---|---|---|---|---|
| Qwen3-ASR-1.7B (MPS) | 1.61 | 1.61 | 1.61 | 4.03 | 7.26 |
| Qwen3-ASR-0.6B (MPS) | 2.42 | 2.42 | 3.23 | 6.45 | 12.10 |
| Whisper-v3-turbo (CPU) | 0.81 | 0.81 | 1.61 | 4.03 | 13.71 |
| Qwen3-ASR-1.7B (CPU) | - | - | - | - | - |

## Long clips

| Run | Clip | Duration (s) | Time (s) | RTF | WER % |
|---|---|---|---|---|---|
| Qwen3-ASR-1.7B (MPS) | long_30s | 47.27 | 4.133 | 0.0874 | 0.00 |
| Qwen3-ASR-1.7B (MPS) | long_60s | 72.09 | 6.252 | 0.0867 | 0.53 |
| Qwen3-ASR-1.7B (MPS) | long_120s | 123.97 | 11.485 | 0.0926 | 1.55 |
| Qwen3-ASR-1.7B (MPS) | long_300s | 305.02 | 33.1 | 0.1085 | 5.54 |
| Qwen3-ASR-0.6B (MPS) | long_30s | 47.27 | 2.571 | 0.0544 | 0.79 |
| Qwen3-ASR-0.6B (MPS) | long_60s | 72.09 | 3.941 | 0.0547 | 0.53 |
| Qwen3-ASR-0.6B (MPS) | long_120s | 123.97 | 7.236 | 0.0584 | 1.24 |
| Qwen3-ASR-0.6B (MPS) | long_300s | 305.02 | 21.198 | 0.0695 | 12.39 |
| Whisper-v3-turbo (CPU) | long_30s | 47.27 | 14.583 | 0.3085 | 0.00 |
| Whisper-v3-turbo (CPU) | long_60s | 72.09 | 19.684 | 0.273 | 0.53 |
| Whisper-v3-turbo (CPU) | long_120s | 123.97 | 29.872 | 0.241 | 0.93 |
| Whisper-v3-turbo (CPU) | long_300s | 305.02 | 76.846 | 0.2519 | 2.65 |

## Language identification

- Qwen3-ASR-1.7B (MPS): 72/72 clips detected as the right language
- Qwen3-ASR-0.6B (MPS): 72/72 clips detected as the right language
- Whisper-v3-turbo (CPU): 72/72 clips detected as the right language
- Qwen3-ASR-1.7B (CPU): 10/10 clips detected as the right language

## Accents (WER % per clip)

| Accent | Qwen3-ASR-1.7B (MPS) | Qwen3-ASR-0.6B (MPS) | Whisper-v3-turbo (CPU) | Qwen3-ASR-1.7B (CPU) |
|---|---|---|---|---|
| Scottish English | 0.0 | 0.0 | 14.3 | - |
| Don't know | 11.1 | 11.1 | 11.1 | - |
| Eastern European | 0.0 | 0.0 | 0.0 | - |
| Mainstream US English | 0.0 | 0.0 | 11.1 | - |
| Chinese | 1.7 | 1.7 | 5.1 | - |
| Catalan | 30.0 | 30.0 | 30.0 | - |
| Spanish | 30.8 | 23.1 | 30.8 | - |
| Bulgarian | 0.0 | 10.0 | 10.0 | - |
| Romanian | 71.4 | 57.1 | 57.1 | - |
| Indian English | 33.3 | 33.3 | 33.3 | - |
| Latin American | 0.0 | 0.0 | 0.0 | - |
| Nigerian English | 15.4 | 15.4 | 15.4 | - |
