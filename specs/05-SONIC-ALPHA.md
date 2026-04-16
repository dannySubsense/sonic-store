# SonicStore — Sonic Alpha: Feature Intelligence Framework
**Version:** 1.0
**Date:** 2026-04-16
**Status:** DRAFT — mental model for feature architecture
**Author:** Quincy (Technical Director) + Danny (Composer)

---

## 0. The Quant Analogy (Why This Matters)

In quantitative finance, there's a stack:

```
Raw Data (price, volume)
    ↓
Technical Indicators (MA, RSI, Bollinger — lagging, descriptive)
    ↓
Factor Models (momentum, value, quality — predictive, leading)
    ↓
Alpha Signals (proprietary, from alternative data — prescriptive, unique)
    ↓
Execution (trades)
```

SonicStore v1 currently does this:

```
Raw Audio
    ↓
Feature Extraction (chroma, BPM, energy — lagging, descriptive)
    ↓
Prompt Builder (simple mapping table)
    ↓
Generation (MusicGen)
```

There's no analysis layer. No prediction. No alpha. We go straight from raw measurement to action. That's like reading the ticker tape and immediately placing a trade.

This document defines the four layers of audio intelligence and maps every known feature to its layer.

---

## 1. The Four Layers

### Layer 1: Instantaneous Features (What the audio IS)

**Quant equivalent:** Raw market data — price tick, volume bar, order book snapshot.

**Nature:** Point-in-time measurement of a single audio chunk. No memory. No context. Describes acoustic properties of the current 2-second window.

**Use:** Direct observation. The building block for everything above.

| Feature | Source | Formula / Method | Dim | Ref |
|---------|--------|-----------------|-----|-----|
| **chroma** | `librosa.feature.chroma_cqt` | CQT → pitch class energy distribution | 12 | Brown 1991 [9] |
| **CENS** | `librosa.feature.chroma_cens` | Chroma → log compress → L2 normalize → smooth | 12 | Müller 2015 [17] |
| **bpm** | `librosa.beat.beat_track` | Onset autocorrelation → comb filter → DP | 1 | Ellis 2007 [15] |
| **key** | Krumhansl-Schmuckler | $k^* = \arg\max_k \sum_{p=0}^{11} C[p] \cdot K_k[p]$ | 2 | Krumhansl 1990 |
| **rms_energy** | `librosa.feature.rms` | $\sqrt{\frac{1}{N}\sum x[n]^2}$ | 1 | — |
| **spectral_centroid** | `librosa.feature.spectral_centroid` | $\text{SC} = \frac{\sum_k f_k \cdot \|X[k]\|}{\sum_k \|X[k]\|}$ | 1 | Grey 1977 [14] |
| **spectral_rolloff** | `librosa.feature.spectral_rolloff` | Frequency below which 85% of spectral energy lies | 1 | — |
| **spectral_flux** | frame-to-frame difference | $\text{SF} = \sum_k (\|X_t[k]\| - \|X_{t-1}[k]\|)^2$ | 1 | Bello 2005 [16] |
| **spectral_contrast** | `librosa.feature.spectral_contrast` | $C_b = \log_{10}(\mu_{peak,b} / \mu_{valley,b})$ per octave subband | 7 | — |
| **onset_strength** | `librosa.onset.onset_strength` | Spectral flux with mel scaling + log compression | 1 | Bello 2005 [16] |
| **zero_crossing_rate** | `librosa.feature.zero_crossing_rate` | $\text{ZCR} = \frac{1}{2(N-1)} \sum \|\text{sgn}(x[n]) - \text{sgn}(x[n-1])\|$ | 1 | — |
| **MFCCs** | `librosa.feature.mfcc` | Mel filter bank → log → DCT | 13 | Davis & Mermelstein 1980 [8] |
| **mel_spectrogram** | `librosa.feature.melspectrogram` | $m(f) = 2595 \log_{10}(1 + f/700)$, triangular filter bank | 128×T | — |
| **harmonic_energy** | `librosa.effects.hpss` | Horizontal median filtering on spectrogram | 1 | Fitzgerald 2010 |
| **percussive_energy** | `librosa.effects.hpss` | Vertical median filtering on spectrogram | 1 | Fitzgerald 2010 |
| **tonnetz** | `librosa.feature.tonnetz` | Tonal centroid features (fifths, minor thirds, major thirds) | 6 | Harte 2006 [22] |

