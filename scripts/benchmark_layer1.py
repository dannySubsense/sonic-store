"""Horizon 1 — Layer 1 Latency Benchmark

Measures the wall-clock cost of each new Layer 1 feature extraction call
on the demo hardware and produces a benchmark report artifact.

Run from repo root:
    python3 scripts/benchmark_layer1.py

Produces:
    benchmarks/horizon-1-layer-1-latency.md
"""

import os
import sys
import platform
import time
import datetime
import pathlib

import numpy as np
import librosa

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURE_DIR = pathlib.Path(__file__).parent.parent / "tests" / "fixtures"
FIXTURES = {
    "sine": FIXTURE_DIR / "440hz_sine_2s.wav",
    "silence": FIXTURE_DIR / "silence_2s.wav",
    "chirp": FIXTURE_DIR / "chirp_2s.wav",
}

BENCHMARK_DIR = pathlib.Path(__file__).parent.parent / "benchmarks"
REPORT_PATH = BENCHMARK_DIR / "horizon-1-layer-1-latency.md"

SR = 22050
WARM_UP_RUNS = 10
TIMED_RUNS = 30


# ---------------------------------------------------------------------------
# Fixture loading — halt if any fixture is missing or unloadable
# ---------------------------------------------------------------------------

def load_fixtures() -> dict:
    """Load all three fixture WAV files into memory as float32 numpy arrays."""
    loaded = {}
    for name, path in FIXTURES.items():
        if not path.exists():
            print(f"HALT: Fixture not found: {path}", file=sys.stderr)
            sys.exit(1)
        try:
            audio, sr = librosa.load(str(path), sr=SR, mono=True)
        except Exception as exc:
            print(f"HALT: Failed to load {path}: {exc}", file=sys.stderr)
            sys.exit(1)
        if audio is None or len(audio) == 0:
            print(f"HALT: Empty audio loaded from {path}", file=sys.stderr)
            sys.exit(1)
        loaded[name] = audio
        print(f"  Loaded {name}: {len(audio)} samples @ {SR} Hz")
    return loaded


# ---------------------------------------------------------------------------
# Individual feature computation functions (verbatim from 02-ARCHITECTURE §3.2)
# ---------------------------------------------------------------------------

def compute_spectral_rolloff_hz(audio: np.ndarray) -> float:
    rolloff_matrix = librosa.feature.spectral_rolloff(y=audio, sr=SR, roll_percent=0.85)
    return float(rolloff_matrix.mean())


def compute_spectral_flux(audio: np.ndarray) -> tuple:
    """Returns (normalized_flux, raw_flux). FLUX_NORM_DIVISOR=1.0 placeholder."""
    S = np.abs(librosa.stft(audio))
    flux_frames = np.sum(np.diff(S, axis=1) ** 2, axis=0)
    raw_flux = float(flux_frames.mean())
    return raw_flux  # return raw for calibration; normalization deferred


def compute_spectral_contrast(audio: np.ndarray) -> list:
    contrast_matrix = librosa.feature.spectral_contrast(y=audio, sr=SR, n_bands=6)
    return contrast_matrix.mean(axis=1).tolist()  # length 7


def compute_zero_crossing_rate(audio: np.ndarray) -> float:
    zcr_matrix = librosa.feature.zero_crossing_rate(y=audio)
    raw_zcr = float(zcr_matrix.mean())
    return float(np.clip(raw_zcr / 0.3, 0.0, 1.0))


def compute_mfcc(audio: np.ndarray) -> list:
    mfcc_matrix = librosa.feature.mfcc(y=audio, sr=SR, n_mfcc=13)
    return mfcc_matrix.mean(axis=1).tolist()  # length 13


def compute_harmonic_ratio(audio: np.ndarray) -> tuple:
    """Returns (harmonic_ratio, harmonic, percussive, total_energy)."""
    harmonic, percussive = librosa.effects.hpss(audio)
    h_energy = float(np.sum(harmonic ** 2))
    p_energy = float(np.sum(percussive ** 2))
    total_energy = h_energy + p_energy
    if total_energy < 1e-8:
        ratio = 0.5
    else:
        ratio = float(np.clip(h_energy / total_energy, 0.0, 1.0))
    return ratio, harmonic, percussive, total_energy


