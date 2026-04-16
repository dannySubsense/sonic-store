# Music Tech Hackathon 2026 — Project Brief

**Created:** 2026-03-15  
**Context:** Conversation between Danny and Major Tom about Berklee AIMS-adjacent hackathon (June 6-7, 2026)

---

## The Event

- **What:** Music Technology Hackathon, Boston
- **When:** June 6-7, 2026 (immediately following Berklee AIMS conference, June 3-5)
- **Where:** Boston, MA, co-hosted with Berklee
- **Format:** 2-day team-based prototyping, 3-4 people per team
- **Sponsors:** Ableton, MuseHub, Audiotool
- **Themes:** Creative Tools for Musicians, Research-to-Practice, Accessibility & Inclusion, New Listening Experiences

**Key Detail:** Berklee musicians/artists can act as "creative leads" — defining artistic vision while technologists build.

---

## Research Sources Identified

### Paper Archives
- **ISMIR:** 2,458 papers (2000-2024) — ISMIR25Meta dataset
- **arXiv cs.SD:** Sound & Music Computing preprints
- **AIMS 2026:** Fresh papers from June 3-5 conference

### Key Datasets
| Dataset | Description | Source |
|---------|-------------|--------|
| FMA | Free Music Archive, 100K+ tracks | Defferrard et al., ISMIR 2017 |
| MTG-Jamendo | Music tagging dataset | Serra, ICML 2019 |
| Music4All A+A | Multimodal MIR dataset | arXiv 2025 |
| LargeSHS | Cover song detection/adaptation | ISMIR 2025 |
| PMEmo | Music emotion recognition | Zhang et al., 2018 |

---

## Project 1: Feature Store for Audio ("SonicStore")

**Concept:** Real-time MIR feature extraction as a service — "AWS for audio features"

**The Problem:**
- MIR demos use pre-computed features (not viable for live)
- Real-time extraction kills CPU
- No middle ground between DIY (librosa) and closed APIs (Spotify internal)

**Architecture:**
```
Sources (Mic/DAW/File) → Ingestion (WebSocket/gRPC) → Feature Engine (Rust + Python FFI)
                                                              │
                    ┌─────────────────────────────────────────┼─────────────────────────────┐
                    │                                         │                             │
                    ▼                                         ▼                             ▼
           Hot Store (Redis)                          Warm Store (DuckDB)            Cold Store (S3)
           Last 5 min                                 Last 24 hrs                    Archive
                    │                                         │                             │
                    └─────────────────────────────────────────┼─────────────────────────────┘
                                                              │
                                                       Query API (REST/gRPC/GraphQL)
                                                              │
                                                       Clients (DAW plugins, web apps, Python SDK)
```

**Tech Stack Recommendation:**
- Feature Engine: Rust + Python FFI (latency + MIR ecosystem)
- Hot Store: Redis Streams (sub-10ms reads, pub/sub)
- Warm Store: DuckDB (columnar, analytical)
- Cold Store: S3 + Parquet (cheap, standard)
- Protocol: gRPC + WebSocket

**2-Day Hackathon MVP:**
- Single feature: chroma vectors only
- File upload ingestion (not real-time streaming)
- Hot storage only (Redis)
- REST API: `POST /analyze` → `GET /features/:id`
- Demo client: web UI showing chroma heatmap

---

## 


**Concept:** Takes MIR/ML research papers → generates working prototype skeletons

**The Problem:** Gap between research and working code is massive in music tech

**Architecture:**
```
PDF/URL (ISMIR/arXiv) → Parser (Grobid/PyPDF) → LLM Extractor (Claude/Code model)
                                                          │
                    ┌─────────────────────────────────────┼──────────────────────┐
                    │                                     │                      │
                    ▼                                     ▼                      ▼
           Model Code (PyTorch/JAX stub)       Data Loader (dataset download)   Eval Setup (metrics, baselines)
```

**Key Insight:** Composable with Feature Store — papers need features, Feature Store provides infrastructure

---

## Early Ideas Explored (Quant-Music Hybrid)

1. **Backtest for Beats** — Framework for testing music generation models like trading strategies (novelty vs. training data, structural coherence, human preference correlation)

2. **Alpha Generator for Samples** — Factor modeling for sample libraries (find the underused 30-second clip that fits your track)

3. **Regime Detection for Music** — Unsupervised segmentation identifying track structure changes (verse→chorus, buildup→drop)

4. **Paper-to-Prod Pipeline** — (Selected as Project 2 above)

---

## Divergent Ideas (Non-Quant)

### Creative Tools for Failure Modes
- **Boredom Detector:** Analyzes DAW project, flags when you're stuck in micro-tweaks
- **Idea Graveyard:** Extracts seeds from abandoned projects, tags why you left
- **Constraint Roulette:** Locks random DAW parameters to force creativity via scarcity

### Accessibility as Performance Art
- **Haptic Composition:** Full haptic vest for deaf audiences — melody as location (high=shoulders, low=hips), rhythm as pulse, timbre as texture

---

## Decisions Made

| Item | Status |
|------|--------|
| Attend hackathon? | Considering — ~12 weeks to prepare |
| Projects to build | 2: Feature Store + Paper-to-Prod |
| Hackathon strategy | TBD: ship MVP before, or build during? |
| Team | TBD: solo or recruit Berklee musicians? |
| Tech stack | TBD: awaiting Danny's preferences |

---

## Next Steps

- [ ] Danny to clarify hackathon deadline strategy
- [ ] Danny to confirm team approach (solo vs. recruit)
- [ ] Danny to indicate tech stack preferences
- [ ] Major Tom to present detailed architecture for both projects
- [ ] Begin MVP development upon explicit approval

---

## Links

- Hackathon page: https://certified.musichackspace.org/events/hackathon-boston-june-2026
- Berklee AIMS: https://www.berklee.edu/beatl/aims
- ISMIR papers: https://transactions.ismir.net/