**v1 extracts 6 of these.** There are at least 10 more established features with known implementations in librosa. Each one is another dimension of observation.

**What they DON'T tell you:** Where the music is going. Whether it's changing. What the musician intends. They're a photograph, not a movie.

---

### Layer 2: Temporal Indicators (What the audio is DOING)

**Quant equivalent:** Technical indicators — moving averages, Bollinger bands, RSI, MACD. Computed from the time series of raw data. Lagging but informative.

**Nature:** Computed from the *history* of Layer 1 features. Requires a window of past observations. Describes trajectory, stability, volatility.

**Key insight:** The delta-delta formula from speech processing (Davis & Mermelstein 1980) generalizes to ANY feature time series:

$$\Delta f_t = \frac{\sum_{n=1}^{N} n(f_{t+n} - f_{t-n})}{2\sum_{n=1}^{N} n^2}$$

This is a regression-weighted first derivative. Apply it to BPM, energy, centroid — anything.

| Indicator | Computed From | Formula / Method | What It Captures | Quant Analog |
|-----------|--------------|-----------------|-----------------|--------------|
| **delta_bpm** | bpm history | $\Delta f_t$ (delta formula above) | Tempo acceleration/deceleration | Price momentum |
| **delta_delta_bpm** | delta_bpm history | $\Delta^2 f_t$ (second derivative) | Tempo acceleration of acceleration | Momentum of momentum (jerk) |
| **bpm_volatility** | bpm history | $\sigma(\text{bpm}_{t-N:t})$ | Rhythmic stability vs exploration | Realized volatility |
| **bpm_ma** | bpm history | $\frac{1}{N}\sum_{i=0}^{N-1} \text{bpm}_{t-i}$ | Smoothed tempo trend | Simple moving average |
| **energy_momentum** | rms_energy history | Slope of linear regression over window | Building energy vs winding down | Price trend (linear regression slope) |
| **energy_regime** | energy_momentum | Classify as rising/falling/stable (thresholds) | Macro dynamic arc | Bull/bear/sideways regime |
| **energy_volatility** | rms_energy history | $\sigma(\text{rms}_{t-N:t})$ | Dynamic range stability | Realized volatility |
| **chroma_entropy** | chroma (current) | $H = -\sum_{i} p_i \log p_i$ where $p_i = C[i] / \sum C$ | Harmonic complexity (low = drone, high = cluster) | Concentration ratio |
| **chroma_volatility** | chroma history | $\text{mean}(\sigma(\text{chroma}_{t-N:t}, \text{axis}=0))$ | Harmonic stability vs modulation | Sector rotation rate |
| **key_stability** | key history | Fraction of last N chunks in same key | Tonal center persistence | Regime duration |
| **key_change_rate** | key history | Count of key changes in last N chunks | Modulation frequency | Regime switch frequency |
| **spectral_trend** | spectral_centroid history | $\Delta f_t$ (delta formula) | Timbre shifting brighter or darker | Spread trend |
| **spectral_bollinger** | spectral_centroid history | $\mu \pm 2\sigma$ over window, current position | Is timbre at extremes? | Bollinger band position |
| **onset_regularity** | onset_strength history | Autocorrelation peak height at lag = beat period | Rhythmic regularity vs rubato | Autocorrelation (mean reversion signal) |
| **onset_density** | onset_strength history | Count of onsets above threshold per window | Note density / activity level | Trade frequency |
| **mfcc_delta** | MFCC history | $\Delta c_t$ per coefficient | Timbral change rate | Factor momentum |
| **mfcc_delta_delta** | mfcc_delta history | $\Delta^2 c_t$ per coefficient | Timbral acceleration | Factor acceleration |
| **flux_trend** | spectral_flux history | $\Delta f_t$ | Is the rate of change itself changing? | Volatility of volatility |
| **harmonic_percussive_ratio** | H/P energies | $\text{H} / (\text{H} + \text{P})$ over time | Shifting toward melodic or rhythmic | Growth/value ratio |
| **dynamic_range** | rms_energy history | $\max - \min$ over window | Compression vs expressiveness | High-low range |

