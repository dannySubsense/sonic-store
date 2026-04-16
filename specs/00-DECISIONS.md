# SonicStore Decision Memo
**Date:** 2026-04-16
**Author:** Technical Director
**Status:** LOCKED — All four decisions approved by Composer (2026-04-16)

---

## Purpose

This document resolves the four critical decisions identified in 00-SYNTHESIS.md. Each decision is framed as a binary choice with a clear recommendation. Once approved, these decisions are **locked** — they become constraints, not topics for further discussion.

The hackathon is June 6-7. That's 51 days. These decisions unblock architecture, which unblocks implementation, which unblocks rehearsal. Every day they stay open costs more than a wrong answer.

---

## Decision 1: Latency Target

**Question:** <50ms (live performance) or <2s (production workflow)?

**Recommendation: <2s for v1. <50ms deferred.**

**Reasoning:**
- <50ms requires edge + native (C++/Rust), which is architecturally complex and limits the addressable market
- <2s enables cloud + Python, which means we use audiocraft/librosa directly without FFI layers
- The hackathon audience (Berklee musicians) will experience SonicStore as a demo, not as an instrument they play — 1-2s response feels interactive in that context
- RAVE can be added as a real-time tier post-hackathon without rearchitecting

**What we give up:** Live instrument feel. A musician can't jam with SonicStore at <2s latency — they can converse with it. That's good enough for June 7. It's not good enough for the Agentic Prosthetic vision, but that's a later problem.

**[X] APPROVED** / **[ ] OVERRIDE** — Danny's call

---

## Decision 2: Product Identity

**Question:** Infrastructure? Research Bridge? Gen AI Evaluator? Agentic Prosthetic?

**Recommendation: Feature Store + Feedback Loop (Threads 2 + 7).**

The Agentic Prosthetic is the **north star** — it informs why we care, what makes this project philosophically distinct, and where it goes in 2027+. It is explicitly NOT the v1 product.

**The v1 product is:**
> Real-time MIR feature extraction as a service, with an AI feedback loop that generates complementary audio from extracted features.

**The hackathon demo tells this story:**
1. Musician plays live audio into SonicStore
2. SonicStore extracts features in real-time (chroma, BPM, key, energy, onset)
3. Features are displayed visually (the "systematic ear" — you see what your music is doing)
4. Features condition a MusicGen prompt automatically
5. MusicGen generates a complementary response (the "feedback loop")
6. The musician hears AI respond to their playing

That demo contains the DNA of every thread:
- Thread 1 (Systematic Ear): You see your music's features quantified
- Thread 2 (Missing Bloomberg): The feature store infrastructure exists
- Thread 4 (Evaluation Layer): You're evaluating AI output against extracted features
- Thread 7 (Feedback Loop): Generate-Analyze-Curate cycle is live
- Agentic Prosthetic: The system "listens" and "responds" — the embryo of agency

**What we give up:** The full prosthetic vision. Multi-model entanglement. SonicStore's own "intuition." Body-knowledge interfaces. These are powerful ideas that belong in a research paper or a 2027 roadmap, not a 48-hour prototype.

**[X] APPROVED** / **[ ] OVERRIDE** — Danny's call

---

## Decision 3: Trust Architecture

**Question:** Open-core? Ungovernable by design? Anti-acquisition positioning?

**Recommendation: MIT license. Open source. Ship it.**

**Reasoning:**
- MIT is the most permissive, most understood, lowest-friction license
- "Ungovernable by design" is a governance problem, not a licensing problem — you can't architect ungovernability until you have something worth governing
- The trust comes from the code being open and the project being real, not from legal structures
- If the project succeeds, you can add foundation governance later. If it doesn't, the license was irrelevant.

**What we give up:** The philosophical purity of "ungovernable by design." The competitive moat of "no one can acquire this." Both are premature optimizations. You don't need anti-acquisition positioning when you don't have a product.

**[X] APPROVED** / **[ ] OVERRIDE** — Danny's call

---

## Decision 4: Research Partnerships

**Question:** Operationalize ISMIR models? Revenue share with researchers?

**Recommendation: Deferred. Use open-source models only.**

**Reasoning:**
- Partnership conversations require leverage, which requires a working product
- librosa + audiocraft + essentia cover every feature extraction and generation need for v1
- All three are permissively licensed (ISC, Apache 2.0/MIT, AGPL respectively — note: essentia's AGPL means our open-source approach is compatible)
- If the hackathon demo is compelling, partnership conversations happen naturally at AIMS/ISMIR

**What we give up:** Access to cutting-edge unpublished models. Early-mover advantage on operationalizing ISMIR research. Both require a product to exist first.

**[X] APPROVED** / **[ ] OVERRIDE** — Danny's call

---

## Summary

| Decision | Recommendation | Risk Level |
|----------|---------------|------------|
| Latency | <2s (defer <50ms) | Low — can add RAVE tier later |
| Identity | Feature Store + Feedback Loop | Medium — constrains scope, enables shipping |
| Trust | MIT, open source | Low — most flexible starting point |
| Partnerships | Deferred | Low — open models sufficient |

**North Star (preserved, not abandoned):**
> SonicStore as agentic prosthetic for embodied listening — a shared sensory organ enabling entangled composition between human composers and AI models. This vision drives long-term research direction. It does not drive the June 7 demo.

---

## What Happens After Approval

1. These decisions become constraints in all subsequent specs
2. Architecture design begins immediately (specs/02-ARCHITECTURE.md)
3. Implementation planning follows within 24 hours (specs/03-ROADMAP.md)
4. Code starts flowing within 48 hours of approval

---

*Decision memo by: Technical Director*
*For: Danny (Composer)*
*Deadline for approval: Today. Every day these stay open is a day we're not building.*
