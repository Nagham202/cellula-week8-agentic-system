import sys
import time

import torch
from qwen_asr import Qwen3ASRModel

device = sys.argv[1] if len(sys.argv) > 1 else "mps"
dtype = torch.bfloat16 if device != "cpu" else torch.float32

start = time.perf_counter()
model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-1.7B",
    dtype=dtype,
    device_map=device,
    max_inference_batch_size=1,
    max_new_tokens=256,
)
print(f"Loaded on {device} ({dtype}) in {time.perf_counter() - start:.1f} s")

start = time.perf_counter()
results = model.transcribe(
    audio="https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav",
    language=None,
)
print(f"Transcribed in {time.perf_counter() - start:.1f} s")
print("Language:", results[0].language)
print("Text:", results[0].text)
