# SonicStore — Feature Horizons
**Version:** 1.0
**Date:** 2026-04-16
**Status:** DRAFT — drives future spec/forge sprints
**Author:** Quincy (Technical Director) + Danny (Composer)

---

## 0. Context

SonicStore v1 extracts 6 standard MIR features from audio and uses 4 of them to condition MusicGen prompts. These features are well-known, hand-picked by researchers decades ago. They describe *acoustic properties* — not musical *intent*.

The v1 feedback loop (human plays → features extracted → AI generates → human responds) creates a dataset nobody else is collecting: paired interaction data between a musician and a generative model in real time. This document defines three horizons for mining that data.

Each horizon builds on the previous one. Each is spec-able, forgeable, and independently valuable.

---

## 1. Horizon 0 — Standard Features (COMPLETE)

**What we have now.** The v1 feature set.

| Feature | Source | Dimensionality | Used In |
|---------|--------|---------------|---------|
| chroma | `librosa.feature.chroma_cqt` | 12 | UI heatmap |
| bpm | `librosa.beat.beat_track` | 1 | Prompt: tempo descriptor |
| key | Krumhansl-Schmuckler on chroma | 2 (pitch_class + mode) | Prompt: key name |
| rms_energy | `librosa.feature.rms` | 1 | Prompt: energy descriptor |
| spectral_centroid | `librosa.feature.spectral_centroid` | 1 | Prompt: timbre descriptor |
| onset_strength | `librosa.onset.onset_strength` | 1 | UI display |
| mel_spectrogram | `librosa.feature.melspectrogram` | 128×T | Available, not rendered |

**Prompt uses 4 features.** Chroma drives key detection but isn't directly in the prompt. Onset strength and mel spectrogram are extracted but not used for generation conditioning.

**Data captured per chunk:** 1 FeatureVector (13 keys), stored in history ring (30 entries).

---

## 2. Horizon 1 — Derivative Features

**What:** Features computed from the *time series* of feature vectors, not from raw audio. The history ring already stores 30 snapshots. This is signal sitting on the table.

**Analogy:** Horizon 0 is the price. Horizon 1 is momentum, volatility, and rate of change.

**When:** Post-hackathon. Weeks of work. No new ML models required — pure computation on existing data.

### Candidate Derivative Features

| Feature | Computation | What It Captures |
|---------|-------------|-----------------|
| delta_bpm | `bpm[t] - bpm[t-1]` | Tempo acceleration/deceleration |
| bpm_volatility | `std(bpm[-N:])` | Rhythmic stability vs. exploration |
| energy_momentum | Slope of `rms_energy` over last N chunks | Building energy vs. winding down |
| energy_regime | Classify trajectory as rising/falling/stable | Macro dynamic arc |
| chroma_entropy | `scipy.stats.entropy(chroma)` | Harmonic complexity (low = single note, high = dense harmony) |
| chroma_volatility | `std(chroma[-N:], axis=0).mean()` | Harmonic stability vs. exploration |
| key_stability | Fraction of last N chunks in the same key | Whether the musician is staying in key or modulating |
| spectral_trend | Slope of `spectral_centroid` over last N chunks | Timbre shifting brighter or darker |
| onset_regularity | Autocorrelation of `onset_strength` series | Rhythmic regularity vs. rubato |

### Impact on Generation

The prompt builder becomes richer. Instead of:

```
"upbeat balanced musical accompaniment, 124 BPM, D minor,
 complementary to the input melody, instrumental"
```

It becomes:

```
"accelerating toward 130 BPM with building energy,
 harmonically stable in D minor, brightening timbre,
 complementary to the input melody, instrumental"
```

The generation doesn't just match the current state — it responds to *where the music is going*.

### Architecture Impact

- **Feature store:** No schema change needed. Derivative features are computed at read time or as a post-processing step before prompt building. They don't need to be stored — they're derived from the history ring.
- **Prompt builder:** Extend `build_prompt()` to accept derivative features. New descriptor functions for trajectory terms.
- **UI:** New dashboard elements for trends (spark lines, direction arrows).
- **Store:** May want to extend history beyond 30 entries for longer-window computations. Configurable via `HISTORY_MAX_ENTRIES`.

### Spec Scope

One spec, one forge sprint. Estimated 3-4 slices:
1. Derivative feature computation module
2. Extended prompt builder with trajectory descriptors
3. UI trend indicators
4. Tests covering all derivative features + prompt integration

---

## 3. Horizon 2 — Learned Features

**What:** Representation learning on audio chunks to discover latent features that the standard MIR features don't capture. Instead of asking "what are the acoustics?" ask "what does this audio *mean* in the context of this interaction?"

**Analogy:** Horizon 0 is fundamental analysis. Horizon 1 is technical analysis. Horizon 2 is discovering new factors that the market (standard MIR) hasn't priced in. Sonic alpha.

**When:** Months of work. Requires collecting interaction data, training a model, evaluating whether learned features improve generation quality.

### Approach

**Data collection first.** Every SonicStore session generates tuples of:
- Input audio chunk (raw waveform)
- Extracted feature vector
- Generated prompt
- Generated audio (output)
- Implicit feedback: did the musician keep playing? Did their energy increase? Did they change key toward the AI's key?

