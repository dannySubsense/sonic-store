#!/usr/bin/env python3
"""Benchmark MusicGen-Small generation time on current hardware.

Usage:
    python3 scripts/benchmark_generation.py

Reports device, model load time, and generation time for a single 10-second clip.
Run before the hackathon to confirm hardware is within budget:
  - RTX 5090: <4s
  - M3 Max (MPS): <6s
  - CPU fallback: ~40s (acceptable with warning)
"""

import time

import torch


def main() -> None:
    # Device selection
    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    print(f"Device: {device}")
    print(f"PyTorch: {torch.__version__}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print()

    # Load model
    print("Loading MusicGen-Small...")
    t0 = time.time()

    from audiocraft.models import MusicGen

    model = MusicGen.get_pretrained("facebook/musicgen-small")
    model.set_generation_params(duration=10, use_sampling=True, top_k=250, temperature=1.0)

    if device == "cuda":
        model = model.half()

    load_time = time.time() - t0
    print(f"Model loaded in {load_time:.1f}s")
    print()

    # Generate
    prompt = "upbeat balanced musical accompaniment, 120 BPM, D minor, complementary to the input melody, instrumental"
    print(f"Prompt: {prompt}")
    print("Generating 10s clip...")

    t1 = time.time()
    with torch.no_grad():
        output = model.generate([prompt])
    gen_time = time.time() - t1

    samples = output.shape[-1]
    duration = samples / 32000.0

    print(f"Generated {duration:.1f}s audio in {gen_time:.1f}s")
    print()

    # Verdict
    if device == "cuda" and gen_time < 4.0:
        print("PASS: Within CUDA budget (<4s)")
    elif device == "mps" and gen_time < 6.0:
        print("PASS: Within MPS budget (<6s)")
    elif device == "cpu" and gen_time < 60.0:
        print("WARN: CPU fallback — generation works but is slow")
    elif gen_time < 8.0:
        print("PASS: Within total loop budget (<8s)")
    else:
        print(f"SLOW: {gen_time:.1f}s exceeds budget — consider reducing MUSICGEN_DURATION")


if __name__ == "__main__":
    main()
