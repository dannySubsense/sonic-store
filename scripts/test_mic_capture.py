#!/usr/bin/env python3
"""Standalone mic capture test — requires a real microphone.

Usage: python3 scripts/test_mic_capture.py

Captures 3 audio chunks via MicIngestion, prints shape/dtype/range,
and verifies the output contract.
"""

import queue
import time
import sys

import numpy as np

from src.ingestion.mic import MicIngestion, CHUNK_SAMPLES


def main() -> None:
    print("=== MicIngestion Test ===")
    print("This test requires a microphone. Speak or play audio near the mic.")
    print()

    q: queue.Queue[np.ndarray] = queue.Queue()
    mic = MicIngestion(output_queue=q)

    try:
        mic.start()
    except Exception as e:
        print(f"ERROR: Could not start microphone: {e}")
        print("On macOS, grant microphone permission in System Settings > Privacy.")
        sys.exit(1)

    print("Waiting for 3 chunks (should take ~3 seconds)...")
    chunks = []
    timeout = 10.0
    start = time.time()

    while len(chunks) < 3 and (time.time() - start) < timeout:
        try:
            chunk = q.get(timeout=1.0)
            chunks.append(chunk)
            print(f"  Chunk {len(chunks)}: shape={chunk.shape}, dtype={chunk.dtype}, "
                  f"min={chunk.min():.4f}, max={chunk.max():.4f}")
        except queue.Empty:
            continue

    mic.stop()

    if len(chunks) < 3:
        print(f"\nFAIL: Only received {len(chunks)} chunks in {timeout}s")
        sys.exit(1)

    # Verify output contract
    print("\n--- Verification ---")
    all_ok = True

    for i, chunk in enumerate(chunks):
        if chunk.shape != (CHUNK_SAMPLES,):
            print(f"FAIL: Chunk {i+1} shape is {chunk.shape}, expected ({CHUNK_SAMPLES},)")
            all_ok = False
        if chunk.dtype != np.float32:
            print(f"FAIL: Chunk {i+1} dtype is {chunk.dtype}, expected float32")
            all_ok = False
        if chunk.min() < -1.0 or chunk.max() > 1.0:
            print(f"WARN: Chunk {i+1} values outside [-1, 1]: min={chunk.min()}, max={chunk.max()}")

    # Check overlap: chunks should share data due to ring buffer
    if len(chunks) >= 2:
        # The second half of chunk 1 should approximately equal the first half of chunk 2
        half = CHUNK_SAMPLES // 2
        overlap_corr = np.corrcoef(chunks[0][half:], chunks[1][:half])[0, 1]
        print(f"Overlap correlation (chunk1 second half vs chunk2 first half): {overlap_corr:.4f}")
        if overlap_corr > 0.9:
            print("OK: Ring buffer overlap is working correctly")
        else:
            print("WARN: Low overlap correlation — ring buffer may not be overlapping correctly")

    if all_ok:
        print("\nPASS: All checks passed")
    else:
        print("\nFAIL: Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