**What they tell the prompt builder:** Not just "124 BPM" but "accelerating from 120, energy building, harmonically locked in D minor for 8 chunks, timbre drifting brighter." The generation can respond to *trajectory*.

**What they DON'T tell you:** Whether the trajectory will continue. Whether the musician intends it. Whether the AI should follow or contrast.

---

### Layer 3: Structural Signals (Where the music is GOING)

**Quant equivalent:** Factor models — momentum, mean reversion, quality, value. These are predictive. They say "given this pattern, here's what typically happens next."

**Nature:** Pattern recognition on the feature time series. Requires longer history and more computation. Some are statistical, some require learned models.

**Key mathematical tools (all in research doc 01-AUDIO-DSP-MIR.md):**

**Self-Similarity Matrix (SSM)** — Section 4.5:
$$S[i, j] = \frac{\langle f_i, f_j \rangle}{\|f_i\| \cdot \|f_j\|}$$

Compute on the feature history. Diagonal lines = the musician is repeating a pattern. Blocks = stable section. Off-diagonal similarity = the musician returned to an earlier idea.

**Novelty Detection** — Section 4.5:
Convolve a checkerboard kernel along the SSM diagonal. Peaks = structural boundaries. The music just changed character.

**Autocorrelation for periodicity** — Section 4.2:
$$R_{xx}[\tau] = \sum_t f[t] \cdot f[t + \tau]$$

Peaks reveal periodic structure at multiple time scales — not just beat-level but phrase-level, section-level.

| Signal | Computed From | Method | What It Predicts | Quant Analog |
|--------|--------------|--------|-----------------|--------------|
| **repetition_score** | SSM of feature history | Diagonal line detection in SSM | Musician is in a loop / repeating | Mean reversion signal |
| **novelty_score** | SSM of feature history | Checkerboard kernel convolution | Structural boundary — music is changing | Regime change detector |
| **phrase_length** | onset + novelty history | Distance between novelty peaks | Expected duration of current section | Trade holding period |
| **convergence_forecast** | feature trajectory | Linear extrapolation of delta features | Where BPM/energy/timbre will be in N chunks | Price target |
| **energy_arc_position** | energy history + novelty | Classify: intro / build / peak / release / coda | Where are we in the musical arc? | Market cycle phase |
| **harmonic_tension** | chroma history | Distance from tonic chroma template over time | Tension building (away from key) or resolving (toward key) | Credit spread |
| **exploration_score** | SSM + key_stability + chroma_entropy | Composite: low repetition + low key stability + high entropy | Musician is exploring vs consolidating | Dispersion measure |
| **rhythmic_momentum** | bpm_delta + onset_regularity | Composite: consistent acceleration + high regularity | Building toward a rhythmic peak | Trend strength (ADX) |
| **return_probability** | SSM pattern matching | How often past SSM patterns led to a return to earlier material | Likelihood of reprise / return | Mean reversion probability |
| **surprise_index** | feature vector vs N-step prediction | Prediction error: how far is the current chunk from what the model expected? | The musician did something unexpected | Earnings surprise |

**What they tell the generation strategy:** "The musician is in a build phase, halfway through a 16-chunk arc, tension rising, likely 4 more chunks before peak." The AI can anticipate.

**What they DON'T tell you:** Whether the musician *wants* the AI to follow, contrast, or surprise. That's Layer 4.

---

### Layer 4: Interaction Alpha (What the musician NEEDS)

**Quant equivalent:** Proprietary alpha signals from alternative data. The edge nobody else has because nobody else has this dataset.

**Nature:** Learned from interaction data — the paired observations of (what human played, what AI generated, what human did next). Requires data collection infrastructure and offline training. This is the Agentic Prosthetic.

**The dataset:** Every SonicStore session produces tuples:
```
(human_features[t], ai_generation[t], human_features[t+1], session_continues: bool)
```

This is the training data. The question it answers: "Given what the human played and what the AI generated, did the human engage more, less, or stop?"

**Key research grounding:**

