#!/usr/bin/env python3
"""Load WAV files from a directory and POST them to SonicStore /analyze endpoint.

Usage:
    python3 scripts/demo_loader.py --dir demo/ --interval 0.5
    python3 scripts/demo_loader.py  # defaults: demo/, 0.5s interval
"""

import argparse
import sys
import time
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Load demo WAV files into SonicStore")
    parser.add_argument("--dir", default="demo", help="Directory containing WAV files")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between uploads")
    parser.add_argument("--url", default="http://localhost:8000", help="SonicStore base URL")
    args = parser.parse_args()

    demo_dir = Path(args.dir)
    if not demo_dir.is_dir():
        print(f"Error: {demo_dir} is not a directory")
        sys.exit(1)

    wav_files = sorted(demo_dir.glob("*.wav"))
    if not wav_files:
        print(f"Error: No WAV files found in {demo_dir}")
        sys.exit(1)

    print(f"Found {len(wav_files)} WAV files in {demo_dir}")
    print(f"Uploading to {args.url}/analyze with {args.interval}s interval\n")

    client = httpx.Client(timeout=30.0)

    for i, wav_path in enumerate(wav_files, 1):
        print(f"[{i}/{len(wav_files)}] {wav_path.name}...", end=" ", flush=True)

        with open(wav_path, "rb") as f:
            resp = client.post(
                f"{args.url}/analyze",
                files={"file": (wav_path.name, f, "audio/wav")},
            )

        if resp.status_code == 200:
            data = resp.json()
            bpm = data.get("bpm", "?")
            key_pc = data.get("key_pitch_class", 0)
            key_mode = data.get("key_mode", "?")
            key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            key_name = key_names[key_pc % 12]
            print(f"OK — BPM={bpm:.0f}, Key={key_name} {key_mode}")
        else:
            print(f"FAILED ({resp.status_code}: {resp.text})")

        if i < len(wav_files):
            time.sleep(args.interval)

    client.close()
    print(f"\nDone. {len(wav_files)} files loaded.")


if __name__ == "__main__":
    main()