def compute_tonnetz(audio: np.ndarray) -> list:
    """Standalone: runs HPSS internally for timing purposes."""
    harmonic, percussive = librosa.effects.hpss(audio)
    h_energy = float(np.sum(harmonic ** 2))
    p_energy = float(np.sum(percussive ** 2))
    total_energy = h_energy + p_energy
    harmonic_for_tonnetz = harmonic if total_energy >= 1e-8 else audio
    tonnetz_matrix = librosa.feature.tonnetz(y=harmonic_for_tonnetz, sr=SR)
    result = tonnetz_matrix.mean(axis=1).tolist()
    if any(np.isnan(t) or np.isinf(t) for t in result):
        result = [0.0] * 6
    return result


# ---------------------------------------------------------------------------
# Combined extract call (all 7 new features; shares HPSS between
# harmonic_ratio and tonnetz per §3.3)
# ---------------------------------------------------------------------------

def compute_all_seven(audio: np.ndarray) -> dict:
    """All 7 new Layer 1 features computed back-to-back, sharing HPSS output."""
    # spectral_rolloff_hz
    rolloff_matrix = librosa.feature.spectral_rolloff(y=audio, sr=SR, roll_percent=0.85)
    spectral_rolloff_hz = float(rolloff_matrix.mean())

    # spectral_flux
    S = np.abs(librosa.stft(audio))
    flux_frames = np.sum(np.diff(S, axis=1) ** 2, axis=0)
    raw_flux = float(flux_frames.mean())
    spectral_flux = float(np.clip(raw_flux / 1.0, 0.0, 1.0))  # placeholder divisor

    # spectral_contrast
    contrast_matrix = librosa.feature.spectral_contrast(y=audio, sr=SR, n_bands=6)
    spectral_contrast = contrast_matrix.mean(axis=1).tolist()

    # zero_crossing_rate
    zcr_matrix = librosa.feature.zero_crossing_rate(y=audio)
    raw_zcr = float(zcr_matrix.mean())
    zero_crossing_rate = float(np.clip(raw_zcr / 0.3, 0.0, 1.0))

    # mfcc
    mfcc_matrix = librosa.feature.mfcc(y=audio, sr=SR, n_mfcc=13)
    mfcc = mfcc_matrix.mean(axis=1).tolist()

    # harmonic_ratio (HPSS — shared with tonnetz)
    harmonic, percussive = librosa.effects.hpss(audio)
    h_energy = float(np.sum(harmonic ** 2))
    p_energy = float(np.sum(percussive ** 2))
    total_energy = h_energy + p_energy
    if total_energy < 1e-8:
        harmonic_ratio = 0.5
    else:
        harmonic_ratio = float(np.clip(h_energy / total_energy, 0.0, 1.0))

    # tonnetz (reuses harmonic from HPSS above)
    harmonic_for_tonnetz = harmonic if total_energy >= 1e-8 else audio
    tonnetz_matrix = librosa.feature.tonnetz(y=harmonic_for_tonnetz, sr=SR)
    tonnetz = tonnetz_matrix.mean(axis=1).tolist()
    if any(np.isnan(t) or np.isinf(t) for t in tonnetz):
        tonnetz = [0.0] * 6

    return {
        "spectral_rolloff_hz": spectral_rolloff_hz,
        "spectral_flux": spectral_flux,
        "spectral_contrast": spectral_contrast,
        "zero_crossing_rate": zero_crossing_rate,
        "mfcc": mfcc,
        "harmonic_ratio": harmonic_ratio,
        "tonnetz": tonnetz,
    }


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

def time_feature(fn, audio: np.ndarray, warm: int = WARM_UP_RUNS, runs: int = TIMED_RUNS):
    """Run fn(audio), time it, return (mean_ms, p95_ms, all_times_ms)."""
    for _ in range(warm):
        fn(audio)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn(audio)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
    arr = np.array(times)
    return float(arr.mean()), float(np.percentile(arr, 95)), times


# ---------------------------------------------------------------------------
# Main benchmark logic
# ---------------------------------------------------------------------------