This interaction data is the training set. Nobody else has it.

**Candidate methods:**

| Method | What It Learns | Complexity |
|--------|---------------|-----------|
| Contrastive learning (SimCLR-style) | Audio embeddings where "similar musical moments" cluster together | Medium |
| Variational autoencoder on feature vectors | Compressed latent space; discover which dimensions carry the most information | Low-medium |
| Next-chunk prediction | Features that predict what the musician plays next (i.e., musical intention) | Medium-high |
| Response quality predictor | Given (features, prompt, generated_audio), predict whether the musician's subsequent playing "engages" (energy up, session continues) | High — requires labeled data |

**The key insight:** Standard MIR features describe the audio. Learned features can describe the *musician's state* — are they exploring, consolidating, building toward a climax, losing interest? These are the features that would make generation actually feel responsive.

### Architecture Impact

- **New module:** `src/features/learned.py` — inference only (training happens offline)
- **Feature vector:** Extended with learned dimensions (e.g., `latent_embedding: list[float]`)
- **Prompt builder:** Learned features map to new descriptor vocabulary or directly influence generation parameters (temperature, top_k)
- **Data pipeline:** New module to log full interaction sessions for offline training
- **Model serving:** Lightweight — the learned model is a small encoder, not MusicGen-sized

### Spec Scope

Multiple sprints. Data collection infra first (log sessions), then training pipeline, then integration. Estimated 8-12 slices across 3-4 specs.

---

## 4. Horizon 3 — Interaction Features (Agentic Prosthetic)

**What:** Features that describe the *relationship* between human and AI, not either one in isolation. The system models the conversation, not just the audio.

**Analogy:** Horizons 0-2 analyze each player. Horizon 3 analyzes the game.

**When:** Long-term research direction. This is the north star from `research/AGENTIC-PROSTHETIC.md`. It doesn't have a timeline because it's genuinely novel.

### Candidate Interaction Features

| Feature | What It Captures |
|---------|-----------------|
| harmonic_convergence | Are human and AI moving toward the same key? Measured as distance between human's key and AI's last generated key over time |
| call_response_latency | How quickly does the musician respond to the AI's generation? Shorter = more engaged |
| energy_mirroring | Correlation between human energy trajectory and AI energy. Are they in sync? |
| novelty_seeking | Is the musician repeating patterns or exploring new territory after hearing the AI? |
| influence_direction | Is the human leading the AI or following it? Measured by who changes key/tempo first |
| session_arc | Macro structure of the interaction: intro → exploration → climax → resolution? Or chaotic? |
| surprise_response | When the AI generates something unexpected (key change, tempo shift), does the musician follow, resist, or amplify? |

### What This Enables

The generation engine stops being reactive and becomes *anticipatory*. It doesn't just match your current state — it shapes the trajectory of the conversation. If it detects the musician is building toward a climax, it can build with them. If it detects exploration, it can offer unexpected harmonic material. If it detects fatigue, it can simplify.

This is the Agentic Prosthetic: the AI isn't a tool you operate, it's a collaborator that has a model of the relationship.

### Architecture Impact

- **Session model:** A persistent representation of the current interaction that updates on each cycle. Not just the latest feature vector — the full history, both sides.
- **Generation strategy:** The prompt builder is replaced or augmented by a strategy layer that chooses *what kind* of response to generate (supportive, challenging, surprising, simplifying).
- **New store requirements:** Full session logging, both human and AI chunks, with timestamps and causal links.
- **Research infrastructure:** A/B testing framework for interaction strategies. Evaluation metrics for "good" musical conversations.

### Spec Scope

Research-grade. Multiple specs, each requiring its own research contract. This is where the white paper lives.

---

## 5. Dependency Map

```
Horizon 0 (COMPLETE)
    │
    ▼
Horizon 1 — Derivative Features
    │  requires: history ring data (already exists)
    │  unlocks: trajectory-aware prompts
    │
    ▼
Horizon 2 — Learned Features
    │  requires: interaction data logging (new infra)
    │  requires: offline training pipeline (new infra)
    │  unlocks: intent-aware features, sonic alpha
    │
    ▼
Horizon 3 — Interaction Features
    │  requires: Horizon 2 learned representations
    │  requires: session modeling (new architecture)
    │  unlocks: anticipatory generation, the Agentic Prosthetic
```

Horizon 1 is immediately actionable from the current codebase. Horizon 2 requires data infrastructure. Horizon 3 requires Horizon 2's outputs plus new research.

---

## 6. Next Steps

1. **Ship v1** — the working skeleton. All 11 slices. (DONE)
2. **Spec Horizon 1** — derivative features are low-hanging fruit with high impact on generation quality. One spec, one forge sprint.
3. **Build interaction logging** — even before Horizon 2 is spec'd, start capturing full session data. Every session is training data you'll want later.
4. **Play with it** — Danny plays with v1, notices what the AI gets right and wrong, identifies what features would fix the gaps. The musician's intuition guides the feature mining.

---

*Horizons document by: Quincy (Technical Director)*
*For: Danny (Composer) — driving future spec/forge sprints*
*Status: DRAFT — ready for Danny's review and prioritization*
