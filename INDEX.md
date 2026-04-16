# SonicStore Master Index
**Project:** SonicStore — AI Music Platform  
**Location:** `~/projects/sonic-store/` (canonical)  
**Created:** 2026-04-11  
**Purpose:** Single source of truth for all SonicStore resources

---

## Quick Navigation

| Section | Description | Path |
|---------|-------------|------|
| [Research Reports](#research-reports) | 6 parallel research streams (00-06) | `research/` |
| [Strategic Intelligence](#strategic-intelligence) | Competitive analysis, landscape | `research/` |
| [Technical References](#technical-references) | Audio/MIR knowledge base | `references/audio-tech-kb/` |
| [Specifications](#specifications) | Architecture specs (when created) | `specs/` |
| [Audit & Assessment](#audit--assessment) | Major Tom's navigation guide | `../.openclaw/workspace/` |
| [Idea Evolution](#idea-evolution) | Historical captures | `life/resources/captures/` |

---

## Research Reports (Tier 1 — Core)

**Location:** `~/projects/sonic-store/research/`

### 00-06 Series (Read in Order)

| # | Report | Key Questions | Status |
|---|--------|---------------|--------|
| 00 | **SYNTHESIS.md** | Strategic tensions, product hypotheses, unresolved decisions | **START HERE** |
| 01 | AUDIO-DSP-MIR.md | DSP fundamentals, feature extraction, real-time constraints | Technical foundation |
| 02 | SOTA-MUSIC-GENERATION.md | Suno, Udio, Stable Audio; Gen AI landscape | Market analysis |
| 03 | MODEL-ARCHITECTURE.md | Neural architectures, embeddings, self-supervised | ML engineering |
| 04 | INFERENCE-DEPLOYMENT.md | Edge vs cloud, latency, scaling | Infrastructure |
| 05 | DATA-TRAINING.md | Datasets, training pipelines | ML ops |
| 06 | GITHUB-MIR-DISCOVERY.md | Open-source ecosystem, build vs buy | Implementation |

### Strategic Intelligence (Tier 2)

| Document | Focus | Key Value |
|----------|-------|-----------|
| competitive-intel.md | Gladia, AssemblyAI, Spotify | Pricing, API stability risks |
| mir-landscape.md | Essentia, Librosa, Madmom | Library capabilities, licensing |
| gen-ai-landscape.md | Suno, Udio, Stable Audio | API gaps, integration potential |
| user-research.md | Developer interviews | Pain points, willingness-to-pay |
| technical-feasibility.md | <50ms validation | Proof-of-concept benchmarks |
| quant-music-mapping.md | Finance-MIR analogies | "Alpha generation" concept |

### Exploratory & Archived (Tier 3 — Skimmable)

- AGENTIC-PROSTHETIC.md — AI as creative partner (tangential)
- ARCHIVE-EXPLORATION-REPORT.md — Early broad exploration (superseded)
- archive-*.md files — Discarded angles (historical)
- hackathon-brief-2026.md — June 6-7 event planning (tactical)

---

## Technical References

**Location:** `~/projects/sonic-store/references/audio-tech-kb/` (symlinked from `~/life/resources/`)

**Original Created:** March 15, 2026  
**Scope:** Pre-existing audio/MIR technical foundation

### Contents

| Section | Files | Key Topics |
|---------|-------|------------|
| **Essentia.js** | 3 files | WebAssembly audio analysis, real-time patterns |
| **Max/MSP** | 1 file | DAW integration, external development |
| **ISMIR Papers** | 1 file | BeatNet+, BEAST, PESTO benchmarks |
| **Web Audio API** | 1 file | Browser audio processing, AudioWorklet |

### Integration Notes

This knowledge base predates the 00-06 research series (March 15 vs April 5). Key insights:
- Architecture recommendation: Hybrid (jweb prototype → Max-Net production)
- Performance targets: <50ms latency, <0.1 RTF (validated by ISMIR)
- Technology stack: Essentia.js + Web Audio API + Max/MSP

**Gap:** Not explicitly referenced in 00-SYNTHESIS.md — potential lost context

---

## Specifications

**Location:** `~/projects/sonic-store/specs/`

**Status:** Empty (awaiting spec pipeline)

**Next Steps:**
1. Resolve 4 critical decisions (latency target, product identity, trust architecture, research partnerships)
2. Run requirements-analyst → architect → planner
3. Generate 01-REQUIREMENTS.md, 02-ARCHITECTURE.md, etc.

---

## Audit & Assessment

**Location:** `~/.openclaw/workspace/SONICSTORE-RESEARCH-AUDIT.md`

**Prepared by:** Major Tom  
**Purpose:** Navigation guide through research corpus

### Key Sections
- Corpus map (28 documents organized by tier)
- Critical findings (feasibility ✅, need ✅, identity ⚠️)
- Domain knowledge inventory (DSP, ML, infrastructure, competitive)
- Architectural options (performance vs production vs hybrid)
- 12 additional threads (legal, ethics, business model, etc.)
- Recommended reading paths (30 min / 2 hour / 4 hour)

**Use this for:** Strategic overview before diving into research reports

---

## Idea Evolution (Historical)

**Original Capture:** `~/life/resources/captures/2026-03-17-ideas.md`

**First Concept:** (March 17, 2026)
> "AI music creation platform. Feature store + generative tools. Hackathon June 6-7. Spec sprint interview pending."

**Evolution Timeline:**
```
March 15: Audio-tech KB created (technical foundation)
March 16: POMSKI discovered (generative inspiration)
March 17: SonicStore named and captured (concept born)
April 5-10: Research sprints (strategic expansion)
```

**Scope Question:** March concept was "feature store + generative tools" — April research explores infrastructure, research bridge, evaluator. Which is the real focus?

---

## Related Resources (External to Project)

### POMSKI Sequencer
**Location:** `~/life/resources/music-dev/pomski.md`

Python live-coding MIDI environment. Relevance:
- Algorithmic composition (Euclidean, Markov, chaos)
- Live performance philosophy ("code as notation")
- **Potential connection:** Generative algorithms for SonicStore?

### QMD Integration (Option B)
**Status:** Not yet implemented

**Benefit:** Semantic search across all SonicStore documents
**Approach:** Add `sonic-store` collection to QMD index
**Scope:** research/, references/audio-tech-kb/, specs/ (when created)

---

## Critical Decisions Requiring Resolution

Before spec pipeline, resolve:

1. **Latency Target:** <50ms (live) vs <2s (production)
2. **Product Identity:** Infrastructure vs Research Bridge vs Gen AI Evaluator
3. **Trust Architecture:** Open-core viability, anti-acquisition positioning
4. **Research Partnerships:** Operationalize ISMIR models? Revenue share?

**Reference:** 00-SYNTHESIS.md for full analysis of each tension

---

## File Inventory

```
~/projects/sonic-store/
├── INDEX.md                          ← This file
├── research/
│   ├── 00-SYNTHESIS.md               ← Start here
│   ├── 01-AUDIO-DSP-MIR.md
│   ├── 02-SOTA-MUSIC-GENERATION.md
│   ├── 03-MODEL-ARCHITECTURE.md
│   ├── 04-INFERENCE-DEPLOYMENT.md
│   ├── 05-DATA-TRAINING.md
│   ├── 06-GITHUB-MIR-DISCOVERY.md
│   ├── AGENTIC-PROSTHETIC.md
│   ├── ARCHIVE-EXPLORATION-REPORT.md
│   ├── archive-*.md (6 files)
│   ├── competitive-intel.md
│   ├── gen-ai-landscape.md
│   ├── hackathon-brief-2026.md
│   ├── MAJOR-TOM-OBSERVATIONS.md
│   ├── mir-landscape.md
│   ├── NOVEL-ANGLES.md
│   ├── quant-music-mapping.md
│   ├── technical-feasibility.md
│   ├── THREADS.md
│   └── user-research.md
├── references/
│   └── audio-tech-kb/                ← Symlink to ~/life/resources/
│       ├── README.md
│       ├── essentia-js/
│       ├── ismir-papers/
│       ├── max-msp/
│       └── web-audio-api/
└── specs/                            ← Empty (awaiting spec pipeline)

External references:
~/life/resources/captures/2026-03-17-ideas.md
~/life/resources/music-dev/pomski.md
~/.openclaw/workspace/SONICSTORE-RESEARCH-AUDIT.md
```

---

## Next Steps

1. **Review INDEX.md** — Confirm structure meets needs
2. **Read 00-SYNTHESIS.md** — Understand strategic tensions
3. **Resolve 4 critical decisions** — Latency, identity, trust, partnerships
4. **Run spec pipeline** — requirements-analyst → architect → planner
5. **Consider QMD integration** — Semantic search across corpus

---

## Questions?

Major Tom is standing by for clarification, additional consolidation, or QMD setup.

---

*Last updated: 2026-04-11*  
*Consolidation by: Major Tom*