From quant-music mapping doc:
- "Both domains use similar feature engineering pipelines: raw signal → preprocessing → feature extraction → dimensionality reduction → model input"
- "Change point detection algorithms developed for financial markets directly apply to music segmentation"
- "Horizontal Visibility Graphs... successfully map both financial time series and audio waveforms to graph representations"

From 01-AUDIO-DSP-MIR.md:
- Section 5.1: Content-based filtering with feature similarity metrics
- Section 5.2: Mood/emotion recognition — Russell's Circumplex (valence × arousal)
- Section 8.3: Conditioning strategies — local (frame-level) vs global (track-level) vs hierarchical

| Alpha Signal | Training Data | Method | What It Prescribes | Quant Analog |
|-------------|--------------|--------|-------------------|--------------|
| **engagement_prediction** | (features, generation) → session_continues | Binary classifier on feature+generation pairs | Will this generation keep the musician playing? | Return prediction |
| **intent_classification** | Feature trajectory patterns → labels | Sequence classifier on Layer 2/3 features | Is the musician exploring, building, resolving, resting? | Market regime classifier |
| **response_preference** | (features, generation_type) → engagement_delta | Bandit / contextual optimization | What *kind* of response works here? (supportive, contrasting, surprising) | Strategy selection |
| **influence_direction** | Cross-correlation of human/AI feature trajectories | Lead-lag analysis | Is the human leading or following the AI? | Granger causality |
| **harmonic_convergence** | Human key vs AI key over time | Trajectory correlation | Are human and AI moving toward same tonal center? | Correlation / cointegration |
| **energy_mirroring** | Cross-correlation of human/AI energy | Rolling correlation coefficient | Are they in sync or diverging? | Beta / correlation |
| **novelty_utility** | (surprise_index, engagement_delta) | Regression: when does surprise help? | When should the AI be unexpected? | Contrarian signal timing |
| **fatigue_detection** | Energy decline + onset_density decline + key_stability increase | Composite threshold detector | Musician is losing energy — simplify | Risk-off signal |
| **creative_temperature** | Composite of exploration_score + surprise response + engagement | Continuous score 0-1 | How much creative risk to take in generation | Position sizing / Kelly criterion |
| **session_arc_model** | Full session feature trajectories | Sequence model (LSTM/Transformer) | Predict optimal generation strategy for remaining session | Portfolio optimization over horizon |

**What they tell the system:** Not just "match the features" or "follow the trajectory" but "this musician, in this moment, at this point in the session, needs *this kind* of response."

**This is the alpha.** It's learned from data nobody else is collecting, about a relationship nobody else is modeling.

---

## 2. The Stack (How It All Connects)

```
LAYER 4: Interaction Alpha
│  Learned models on interaction data
│  Output: generation STRATEGY (supportive/contrasting/surprising)
│  Quant: Alpha signals, strategy selection
│
├── requires Layer 3 signals + interaction dataset
│
LAYER 3: Structural Signals
│  Pattern recognition on feature time series
│  Output: WHERE the music is going (predictions)
│  Quant: Factor models, regime detection
│
├── requires Layer 2 indicators over longer windows
│
LAYER 2: Temporal Indicators
│  Time series computation on feature history
│  Output: WHAT the audio is doing (trends, momentum, volatility)
│  Quant: Technical indicators (MA, RSI, Bollinger)
│
├── requires Layer 1 features stored in history ring
│
LAYER 1: Instantaneous Features
│  Librosa extraction on 2-second audio chunks
│  Output: WHAT the audio is (point-in-time measurement)
│  Quant: Raw market data (price tick, volume bar)
│
├── requires raw audio from mic/file
│
RAW AUDIO
```

Each layer feeds the next. Each layer adds intelligence. The prompt builder currently reads Layer 1. Moving it up the stack is the roadmap.

---

## 3. The Prompt Builder Evolution

### v1 (Current) — Layer 1 Only
```
"upbeat balanced musical accompaniment, 124 BPM, D minor,
 complementary to the input melody, instrumental"
```

### v2 (Horizon 1) — Layer 1 + Layer 2
```
"accelerating from 120 toward 130 BPM with building energy,
 harmonically stable in D minor for 8 measures, brightening timbre,
 complementary to the input melody, instrumental"
```

