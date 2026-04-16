# Model Architecture Patterns for Real-Time AI Music Generation
## Technical Design Report — SonicStore Hackathon Research

**Research Document 03**  
*SonicStore Project — Architecture Patterns & Design Decisions*  
**Date:** April 2026  
**Bridges:** 02-SOTA-MUSIC-GENERATION.md → 04-INFERENCE-DEPLOYMENT.md

---

## Executive Summary

This report bridges the SOTA music generation landscape (Document 02) with the inference deployment constraints (Document 04) by analyzing architecture patterns through the lens of SonicStore's specific requirements: a live-performance-capable, real-time music generation system with user interaction latency targets in the 50–500ms range.

The central finding: **no single architecture satisfies all SonicStore requirements.** Instead, a tiered hybrid is recommended — RAVE (VAE-based, true real-time) for interactive generation, MusicGen-Small (neural codec + autoregressive transformer) for prompt-driven generation, and a diffusion fallback (AudioLDM/Stable Audio) for offline quality rendering. The hackathon MVP should implement the RAVE + MusicGen-Small tier only.

---

## Table of Contents

1. [Architecture Pattern Catalog](#1-architecture-pattern-catalog)
2. [Real-Time Constraints Analysis](#2-real-time-constraints-analysis)
3. [SonicStore-Specific Considerations](#3-sonicstore-specific-considerations)
4. [Architecture Recommendations](#4-architecture-recommendations)
5. [Reference Models — Application Mapping](#5-reference-models--application-mapping)
6. [Implementation Paths](#6-implementation-paths)
7. [Decision Matrix](#7-decision-matrix)
8. [References](#8-references)

---

## 1. Architecture Pattern Catalog

This section establishes a common vocabulary for the architecture patterns present in SOTA music generation, analyzing each against core engineering properties: generation quality, latency, memory footprint, controllability, and hackathon feasibility.

---

### 1.1 Autoregressive Transformers (AR)

**Core Mechanism:**  
Autoregressive transformers generate sequences token-by-token, where each token is conditioned on all prior tokens. In music generation, the "tokens" are discrete codes produced by a neural audio codec (EnCodec, SoundStream, DAC), not raw samples or MIDI events.

```
Codec → Discrete Token Sequence
         [t₁, t₂, ... tₙ]
              ↓
   Transformer Decoder (causal)
         P(tᵢ | t₁...tᵢ₋₁, condition)
              ↓
         Token Stream
              ↓
Codec Decoder → Waveform
```

**Key Variants:**

| Variant | Example | Token Space | Conditioning |
|---------|---------|-------------|--------------|
| Single-Stage | MusicGen | Codec tokens (flat) | T5 text encoder |
| Hierarchical | MusicLM | Semantic → Coarse → Fine | MuLan (audio-text) |
| Multi-Codebook Interleaved | MusicGen w/ delay pattern | Parallel codebooks | Various |

**The Codebook Interleaving Problem:**  
Neural codecs like EnCodec use Residual Vector Quantization (RVQ) with multiple codebooks in parallel (e.g., 4 codebooks at 32 kHz → 50 frames/second × 4 = 200 tokens/second). Naive flattening creates long sequences; MusicGen's innovation was the "delay pattern" — codebooks are interleaved with offsets so the model only needs to predict Q tokens per frame at each step, not Q×N.

```
Naive:     [CB1_f1, CB2_f1, CB3_f1, CB4_f1, CB1_f2, CB2_f2, ...]  ← Long sequences
Delay:     [CB1_f1, CB2_f1, CB1_f2, CB3_f1, CB2_f2, CB1_f3, ...]  ← Parallel-friendly
```

This reduced MusicGen's effective sequence length by ~4×, making 30-second generation tractable on consumer hardware.

**Strengths:**
- Highest audio quality among realistically deployable architectures
- Natural streaming: tokens can be decoded to audio as they're generated
- Text/melody conditioning is well-studied and robust
- Open-source ecosystem (audiocraft) is mature and well-maintained

**Weaknesses:**
- Sequential generation: cannot parallelize across time dimension
- KV-cache grows with sequence length → memory scales with output duration
- No explicit musical structure modeling (no explicit bar/beat awareness)
- First-token latency is high if model must be warmed up

**Inference Complexity:** O(n²) attention per token, O(n) tokens for n seconds of audio at 50 Hz frame rate.

---

### 1.2 Diffusion Models (Score-Based / DDPM)

**Core Mechanism:**  
Diffusion models learn to reverse a noise-addition process. A forward process adds Gaussian noise to clean audio (or a latent representation) over T timesteps; the model learns the reverse denoising trajectory. At inference, pure noise is iteratively denoised toward a sample from the learned distribution.

```
Training:
x₀ (clean) → x₁ → x₂ → ... → xT (noise)  [Forward: fixed Markov chain]
Model learns: εθ(xₜ, t, condition) ≈ ε  [Predict noise]

Inference:
xT (random noise) → ... → x₁ → x₀ (generated audio)  [Reverse: T model calls]
```

**Two Main Operating Spaces:**

| Mode | Example | Operating Space | Quality | Speed |
|------|---------|-----------------|---------|-------|
| Raw spectrogram | Riffusion | Mel-spectrogram pixels | Medium | Medium |
| Latent diffusion | AudioLDM, Stable Audio | VAE latent space | High | Higher |

Latent Diffusion Models (LDMs) achieve dramatically faster inference by operating in a compressed latent space (typically 16-64× compression ratio via a pre-trained VAE), then decoding the latent at the end via the VAE decoder.

**Sampling Efficiency:**  
The T inference calls are the fundamental bottleneck. Key innovations:

| Sampler | Steps Required | Speedup | Quality |
|---------|---------------|---------|---------|
| DDPM | 1000 | 1× | Baseline |
| DDIM | 50-100 | 10-20× | ~Same |
| DPM-Solver++ | 15-25 | 40-67× | Comparable |
| Consistency Models | 1-4 | 250-1000× | Reduced |

**Strengths:**
- Highest output quality ceiling (Stable Audio, AudioLDM-2)
- Parallel generation (unlike AR): all latent dimensions computed simultaneously per step
- Flexible conditioning via classifier-free guidance (CFG) — scale at inference time
- Robust interpolation: can smoothly morph between two audio styles in latent space

**Weaknesses:**
- Multiple sequential model calls per generation (minimum 10-15 for acceptable quality)
- Phase reconstruction artifacts when operating on spectrograms
- Not natively streamable (generation completes before first audio token)
- Higher memory pressure during denoising steps (activations held in memory)

**Real-Time Status:** ❌ Not viable for interactive latency. Minimum ~2 seconds for 10s audio even with optimized samplers on A100.

---

### 1.3 Variational Autoencoders (VAE)

**Core Mechanism:**  
A VAE learns a compressed latent representation of audio by jointly training an encoder (audio → latent) and decoder (latent → audio) with a regularization term (KL divergence toward a prior distribution). The latent space is continuous and smooth, enabling interpolation and manipulation.

```
Encoder: x (audio) → μ, σ → z ~ N(μ, σ²)  [Latent distribution]
Decoder: z → x̂ (reconstructed audio)
Loss: ||x - x̂||² + β · KL(q(z|x) || p(z))  [Reconstruction + regularization]
```

**RAVE: The Real-Time Specialist:**  
RAVE (Realtime Audio Variational autoEncoder) is the critical architecture for SonicStore's live performance context. It achieves several properties no other architecture matches:

- **True real-time synthesis**: Processes audio in chunks with causal convolutions
- **Latency**: <10ms processing latency at 48kHz
- **Real-time factor**: 20× faster than real-time on a standard laptop CPU
- **Streamable**: Produces audio continuously without waiting for full generation
- **Controllable**: Latent space manipulable in real-time via external controllers

RAVE's architecture uses multi-band convolutions to achieve causal, streamable processing:

```
Audio → Multi-band Decomposition → Encoder (Causal Convolutions)
                                           ↓
                                    Latent z(t)  ← Real-time control
                                           ↓
                                  Decoder (Causal Convolutions)
                                           ↓
                                    Multi-band Reconstruction → Audio
```

The key innovation enabling streaming: all convolutions are causal (no future context), and a "streamable" mode removes any non-causal normalization layers that would require full-sequence statistics.

**Other VAE Variants for Music:**

| Model | Parameters | Focus | Latency |
|-------|-----------|-------|---------|
| RAVE | 10-50M | Timbre/texture | <10ms |
| MusicVAE (Magenta) | 100-500M | Symbolic MIDI | N/A |
| Stable Audio VAE component | ~100M | Latent compression | Pre-computed |

**Strengths:**
- Dramatically lower latency than any transformer or diffusion approach
- Smooth, interpolatable latent space — ideal for expressive live control
- Small model footprint (10-50M vs. 300M-3.3B for MusicGen)
- CPU-deployable at real-time speeds

**Weaknesses:**
- Limited controllability from high-level semantics (text prompts don't map cleanly)
- Quality ceiling lower than autoregressive or diffusion approaches
- Requires domain-specific training (a guitar RAVE ≠ a piano RAVE)
- No intrinsic musical structure modeling

---

### 1.4 Hierarchical VQ-VAE

**Core Mechanism:**  
Hierarchical VQ-VAE (as in Jukebox) learns a multi-level discrete latent representation. Multiple VQ-VAE levels compress audio at different temporal resolutions, then autoregressive transformers are trained to model the distribution of codes at each level, conditioned on higher levels.

```
Level 3 (lowest res): 128× compression → Long-term structure
Level 2 (mid res):     32× compression → Mid-term structure  
Level 1 (highest res):  8× compression → Fine details

AR Transformer (L3) → AR Transformer (L2 | L3) → AR Transformer (L1 | L2)
                                        ↓
                              VQ-VAE Decoder → 44.1 kHz Audio
```

**Why This Matters for SonicStore:**  
Jukebox demonstrated that raw 44.1 kHz audio generation is *possible* but *prohibitively slow* (9 hours per 3-minute song on V100). It established the architectural insight that neural codec + autoregressive generation was the right abstraction — the same insight that MusicGen productized efficiently with EnCodec's higher compression ratio and a single-stage model.

The lesson: hierarchical generation is architecturally elegant but compounds inference cost multiplicatively. Single-stage approaches (MusicGen's "flat" codec token AR) achieve 95% of the quality at 1% of the compute.

**Status for SonicStore:** Historical reference only. Not recommended for any production path.

---

### 1.5 Encoder-Decoder Transformer (Seq2Seq)

**Core Mechanism:**  
Encoder-decoder architectures use a bidirectional encoder to process input conditioning (text, reference audio, melody) and a causal decoder to generate output tokens. The encoder produces a rich contextual representation that the decoder cross-attends to at every step.

```
Text/Melody → Encoder → Context C
                              ↓ (cross-attention)
[BOS, t₁, t₂, ...] → Decoder → [t₁, t₂, t₃, ...]
```

**Application in Music Generation:**  
MusicGen uses a variant of this: a frozen T5 encoder processes text descriptions, and an autoregressive transformer decoder generates codec tokens with T5 encoder outputs as cross-attention keys/values.

```
Text Prompt → T5 Encoder (frozen) → 768-dim context vectors
                                            ↓ (cross-attention at every layer)
              Transformer Decoder (24-48 layers) → EnCodec tokens
```

Freezing the T5 encoder is a critical practical decision: it prevents catastrophic forgetting of language understanding and eliminates gradient flow through the encoder during music generation training, reducing compute by ~40%.

**Conditioning via Classifier-Free Guidance (CFG):**  
CFG runs two forward passes per decoding step — one conditioned, one unconditioned — and interpolates:

```
token_probs = (1 + cfg_scale) × P(t|condition) - cfg_scale × P(t|∅)
```

CFG scale of 3.0–5.0 significantly improves prompt adherence but doubles inference cost.

**Strengths:**
- Proven architecture with well-understood training dynamics
- Strong text-to-music alignment via pretrained encoders
- Supports multi-modal conditioning (text + melody + style)

**Weaknesses:**
- CFG doubles inference cost
- Encoder bottleneck limits conditioning granularity
- No explicit temporal conditioning (no "bar 4, chorus starts here")

---

### 1.6 Flow Matching Models

**Core Mechanism:**  
Flow matching learns to map a simple distribution (Gaussian) to the data distribution via a learned vector field. Unlike diffusion, it uses straight-line "optimal transport" paths between noise and data, enabling fewer integration steps.

```
x₀ ~ N(0,I)  →  x₁ (data)   [Straight path: xₜ = (1-t)x₀ + tx₁]
Model learns: vθ(xₜ, t) = dx_t/dt = x₁ - x₀  [Constant vector field]
```

**StreamFlow (NeurIPS 2025):**  
StreamFlow introduced causal flow matching for streaming audio generation, achieving 100–500ms latency per chunk. This is an emerging architecture that may mature for production use by Q3 2026 (post-hackathon).

**Status for SonicStore:** Watch-and-wait. Not recommended for hackathon, potentially relevant for MVP.

---

### 1.7 GAN-Based Audio Models

**Core Mechanism:**  
Generative Adversarial Networks train a generator to fool a discriminator. For audio, HiFi-GAN and similar vocoder architectures use multi-period and multi-scale discriminators operating on raw waveforms.

**Role in Music Generation:**  
Pure GAN music generation has largely been superseded by diffusion and autoregressive approaches. However, GAN-based vocoders (HiFi-GAN, BigVGAN) remain critical components in hybrid pipelines — they convert intermediate representations (spectrograms, VAE latents) to high-quality waveforms at real-time speeds.

```
Spectrogram/Latent → GAN Vocoder (HiFi-GAN) → 24/44.1 kHz Waveform
                      [Real-time capable, <5ms]
```

**Relevance to SonicStore:**  
EnCodec and DAC (Descript Audio Codec) both use GAN discriminators in their training pipeline. The real-time decoding speed of these codecs (effectively instant once the token stream is complete) is a GAN contribution.

---

## 2. Real-Time Constraints Analysis

### 2.1 The Latency Budget Hierarchy

SonicStore must navigate three distinct latency regimes, each with fundamentally different architecture implications:

| Regime | Budget | User Experience | Architecture Requirement |
|--------|--------|-----------------|-------------------------|
| **Hard Real-Time** | <10ms | Analog-feel instrument | RAVE, GAN vocoders only |
| **Soft Real-Time** | 10–100ms | Responsive DAW plugin | RAVE with lookahead |
| **Near Real-Time** | 100ms–2s | Interactive web app | MusicGen-Small (streaming) |
| **Async Generation** | 2s–30s | Background generation | MusicGen-Medium/Large, Diffusion |

**The 10ms Wall:**  
Human perception of audio latency becomes noticeable above ~10ms for direct monitoring tasks (guitar→amp) and above ~20–30ms for interactive software instruments. Live performance at a hackathon with Berklee musicians will demand the 20–50ms range — not 10ms, but close enough that diffusion models are categorically out.

**The 150ms Conversational Threshold:**  
For text-prompt-driven generation ("generate something more jazzy"), latency up to ~150ms feels interactive. Above 300ms, users perceive a noticeable delay. Above 1000ms, the interaction feels like a server round-trip. MusicGen-Small on RTX 4090 generates the first audio tokens in ~50ms after prompt submission — within this window.

### 2.2 Memory Footprint Analysis

Memory constrains which models can be loaded simultaneously on a single machine — critical for hackathon hardware (likely a single gaming laptop or workstation).

**Active Model Memory (FP16):**

| Model | Weights | KV-Cache (30s) | Peak Activation | Total |
|-------|---------|----------------|-----------------|-------|
| MusicGen-Small | 600MB | ~800MB | ~1.2GB | ~2.6GB |
| MusicGen-Medium | 3GB | ~2GB | ~3GB | ~8GB |
| MusicGen-Large | 6.6GB | ~4GB | ~6GB | ~16.6GB |
| RAVE | 100MB | N/A (streaming) | ~200MB | ~0.3GB |
| AudioLDM-2 (LDM) | 2.4GB | N/A | ~3GB | ~5.4GB |
| VAE (AudioLDM-2) | 400MB | N/A | ~600MB | ~1GB |

**KV-Cache Growth:**  
For autoregressive models, the KV-cache grows linearly with generated sequence length:

```
KV-cache size = 2 × L × H × D × S × dtype_bytes
where:
  L = number of layers (24 for MusicGen-Small)
  H = number of attention heads (16)
  D = head dimension (64)
  S = sequence length (tokens)
  dtype = FP16 (2 bytes)

For MusicGen-Small, 30 seconds = 30 × 50 × 4 = 6000 tokens
KV-cache = 2 × 24 × 16 × 64 × 6000 × 2 ≈ 1.47 GB
```

This means generating longer outputs consumes exponentially more memory. For a hackathon demo targeting 30-second generations, 8GB VRAM is the practical minimum for MusicGen-Small.

### 2.3 Inference Optimization Trade-Offs

Each optimization technique imposes trade-offs that must be understood before applying them:

**FP16/BF16 Quantization:**
- Savings: ~2× memory, ~1.3-2× speed
- Cost: Negligible quality loss (FAD increase <5%)
- Verdict: Apply unconditionally to all models

**INT8 Quantization:**
- Savings: ~4× memory, ~2-4× speed
- Cost: 10-15% FAD increase, perceptible artifacts at INT8 for audio
- Verdict: Apply to embedding layers only; leave attention/MLP in FP16

**`torch.compile()`:**
- Savings: 20-30% speedup
- Cost: 60-120 second compilation on first call; graph breaks on dynamic control flow
- Verdict: Apply with `mode="reduce-overhead"` for batch inference; skip for low-latency streaming

**Flash Attention:**
- Savings: O(n²) → O(n) memory for attention; 2-4× speedup for long sequences
- Cost: Requires flash-attn library; some hardware incompatibilities
- Verdict: Apply for all autoregressive transformers, essential for 30+ second generation

**CUDA Graphs:**
- Savings: 10-20% speedup by eliminating CUDA kernel launch overhead
- Cost: Fixed batch size and sequence length; incompatible with dynamic inputs
- Verdict: Apply only for fixed-length inference (pre-demo warm-up runs)

**Speculative Decoding:**
- Mechanism: Small "draft" model proposes tokens, large "verifier" accepts/rejects in parallel
- Savings: 2-3× speedup for autoregressive generation
- Cost: Requires compatible small model as draft; implementation complexity
- Verdict: High-value for production; too complex for hackathon

**KV-Cache Management:**
- Chunked KV-cache (e.g., vLLM's PagedAttention): reduces memory fragmentation
- Verdict: Implement if serving multiple users; skip for single-user hackathon demo

### 2.4 Streaming Inference for Autoregressive Models

MusicGen can be made partially streaming using token-level decoding with early audio output. The EnCodec decoder can reconstruct audio from partial token streams:

```
Token generation: [t₁] → [t₁, t₂] → ... → [t₁...tₙ]
                   ↓        ↓                    ↓
Audio decode:    chunk₁  chunk₂  ...          chunkₙ
```

**Practical implementation (audiocraft streaming):**
```python
with model.streaming(30, progress=False) as streamer:
    for tokens in streamer:
        audio_chunk = decode_tokens(tokens)
        play_immediately(audio_chunk)  # First audio at ~1 second
```

This delivers first audio to the user within ~1 second for MusicGen-Small, significantly improving perceived responsiveness versus waiting for full generation (~5s for 30s audio).

**Lookahead Buffer Architecture:**  
For live performance, a lookahead buffer pre-generates the next 5-10 seconds while the current segment plays:

```
Time:  |──── t=0-10s playing ────|──── t=10-20s playing ────|
Regen: |── t=5s: start generating t=10-20s ──|── t=15s: start generating t=20-30s ──|
```

This allows MusicGen-Medium to "feel" real-time if the musical structure evolves slowly enough.

---

## 3. SonicStore-Specific Considerations

### 3.1 SonicStore's Core Use Case

Per the hackathon brief, SonicStore's primary concept is **real-time MIR feature extraction as a service**. The music generation component enters as a natural extension: not just *analyzing* music in real-time, but *generating* music in response to features extracted from live input.

The generative flow this enables:

```
Live Audio Input → SonicStore Feature Engine → [BPM, Key, Mood, Chroma, Spectral]
                                                        ↓
                                          Generative Conditioning Signal
                                                        ↓
                             Music Generation Model → AI-Generated Response Audio
                                                        ↓
                                                Live Performance Mix
```

This creates a **closed-loop generative system** — a fundamental shift from batch generation to continuous, responsive generation. The architecture must support this loop, which rules out anything with >500ms latency for the initial response.

### 3.2 Live Performance Context

**Who the users are:**  
Berklee musicians acting as "creative leads" at the hackathon. These users have:
- Low tolerance for perceptible latency in an instrument context
- High sensitivity to audio quality artifacts (trained ears)
- Expectation of expressivity — the system should respond to nuance, not just coarse commands
- Strong preference for organic, controllable output over "black box" generation

**Live performance latency expectations:**  
From the user research and audio engineering literature, the implicit expectations are:

| User Role | Expected Latency | Acceptable Latency | Notes |
|-----------|-----------------|-------------------|-------|
| Performer (instrument substitute) | <5ms | <15ms | Like a synth |
| Performer (generative collaborator) | <100ms | <300ms | Like a bandmate |
| Producer (interactive tool) | <500ms | <2s | Like a DAW plugin |
| Listener (passive generation) | N/A | <30s | Background music |

For the hackathon's live demo, the "generative collaborator" frame is most appropriate: the AI responds to what the musician plays within 100-300ms, generating complementary patterns or variations.

### 3.3 Hardware Targets

**Hackathon hardware (likely scenarios):**

| Scenario | Hardware | Available VRAM | Recommended Stack |
|----------|----------|---------------|-------------------|
| **MacBook Pro M3 Max** | Apple Silicon | 36-128GB unified | RAVE + MusicGen-Small (CoreML) |
| **Gaming Laptop (RTX 4080)** | NVIDIA | 16GB | RAVE + MusicGen-Small (PyTorch FP16) |
| **Gaming Desktop (RTX 4090)** | NVIDIA | 24GB | RAVE + MusicGen-Medium (PyTorch FP16) |
| **Cloud (A100 80GB)** | Remote GPU | 80GB | Full stack incl. diffusion |
| **No GPU (CPU only)** | x86/ARM | N/A | RAVE only |

**The M3 Max Case:**  
Apple Silicon's unified memory architecture is architecturally advantageous for music generation: the full 36-128GB pool is available to both CPU and GPU, eliminating PCIe transfer overhead. MusicGen-Medium in FP16 (3GB weights + ~5GB runtime) fits comfortably on M3 Pro (18GB), with significant headroom for the RAVE stack and SonicStore's feature extraction pipeline running simultaneously.

CoreML export of MusicGen-Small has been demonstrated in the community; expect ~2× speedup over PyTorch on Apple Silicon (Neural Engine acceleration).

### 3.4 SonicStore Integration Architecture

The music generation component must integrate with SonicStore's feature store architecture:

```
                    SonicStore Stack
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Sources (Mic/DAW/File) → Ingestion → Feature Engine        │
│                                             │                │
│                           ┌────────────────┤                │
│                           ▼                ▼                │
│                      Hot Store         Warm Store           │
│                      (Redis)          (DuckDB)              │
│                           │                                  │
│                    Feature API                               │
│                           │                                  │
│              ┌────────────┼────────────┐                    │
│              ▼            ▼            ▼                    │
│          Chroma         BPM           Mood                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                           │
                    Conditioning Signal
                           │
                           ▼
              ┌────────────────────────┐
              │   Generation Layer     │
              │                        │
              │  RAVE (real-time)      │ ← Continuous timbre/texture modulation
              │  MusicGen (near-RT)    │ ← Prompt-driven section generation
              │  Diffusion (async)     │ ← Quality rendering (future)
              └────────────────────────┘
                           │
                    Output Audio
```

**Key Design Decision — Push vs. Pull:**  
The feature engine should push conditioning updates to the generation layer, not the generation layer polling for features. Redis Pub/Sub (already in the SonicStore architecture) is the natural mechanism: feature vectors are published to channels that the generation layer subscribes to, updating RAVE's latent conditioning vector in real-time.

---

## 4. Architecture Recommendations

### 4.1 Recommended Stack: Tiered Hybrid

**Tier 1 — Real-Time Interactive (RAVE):**

| Property | Value |
|----------|-------|
| Latency | <10ms |
| Use case | Live timbre/texture modulation, continuous generation |
| Conditioning | Feature vectors from SonicStore (BPM, chroma, mood) |
| Hardware | Any (CPU-capable) |
| Quality | Medium-High (timbre-accurate, not prompt-precise) |
| Hackathon feasibility | ✅ High |

RAVE is the only architecture that satisfies live performance requirements. It operates continuously, modulating audio in real-time based on external control signals. For SonicStore, RAVE's latent space can be mapped to features extracted by the feature engine:

```python
# Real-time control loop
while playing:
    features = redis.get("features:latest")       # <1ms, non-blocking
    z = feature_to_latent(features)               # Linear projection
    audio_chunk = rave.decode(z)                  # <5ms
    output_buffer.write(audio_chunk)              # <1ms
```

**Tier 2 — Near-Real-Time Generative (MusicGen-Small):**

| Property | Value |
|----------|-------|
| Latency | 1–5 seconds (first audio) |
| Use case | Text-prompt generation, style changes, section transitions |
| Conditioning | Text prompt + melody reference |
| Hardware | 6–8GB VRAM minimum |
| Quality | High (benchmark-comparable to commercial APIs) |
| Hackathon feasibility | ✅ High |

MusicGen-Small with streaming output provides a compelling interactive demo. When a musician says "add some jazz piano here," a text prompt triggers a new generation that fades in within 1–2 seconds.

**Tier 3 — Async Quality Rendering (Optional for Hackathon):**

| Property | Value |
|----------|-------|
| Latency | 10–30 seconds |
| Use case | Offline recording, high-quality output, export |
| Conditioning | Full prompt + reference audio |
| Hardware | 16GB+ VRAM |
| Quality | Maximum |
| Hackathon feasibility | ⚠️ Optional stretch goal |

AudioLDM-2 or Stable Audio Open for this tier. Not required for live demo but adds value for post-performance export.

### 4.2 Architecture Decision Rationale

**Why RAVE over MusicGen for real-time?**  
MusicGen's autoregressive generation is fundamentally sequential: each token depends on all prior tokens. There is no architectural path to <100ms latency. RAVE's convolutional streaming architecture, by contrast, produces audio with single-buffer latency (~5–10ms). For live performance, this is not negotiable.

**Why MusicGen-Small over MusicGen-Medium or Large?**  
For a hackathon context with a single machine:
- Small → Medium: Quality improvement is real (~15% FAD improvement) but not dramatic enough to justify 4× higher memory requirement
- Small → Large: On a 16GB VRAM machine, Large would need memory offloading, adding ~50% latency
- Small with FP16 + Flash Attention matches Medium quality on a fast GPU through better sampling strategies

**Why not Riffusion?**  
Riffusion was architecturally interesting (spectrogram diffusion) but is now deprecated. Griffin-Lim phase reconstruction introduces audible artifacts, and the maximum duration (12 seconds, fixed by image size) is constraining. MusicGen is strictly better on every axis except perhaps "novelty as a demo hook."

**Why not Jukebox?**  
Jukebox's 9-hour inference time for 3 minutes of audio is a categorical disqualifier. The architecture is historically important but practically irrelevant for SonicStore.

**Why not MusicLM?**  
MusicLM is not open-source. API-only access introduces network latency, cost per generation, and dependency on Google's infrastructure. For a hackathon, external API dependencies are high-risk; for a live demo, network latency is disqualifying.

### 4.3 Trade-Off Analysis

**RAVE Trade-Offs:**

| Pro | Con |
|-----|-----|
| True real-time (<10ms) | No text prompt conditioning |
| CPU-capable, any hardware | Quality ceiling lower than AR/diffusion |
| Small footprint (50-100MB) | Domain-specific (need separate models per instrument) |
| Smooth latent interpolation | Requires pre-trained domain model |
| Deterministic, predictable | Limited "generativity" — more like a neural synthesizer |

**MusicGen-Small Trade-Offs:**

| Pro | Con |
|-----|-----|
| Text-conditioned generation | 1–5s latency (not live-performance viable alone) |
| Open-source, Apache 2.0 | KV-cache memory grows with output length |
| Well-maintained audiocraft library | No explicit musical structure (no bars/beats) |
| Streaming output reduces perceived latency | Temperature tuning required for quality |
| Good VRAM efficiency at Small scale | Repetition artifacts on longer generations |

**Diffusion (AudioLDM-2) Trade-Offs:**

| Pro | Con |
|-----|-----|
| Highest quality ceiling | 2–30s latency even on A100 |
| Parallel generation per denoising step | Not streamable |
| Flexible CFG conditioning at inference | Multiple forward passes required |
| Smooth style interpolation in latent space | Memory intensive during denoising |

---

## 5. Reference Models — Application Mapping

This section maps SOTA models from Document 02 to SonicStore's specific use cases, with concrete implementation guidance.

### 5.1 RAVE — Real-Time Generation Tier

**Architecture (Caillon & Esling, 2021):**
- Multi-band variational autoencoder
- Encoder: 4 residual convolutional layers, causal
- Decoder: 4 transposed convolutional layers, causal
- Latent dimension: 16-128 (configurable)
- Sample rate: 48 kHz
- Model size: 10-50M parameters

**Pretrained Models Available:**
- `rave_violin.ts` — Violin timbre
- `rave_percussion.ts` — Percussion
- `rave_darbouka_plus_oud.ts` — World music
- `rave_nasa_hubble.ts` — Atmospheric/drone
- Community-trained: piano, guitar, synthesizer

**SonicStore Integration:**
```python
import torch
import torchaudio

# Load pretrained RAVE
rave = torch.jit.load("rave_percussion.ts")
rave.eval()

# Real-time control via SonicStore features
def on_feature_update(features: dict):
    """Called by Redis subscriber on each feature tick."""
    z = feature_to_latent_mapping(features)  # Learned linear projection
    with torch.no_grad():
        audio = rave.decode(z.unsqueeze(0))  # <5ms
    audio_output_queue.put(audio)
```

**Feature-to-Latent Mapping:**  
RAVE's latent dimensions don't have semantic labels — they're learned, opaque. For SonicStore, a lightweight linear mapping must be trained to connect SonicStore feature vectors to RAVE's latent space. This requires ~30 minutes of paired data (input audio features + desired RAVE output latents) and a simple linear regression or MLP.

```
SonicStore Features → [BPM, Key, RMS, Chroma, Spectral Centroid]
                                    ↓
                    Linear Projection (trainable, 10 min)
                                    ↓
                       RAVE Latent z (16-128 dims)
                                    ↓
                       RAVE Decoder → Audio
```

### 5.2 MusicGen-Small — Near-Real-Time Prompt Tier

**Architecture (Copet et al., 2023):**
- T5-base encoder (frozen, 220M parameters) for text conditioning
- Causal transformer decoder (300M parameters, 24 layers)
- EnCodec: 32 kHz, 4 codebooks, 50 Hz frame rate
- Delay pattern for parallel codebook decoding
- CFG scale 3.0 default

**Key Implementation Details:**
```python
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

# Load with FP16 for 2× memory efficiency
model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(
    use_sampling=True,
    top_k=250,
    duration=10,           # seconds
    cfg_coef=3.0,
)

# Enable streaming for live demo
with model.streaming(10, progress=False) as streamer:
    descriptions = ["upbeat jazz piano with walking bass, 120 BPM"]
    wav = model.generate(descriptions)
```

**Conditioning from SonicStore Features:**  
MusicGen can be conditioned via text prompts assembled dynamically from feature extraction results:

```python
def features_to_prompt(features: dict) -> str:
    """Convert SonicStore features to MusicGen text prompt."""
    bpm = features.get('bpm', 120)
    key = features.get('key', 'C major')
    mood = features.get('mood', 'neutral')
    instrument = features.get('dominant_instrument', 'piano')
    
    return f"{mood} {instrument}, {int(bpm)} BPM, {key}, complementary accompaniment"

# Example: "energetic bass guitar, 134 BPM, A minor, complementary accompaniment"
```

This creates a **feature → prompt → generation** loop where MusicGen generates music that complements the live input based on extracted features.

**Melody Conditioning (MusicGen-Melody variant):**  
If available, MusicGen-Melody extends conditioning with a melody reference — the live audio input can be passed directly:

```python
model = MusicGen.get_pretrained('facebook/musicgen-melody')
# model size: 1.5B, ~4GB VRAM in FP16

melody_waveform, sr = torchaudio.load("live_input_buffer.wav")
wav = model.generate_with_chroma(
    descriptions=["jazz accompaniment"],
    melody_wavs=melody_waveform,
    melody_sample_rate=sr
)
```

This is a strong demo feature: the AI harmonizes with what the musician is playing in real-time (with ~2-3 second latency for generation).

### 5.3 AudioLDM-2 — Async Quality Tier (Optional)

**Architecture (Liu et al., 2023):**
- CLAP encoder for text-audio joint conditioning
- Latent Diffusion Model (U-Net backbone)
- VAE encoder/decoder pair
- DPM-Solver++ sampler (20 steps for demo quality)

**Practical Notes:**
- Not streamable — full audio generated before output
- Can be used for "export quality" rendering after live performance
- 10-20 step sampling with DPM-Solver++ achieves acceptable quality in ~2s on RTX 4090
- `diffusers` library provides the cleanest integration

```python
from diffusers import AudioLDM2Pipeline

pipe = AudioLDM2Pipeline.from_pretrained(
    "cvssp/audioldm2-music",
    torch_dtype=torch.float16
)
pipe = pipe.to("cuda")

# Generate high-quality export of the live session's theme
audio = pipe(
    prompt="jazz piano trio, live recording warmth, Carnegie Hall ambience",
    num_inference_steps=20,   # 100× faster than full quality, acceptable FAD
    audio_length_in_s=30.0,
    guidance_scale=3.5,
).audios[0]
```

### 5.4 Stable Audio Open — Alternative Async Tier

**Architecture (Evans et al., 2024):**
- Timing-conditioned latent diffusion
- ARC (Adversarial Relativistic-Contrastive) post-training
- Key advantage: explicit duration conditioning

```python
from stable_audio_tools import get_pretrained_model
from stable_audio_tools.inference.generation import generate_diffusion_cond

model, model_config = get_pretrained_model("stabilityai/stable-audio-open-1.0")

# Duration-conditioned generation — novel capability
conditioning = [{
    "prompt": "jazz piano improvisation, warm and intimate",
    "seconds_start": 0,
    "seconds_total": 30    # Explicit 30-second generation
}]
```

Stable Audio Open's timing conditioning is architecturally distinctive: the model knows how long it needs to generate, which enables explicit intro/verse/outro structure — something MusicGen lacks.

### 5.5 MusicLM — Reference Architecture (Not Recommended for SonicStore)

Despite MusicLM's superior quality scores (FAD 2.1 vs MusicGen's 2.3), it is explicitly excluded from SonicStore's recommended stack because:

1. **API-only** — no local deployment path, network latency disqualifies live performance
2. **Hierarchical 3-stage inference** — even with API access, latency is higher than single-stage MusicGen
3. **No open weights** — cannot fine-tune, customize, or adapt
4. **MuLan conditioning** — proprietary joint embedding, cannot substitute custom conditioning

Its architectural insight (semantic token hierarchy → coarse acoustic → fine acoustic) is preserved in practice by SonicStore's own tier structure: RAVE handles fine acoustic modulation, MusicGen handles coarse semantic generation.

---

## 6. Implementation Paths

### 6.1 Hackathon MVP (48 Hours)

**Scope:** Demonstrate real-time generative response to live audio input.

**Day 1 — Core Loop (0-24 hours):**

| Hour | Task | Output |
|------|------|--------|
| 0-2 | Environment setup: audiocraft + RAVE + Redis | Working dev environment |
| 2-5 | SonicStore feature extraction: BPM + chroma via Redis | Feature stream running |
| 5-9 | RAVE integration: load pretrained model, verify real-time playback | <10ms audio output |
| 9-13 | Feature → RAVE latent mapping: simple linear projection | Responsive audio |
| 13-18 | MusicGen-Small integration: text prompt → audio | Generation working |
| 18-21 | Feature → prompt pipeline: SonicStore features → MusicGen text | Automated conditioning |
| 21-24 | Integration: RAVE + MusicGen running simultaneously | Two-tier stack live |

**Day 2 — Polish and Demo (24-48 hours):**

| Hour | Task | Output |
|------|------|--------|
| 24-28 | Smooth crossfade between RAVE output and MusicGen output | Seamless transitions |
| 28-33 | Web UI: show feature extraction, prompt, generated audio | Demo-ready interface |
| 33-38 | Latency optimization: torch.compile + Flash Attention | <2s for 10s audio |
| 38-43 | Demo rehearsal with musician: identify failure modes | Hardened demo |
| 43-47 | Curated prompt library: pre-tested prompts that work well | Reliable demo |
| 47-48 | Buffer: fix critical issues | Ready to present |

**Dependencies and Risks:**

| Dependency | Risk | Mitigation |
|------------|------|-----------|
| RAVE pretrained model quality | Model may not suit desired genre | Pre-select and test 3+ models |
| MusicGen-Small quality | May generate incoherent output | Curate prompt templates |
| Redis availability | Cold start on demo day | Run Redis locally, not cloud |
| Hardware VRAM | OOM on demo machine | Test with target hardware, have CPU fallback |
| Live audio input latency | OS audio driver latency | Pre-configure ASIO/CoreAudio buffer |

### 6.2 Post-Hackathon MVP (4-8 Weeks)

**Scope:** Production-quality interactive music generation with SonicStore integration.

**Architecture additions:**
1. **MusicGen-Melody** (1.5B) replacing Small — melody conditioning from live input
2. **Fine-tuned RAVE models** trained on curated genre-specific datasets
3. **Feature → prompt LLM** — replace hardcoded template with GPT-4o mini generating rich prompts from features
4. **Stable Audio Open** for async quality rendering
5. **Persistent inference server** (FastAPI + background workers) for multi-user scenarios

**Technical upgrades:**
- ONNX Runtime export of MusicGen for 1.8× speedup vs PyTorch
- Speculative decoding with MusicGen-Stereo-Small as draft model
- Streaming WebSocket API for frontend consumption
- Dynamic batching for throughput scaling

### 6.3 Production Scale (3-6 Months)

**Architecture:**
```
                        Load Balancer
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        RAVE Server    MusicGen Server  Diffusion Server
        (CPU cluster)  (GPU: A10G×4)    (GPU: A100×2)
              │              │              │
              └──────────────┼──────────────┘
                             │
                   Feature Routing Service
                             │
                    SonicStore Feature API
```

**Key production considerations:**
- Model serving via TorchServe or Triton Inference Server
- TensorRT compilation for RAVE and MusicGen on NVIDIA hardware
- KV-cache pooling with vLLM-style PagedAttention for MusicGen
- Multi-tenant isolation with per-user generation queues
- Prompt injection safety filtering (prevent adversarial prompts)

---

## 7. Decision Matrix

### 7.1 Architecture vs. SonicStore Requirements

| Architecture | Live Perf (<50ms) | Text Control | Quality | Open Source | Hackathon Fit |
|--------------|------------------|--------------|---------|-------------|---------------|
| **RAVE** | ✅ Excellent | ❌ No text | 🔶 Good | ✅ Yes | ✅ Yes |
| **MusicGen-Small** | ⚠️ Near (~1s) | ✅ Full T5 | ✅ High | ✅ Apache 2.0 | ✅ Yes |
| **MusicGen-Medium** | ⚠️ ~2s | ✅ Full T5 | ✅ High+ | ✅ Apache 2.0 | 🔶 If 16GB+ VRAM |
| **MusicGen-Melody** | ⚠️ ~3s | ✅ T5+melody | ✅ High+ | ✅ Apache 2.0 | 🔶 Stretch goal |
| **AudioLDM-2** | ❌ ~8-15s | ✅ CLAP | ✅ Very High | ✅ Apache 2.0 | 🔶 Async only |
| **Stable Audio Open** | ❌ ~8-15s | ✅ Text+timing | ✅ Very High | ✅ Stability AI | 🔶 Async only |
| **Riffusion** | ❌ ~3s + artifacts | ✅ CLIP | 🔶 Medium | ✅ MIT | ❌ Deprecated |
| **Jukebox** | ❌ Hours | ⚠️ Genre/artist | ✅ High | ✅ MIT | ❌ Too slow |
| **MusicLM** | ❌ API latency | ✅ MuLan | ✅ Very High | ❌ API only | ❌ No local |

### 7.2 Recommended Model by Use Case

| Use Case | Primary Model | Fallback | Notes |
|----------|--------------|---------|-------|
| Live timbre modulation | RAVE | GAN vocoder | CPU-capable |
| Text-to-section generation | MusicGen-Small | MusicGen-Medium | FP16 required |
| Melody harmonization | MusicGen-Melody | MusicGen-Small (no melody) | 1.5B, 4GB FP16 |
| Style transfer | RAVE latent interpolation | AudioLDM-2 | RAVE faster |
| Export quality render | Stable Audio Open | AudioLDM-2 | Async, post-session |
| Demo fallback (no GPU) | RAVE only | Pre-generated audio | RAVE is CPU-viable |

### 7.3 Critical Path for Hackathon Success

The single most important architectural decision for the hackathon is:

**Run RAVE for everything real-time; run MusicGen for everything prompt-driven; never block the RAVE thread on MusicGen generation.**

This means:
1. RAVE runs in a dedicated audio thread with hard real-time priority
2. MusicGen runs in a background thread/process
3. Audio crossfading manages the transition between RAVE output and MusicGen output
4. If MusicGen fails or takes too long, RAVE continues uninterrupted

```python
# Architecture contract (pseudocode)
class SonicStoreGenerationEngine:
    def __init__(self):
        self.rave = RAVEStream(model="rave_percussion.ts")   # Real-time thread
        self.musicgen = MusicGenWorker(model="musicgen-small") # Background worker
        
    def on_audio_tick(self, audio_chunk: np.ndarray, features: dict):
        """Called every 10ms (hard real-time, never block)."""
        z = self.feature_projector(features)
        rave_output = self.rave.step(audio_chunk, z)  # <5ms
        
        # Mix RAVE with any pending MusicGen output (non-blocking)
        musicgen_chunk = self.musicgen.get_buffered(non_blocking=True)
        return crossfade(rave_output, musicgen_chunk, ratio=self.blend_ratio)
    
    def on_prompt(self, prompt: str):
        """Non-blocking prompt dispatch to background worker."""
        self.musicgen.generate_async(prompt, callback=self.on_musicgen_ready)
    
    def on_musicgen_ready(self, audio: np.ndarray):
        """Called when MusicGen completes (may be 1-5s after prompt)."""
        self.musicgen.queue_audio(audio)
        self.blend_ratio = 0.5  # Fade in MusicGen over next 2 seconds
```

---

## 8. References

### Primary Architecture Papers

[1] Caillon, A., & Esling, P. (2021). "RAVE: A variational autoencoder for fast and high-quality neural audio synthesis." *arXiv:2111.05011*. https://arxiv.org/abs/2111.05011

[2] Copet, J., et al. (2023). "Simple and Controllable Music Generation." *NeurIPS 2023*. arXiv:2306.05284. https://arxiv.org/abs/2306.05284

[3] Agostinelli, A., et al. (2023). "MusicLM: Generating Music From Text." *arXiv:2301.11325*. https://arxiv.org/abs/2301.11325

[4] Liu, H., et al. (2023). "AudioLDM 2: Learning Holistic Audio Generation with Self-supervised Pretraining." *arXiv:2308.05734*. https://arxiv.org/abs/2308.05734

[5] Evans, Z., et al. (2024). "Stable Audio Open." *arXiv:2407.14358*. https://arxiv.org/abs/2407.14358

[6] Dhariwal, P., et al. (2020). "Jukebox: A Generative Model for Music." *arXiv:2005.00341*. https://arxiv.org/abs/2005.00341

### Core Infrastructure Papers

[7] Défossez, A., et al. (2022). "High Fidelity Neural Audio Compression (EnCodec)." *arXiv:2210.13438*. https://arxiv.org/abs/2210.13438

[8] Zeghidour, N., et al. (2021). "SoundStream: An End-to-End Neural Audio Codec." *arXiv:2107.03312*. https://arxiv.org/abs/2107.03312

[9] Kumar, R., et al. (2024). "High-Fidelity Audio Compression with Improved RVQGAN (DAC)." *NeurIPS 2024*. arXiv:2306.06546.

### Inference & Optimization

[10] Lu, C., et al. (2022). "DPM-Solver: A Fast ODE Solver for Diffusion Probabilistic Model Sampling in Around 10 Steps." *NeurIPS 2022 Oral*. arXiv:2206.00927.

[11] Caillon, A., et al. (2022). "Streamable Neural Audio Synthesis With Non-Causal Convolutions." *arXiv:2204.07064*. https://arxiv.org/abs/2204.07064

[12] Song, J., et al. (2020). "Denoising Diffusion Implicit Models (DDIM)." *ICLR 2021*. arXiv:2010.02502.

### Evaluation & Metrics

[13] Grötschla, F., et al. (2025). "Benchmarking Music Generation Models and Metrics via Human Preference Studies." *ICASSP 2025*. arXiv:2506.19085.

[14] Kilgour, K., et al. (2019). "Fréchet Audio Distance: A Reference-Free Metric for Evaluating Music Enhancement Algorithms." *Interspeech 2019*.

---

*Document Version: 1.0*  
*Compiled: April 2026*  
*Research for SonicStore Project — Hackathon June 6-7, 2026*
*Bridges: 02-SOTA-MUSIC-GENERATION.md ↔ 04-INFERENCE-DEPLOYMENT.md*