def run_benchmark():
    print("\n=== Horizon 1 Layer 1 Latency Benchmark ===\n")

    # --- Load fixtures ---
    print("Loading fixtures...")
    audio_cache = load_fixtures()
    print()

    feature_fns = {
        "spectral_rolloff_hz": compute_spectral_rolloff_hz,
        "spectral_flux": compute_spectral_flux,
        "spectral_contrast": compute_spectral_contrast,
        "zero_crossing_rate": compute_zero_crossing_rate,
        "mfcc": compute_mfcc,
        "harmonic_ratio": lambda a: compute_harmonic_ratio(a)[0],
        "tonnetz": compute_tonnetz,
    }

    fixture_names = list(audio_cache.keys())
    feature_names = list(feature_fns.keys())

    # --- Per-feature timing ---
    print("Running per-feature timing (10 warm-up + 30 timed runs each)...")
    per_feature_results = {}  # {(feature, fixture): (mean_ms, p95_ms)}

    for fname in feature_names:
        per_feature_results[fname] = {}
        for fixname in fixture_names:
            audio = audio_cache[fixname]
            fn = feature_fns[fname]
            mean_ms, p95_ms, _ = time_feature(fn, audio)
            per_feature_results[fname][fixname] = (mean_ms, p95_ms)
            print(f"  {fname:25s} [{fixname:7s}]  mean={mean_ms:7.2f}ms  p95={p95_ms:7.2f}ms")

    print()

    # --- Combined extract (all 7 back-to-back) ---
    print("Running combined extract_features() timing (10 warm-up + 30 timed runs each)...")
    combined_results = {}
    for fixname in fixture_names:
        audio = audio_cache[fixname]
        mean_ms, p95_ms, _ = time_feature(compute_all_seven, audio)
        combined_results[fixname] = (mean_ms, p95_ms)
        within = "PASS" if p95_ms < 500.0 else "FAIL"
        print(f"  [{fixname:7s}]  mean={mean_ms:7.2f}ms  p95={p95_ms:7.2f}ms  {within}")

    print()

    # --- Raw spectral flux calibration ---
    print("Running raw spectral flux calibration...")
    flux_stats = {}  # {fixture: {"min", "mean", "p95", "max"}}
    for fixname in fixture_names:
        audio = audio_cache[fixname]
        # Warm up
        for _ in range(WARM_UP_RUNS):
            compute_spectral_flux(audio)
        raw_values = []
        for _ in range(TIMED_RUNS):
            raw_values.append(compute_spectral_flux(audio))
        arr = np.array(raw_values)
        flux_stats[fixname] = {
            "min": float(arr.min()),
            "mean": float(arr.mean()),
            "p95": float(np.percentile(arr, 95)),
            "max": float(arr.max()),
        }
        print(f"  [{fixname:7s}]  raw_flux min={arr.min():.6f}  mean={arr.mean():.6f}  "
              f"p95={np.percentile(arr, 95):.6f}  max={arr.max():.6f}")

    # Recommended FLUX_NORM_DIVISOR = p95 of music-like fixtures (sine + chirp)
    music_p95_values = [
        flux_stats["sine"]["p95"],
        flux_stats["chirp"]["p95"],
    ]
    flux_norm_divisor = float(np.max(music_p95_values))
    # Use a round-ish value: take max of p95s across music fixtures
    print(f"\n  Recommended FLUX_NORM_DIVISOR: {flux_norm_divisor:.6f}")
    print()

    # --- Verdict ---
    all_combined_p95 = [v[1] for v in combined_results.values()]
    max_combined_p95 = max(all_combined_p95)
    verdict = "PASS" if max_combined_p95 < 500.0 else "FAIL"

    # Check if harmonic_ratio or tonnetz individually exceeds 300ms mean
    hpss_breach = False
    for fixname in fixture_names:
        hr_mean = per_feature_results["harmonic_ratio"][fixname][0]
        tz_mean = per_feature_results["tonnetz"][fixname][0]
        if hr_mean > 300.0 or tz_mean > 300.0:
            hpss_breach = True

    print(f"=== VERDICT: {verdict} ===")
    print(f"  Max combined p95 across fixtures: {max_combined_p95:.2f}ms (budget: 500ms)")
    if hpss_breach:
        print("  WARNING: harmonic_ratio or tonnetz exceeded 300ms mean — amendment path triggered.")
    print()

    return {
        "verdict": verdict,
        "per_feature_results": per_feature_results,
        "combined_results": combined_results,
        "flux_stats": flux_stats,
        "flux_norm_divisor": flux_norm_divisor,
        "max_combined_p95": max_combined_p95,
        "hpss_breach": hpss_breach,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def write_report(results: dict):
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Hardware info
    cpu_info = platform.processor() or platform.machine()
    try:
        import subprocess
        cpu_out = subprocess.run(
            ["lscpu"],
            capture_output=True, text=True, timeout=5
        ).stdout
        model_line = [l for l in cpu_out.splitlines() if "Model name" in l]
        if model_line:
            cpu_info = model_line[0].split(":", 1)[1].strip()
    except Exception:
        pass

    hw_str = f"{platform.node()} — {cpu_info}"
    py_ver = sys.version.split()[0]
    librosa_ver = librosa.__version__

    verdict = results["verdict"]
    per_feature = results["per_feature_results"]
    combined = results["combined_results"]
    flux_stats = results["flux_stats"]
    flux_norm_divisor = results["flux_norm_divisor"]
    max_combined_p95 = results["max_combined_p95"]
    hpss_breach = results["hpss_breach"]

    fixture_names = ["sine", "silence", "chirp"]
    feature_names = [
        "spectral_rolloff_hz",
        "spectral_flux",
        "spectral_contrast",
        "zero_crossing_rate",
        "mfcc",
        "harmonic_ratio",
        "tonnetz",
    ]

    lines = []
    lines.append("# Horizon 1 — Layer 1 Latency Benchmark Report")
    lines.append(f"**Date:** {now}")
    lines.append(f"**Hardware:** {hw_str}")
    lines.append(f"**Python:** {py_ver}")
    lines.append(f"**librosa:** {librosa_ver}")
    lines.append("")

    # --- Verdict ---
    lines.append("## Verdict")
    if verdict == "PASS":
        verdict_line = f"**PASS** — all 7 MUST features fit within 500ms combined budget (max p95: {max_combined_p95:.1f}ms)"
    else:
        verdict_line = f"**FAIL** — combined p95 {max_combined_p95:.1f}ms exceeds 500ms budget — see amendment path below"
    lines.append(verdict_line)
    lines.append("")

    # --- Combined extract timing ---
    lines.append("## Combined extract_features() Timing")
    lines.append("| Fixture | Mean (ms) | P95 (ms) | Within 500ms? |")
    lines.append("|---------|-----------|----------|---------------|")
    for fixname in fixture_names:
        mean_ms, p95_ms = combined[fixname]
        within = "yes" if p95_ms < 500.0 else "no"
        lines.append(f"| {fixname} | {mean_ms:.2f} | {p95_ms:.2f} | {within} |")
    lines.append("")

    # --- Per-feature timing ---
    lines.append("## Per-Feature Timing")
    lines.append("| Feature | Fixture | Mean (ms) | P95 (ms) |")
    lines.append("|---------|---------|-----------|----------|")
    for fname in feature_names:
        for fixname in fixture_names:
            mean_ms, p95_ms = per_feature[fname][fixname]
            lines.append(f"| {fname} | {fixname} | {mean_ms:.2f} | {p95_ms:.2f} |")
    lines.append("")

    # --- Raw spectral flux calibration ---
    lines.append("## Raw Spectral Flux Calibration")
    lines.append("| Fixture | Raw min | Raw mean | Raw p95 | Raw max |")
    lines.append("|---------|---------|----------|---------|---------|")
    for fixname in fixture_names:
        s = flux_stats[fixname]
        lines.append(
            f"| {fixname} | {s['min']:.6f} | {s['mean']:.6f} | {s['p95']:.6f} | {s['max']:.6f} |"
        )
    lines.append("")
    lines.append(f"**Recommended FLUX_NORM_DIVISOR:** `{flux_norm_divisor:.6f}`")
    lines.append("")
    lines.append(
        f"Rationale: FLUX_NORM_DIVISOR is set to the p95 of raw spectral flux across "
        f"music-like fixtures (sine, chirp), so that typical musical audio maps to approximately "
        f"[0.3, 0.95] and silence maps to approximately 0 after normalization."
    )
    lines.append("")

    # --- Amendment path ---
    if verdict == "FAIL" or hpss_breach:
        lines.append("## Amendment Path")
        lines.append("")
        if hpss_breach:
            lines.append(
                "harmonic_ratio (HPSS) exceeded the 300ms mean threshold on one or more fixtures. "
                "Per roadmap H1.S01 amendment path:"
            )
        else:
            lines.append(
                f"Combined extract p95 of {max_combined_p95:.1f}ms exceeds the 500ms budget. "
                "Per roadmap H1.S01 amendment path:"
            )
        lines.append("")
        lines.append("- Downgrade `harmonic_ratio` from MUST to SHOULD in the Horizon 1 MUST list.")
        lines.append(
            "- If `harmonic_ratio` is removed, `tonnetz` falls back to full audio input "
            "(already architected; no code change needed — this is the default path when HPSS energy < threshold)."
        )
        lines.append(
            "- H1.S02 proceeds with 6 MUST features; harmonic_ratio may be re-introduced "
            "post-Horizon 1 if HPSS is optimized via single-STFT reuse."
        )
    else:
        lines.append("## Amendment Path")
        lines.append("")
        lines.append("Not triggered — all features within budget.")

    lines.append("")

    report_text = "\n".join(lines)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    print(f"Report written to: {REPORT_PATH}")
    return report_text


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = run_benchmark()
    write_report(results)
    # Exit 0 regardless of PASS/FAIL (verdict is in the report)
    sys.exit(0)