### v3 (Horizon 2) — Layers 1-3
```
"musician is in a build phase, 4 measures from likely peak,
 tension rising with harmonic movement away from tonic,
 respond with supportive energy, match the acceleration,
 D minor, instrumental"
```

### v4 (Horizon 3) — Full Stack
```
[generation strategy: supportive-amplify]
[creative_temperature: 0.7]
[energy_target: match_trajectory + 10%]
[harmonic_target: stay in D minor but voice-lead toward relative major]
[duration: 8 seconds (shorter — peak is imminent)]
```

At v4, the prompt may not even be natural language anymore. It may be direct parameter conditioning of the generation model.

---

## 4. Implementation Priority

### What to build next (Horizon 1 — derivative features)

**Immediate value, established math, no ML required:**

1. Add to `extract_features()` or new `compute_indicators()`:
   - `spectral_flux` — already in librosa
   - `spectral_rolloff` — already in librosa  
   - `zero_crossing_rate` — already in librosa
   - `spectral_contrast` — already in librosa
   - `MFCCs` — already in librosa (13 coefficients)
   - `tonnetz` — already in librosa
   - `harmonic_percussive_ratio` — from `librosa.effects.hpss`

2. Add `compute_derivatives()` module operating on history ring:
   - Delta formula (Davis & Mermelstein 1980) applied to: bpm, energy, centroid, onset
   - Rolling statistics: mean, std, min, max over configurable window
   - Regime classification: rising/falling/stable

3. Extend prompt builder with trajectory descriptors

**All formulas are in research doc `01-AUDIO-DSP-MIR.md`.** All implementations are in librosa. This is known math.

### What to build after (Horizon 2 — structural signals)

**Requires longer history, more computation:**

1. Self-Similarity Matrix computation on feature history
2. Novelty detection (checkerboard kernel)
3. Phrase length estimation
4. Energy arc classification
5. Harmonic tension tracking

**Formulas are in research doc sections 4.2 and 4.5.** Implementation is custom but math is established.

### What to research (Horizon 3 — interaction alpha)

**Requires data collection infrastructure first:**

1. Session logging (every feature vector + every generation + timestamps)
2. Engagement proxy definition (what does "the musician responded well" look like in the data?)
3. Offline training pipeline
4. A/B testing framework for generation strategies

**The quant-music mapping doc validates the approach.** The Manchester thesis proved graph-based methods transfer between music and finance time series.

---

## 5. Reference Index

All citations refer to research doc `01-AUDIO-DSP-MIR.md` section numbers and bibliography entries.

| Topic | Research Doc Section | Key References |
|-------|---------------------|---------------|
| Delta/delta-delta features | 2.4 | Davis & Mermelstein 1980 [8] |
| Chroma / CENS | 2.5 | Brown 1991 [9], Müller 2015 [17] |
| CQT (constant-Q transform) | 2.6 | Brown 1991 [9] |
| Spectral centroid, rolloff, flux, contrast | 3.2 | Grey 1977 [14] |
| Harmonic-percussive separation | 3.3 | Fitzgerald 2010 |
| Onset detection | 4.1 | Bello et al 2005 [16] |
| Beat tracking / autocorrelation | 4.2 | Ellis 2007 [15], Goto & Muraoka 1999 [19] |
| Key estimation (K-S profiles) | 4.3 | Krumhansl 1990 |
| Self-similarity matrix | 4.5 | Müller 2015 [17] |
| Novelty detection | 4.5 | Müller 2015 [17] |
| Mood/emotion (valence × arousal) | 5.2 | Russell's Circumplex |
| Conditioning strategies | 8.3 | — |
| Quant-music methodology transfer | quant-music-mapping.md | Manchester thesis, ScienceDirect MIR |
| Regime detection transfer | quant-music-mapping.md | "directly apply to music segmentation" |
| Feature engineering parallels | quant-music-mapping.md | "similar feature engineering pipelines" |

---

*Sonic Alpha framework by: Quincy (Technical Director) + Danny (Composer)*
*Grounded in: 28 research documents, research/01-AUDIO-DSP-MIR.md, research/quant-music-mapping.md*
*Status: DRAFT — ready for prioritization and spec-start*
