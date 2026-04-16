# SonicStore — Intake Document
## For Spec Pipeline
## 2026-04-05

---

## 1. What SonicStore Is

### Core Concept

SonicStore is an **agentic prosthetic for embodied listening** — a shared sensory organ that enables entangled composition between human composers and AI models.

Not a feature store. Not an API. A **space where composition happens** through four-way resonance between:
1. Human composer (body-knowledge, taste, intention)
2. Model A (generative capabilities, pattern recognition)
3. Model B (different capabilities, different patterns)
4. SonicStore itself (embodied listening, intuition, agency)

### The Shift

| From | To |
|------|-----|
| Feature extraction as service | Sensory embodiment as shared experience |
| Query/response API | Continuous sensorial field |
| Human uses tool | Human inhabits prosthetic |
| Models generate content | Models participate in discovery |
| SonicStore measures audio | SonicStore feels the sonorous |

---

## 2. Key Tensions (Decisions Required)

### Tension 1: Real-Time vs. The Sensorial

**The Conflict:**
- Technical Feasibility: <50ms requires edge+native (complex, limited market)
- User Research: Developers want convenience, managed infrastructure
- Competitive Intel: Successful APIs (Gladia, AssemblyAI) operate at 100-300ms
- The Sensorial: Human body-knowledge operates at proprioceptive speed (<50ms) and cognitive speed (1-2s)

**The Question:**
Does SonicStore serve:
- **Performance-critical** (<50ms): Live monitoring, interactive instruments, proprioceptive feedback
- **Production-critical** (<2s): DAW workflows, generative AI integration, cognitive reflection
- **Both**: Architecturally separated paths

**Research Insight:** The Contrarian warns that "real-time feature extraction often accounts for 70% of pipeline time" and "real-time is a spectrum with trade-offs." The Pattern Archaeologist found techniques (token-based, self-supervised) that may not survive real-time constraints.

**Decision Required:** Choose latency target(s) and accept trade-offs.

---

### Tension 2: Formalization vs. Body-Knowledge

**The Conflict:**
- Pattern Archaeologist: "Self-supervised primacy! Token-based representations!"
- Composer-Ethnographer: "The most vital aspects live in the body, not in theoretical frameworks"
- User (Danny): "Formalization isn't destructive — it's how we associate style with culture. But it can flatten if mass-produced."

**The Question:**
How does SonicStore formalize without flattening? How does it capture the "envelope" of acoustic instruments (soft→loud→falling off) rather than the flatness of electronic tones?

**Research Insight:** The Technical Poet found beauty in "discovered, not invented" techniques — formalizations that unveil inherent structure (graph representations, tree compression) rather than imposing artificial frameworks.

**Decision Required:** Define what formalization means for SonicStore — not capturing body-knowledge (impossible) but creating conditions for it to flourish.

---

### Tension 3: Infrastructure vs. Agency

**The Conflict:**
- Missing Bloomberg Thread: MIR lacks infrastructure (data feeds, backtesting frameworks)
- Agentic Prosthetic: SonicStore has its own intuition, surprises, participates
- Trust Architecture: "Won't get acquired" as differentiator requires open-core/self-hostable

**The Question:**
Is SonicStore:
- **Infrastructure**: Reliable, neutral, transparent pipes (the "Bloomberg for audio")
- **Agent**: Active participant with its own musical taste and suggestions
- **Both**: Infrastructure that becomes agentic through use

**Research Insight:** The Novel Angles document suggests "ungovernable by design" — not just open-source, but structured so no single entity controls it, not even founders.

**Decision Required:** Define SonicStore's agency. Can it be wrong? Can it mishear? Is error part of its value?

---

### Tension 4: Human-Model Entanglement vs. Human Control

**The Conflict:**
- Agentic Prosthetic: Four-way entanglement (human, model A, model B, SonicStore)
- User Research: Musicians need control, intention, cultural context
- Gen AI Landscape: Current tools generate without understanding, creating "walled gardens"

**The Question:**
Does the human:
- **Lead**: Direct the models through SonicStore
- **Entangle**: Resonate with models through SonicStore
- **Curate**: Choose from model-generated possibilities
- **Discover**: Use SonicStore to navigate sonic territory

**Research Insight:** Danny: "The act of writing music is as much about discovery as it is anything else... listening is the most important part of this work."

**Decision Required:** Define the human's role in the quartet. Not hierarchy, but what?

---

## 3. Technical Architecture (Hypotheses)

### Core Hypothesis

SonicStore as **continuous sensorial field** rather than query/response API.

### Components

#### 1. The Sensorial Layer
- **Input**: Raw audio streams (from human performance, model generation, file playback)
- **Processing**: Real-time feature extraction as **felt qualities** not measurements
  - Chroma as "color" not vector
  - Rhythm as "pulse" not onset detection
  - Timbre as "texture" not spectral centroid
- **Output**: Sonorous qualities inhabitable by human and models

**Technical Questions:**
- What representation enables this translation?
- Token-based (VampNet) vs. continuous embeddings?
- How to preserve "envelope" (soft→loud→falling off) in representation?

#### 2. The Embodiment Layer
- **Human Interface**: Not GUI, but **somatic** — haptic feedback, spatial audio, visualization that mirrors body-knowledge
- **Model Interface**: Not API calls, but **persistent presence** — models inhabit SonicStore, feel changes in real-time
- **SonicStore State**: Maintains its own "listening state" — what it feels, what surprises it, what it suggests

**Technical Questions:**
- How does SonicStore maintain state across sessions?
- How do models "inhabit" rather than query?
- What does SonicStore's "surprise" look like technically?

#### 3. The Resonance Layer
- **Human → SonicStore**: Body-knowledge translated to sonorous qualities
- **SonicStore → Models**: Sonorous qualities as generative constraints/possibilities
- **Models → SonicStore**: Generated audio as new sonorous field
- **SonicStore → Human**: Sonorous qualities as felt experience (haptic, visual, auditory)

**Technical Questions:**
- Bidirectional translation protocols?
- Latency tolerances for each direction?
- Conflict resolution when human, models, and SonicStore disagree?

---

## 4. Use Cases (Validated)

### Primary: Composer-Model Co-Creation
Human composer works with two (or more) models, SonicStore as shared sensory organ:
- Human improvises, SonicStore translates to sonorous field
- Model A responds with variations
- Model B responds with counterpoint
- SonicStore suggests connections human didn't hear
- Human chooses, redirects, discovers

**Validation:** Aligns with Danny's experience as composer, the Composer-Ethnographer's body-knowledge, and the Agentic Prosthetic concept.

### Secondary: Gen AI Evaluation & Iteration
SonicStore as ecological infrastructure for sustainable generative AI:
- Generate (Suno/Udio) → Analyze (SonicStore) → Curate (Human) → Generate variations
- Systematic evaluation of model outputs
- "Backtest for beats" — did v5 actually improve instrument separation?

**Validation:** Addresses Gen AI Landscape finding that models generate without understanding, creating unsustainable production without feedback loops.

### Tertiary: Research Bridge
SonicStore operationalizes ISMIR advances:
- Researchers publish models
- SonicStore hosts as embodied listening
- Composers use, generating research datasets
- Practice produces theory (not just tests it)

**Validation:** Addresses MIR Landscape gap between research and production.

---

## 5. Open Questions for Spec Phase

### Technical
1. Latency target(s): <50ms, <2s, or both with architectural separation?
2. Representation: Token-based, continuous, or hybrid?
3. State management: How does SonicStore maintain "listening state"?
4. Translation: Bidirectional protocols between human body-knowledge and model representations?
5. Agency: How does SonicStore surprise? Suggest? What is its "intuition"?

### Product
6. Human role: Leader, entangled partner, curator, or discoverer?
7. Model relationships: Two models as default? Configurable ensemble?
8. Ownership: Who owns music created by four entangled agents?
9. Scale: Intimate quartet only, or expandable to multiple humans/models?
10. Non-musical sound: Bird songs, industrial recordings — in scope or out?

### Business
11. Model: Open-core + managed service? Ungovernable by design?
12. Revenue: Infrastructure pricing? Creative tool pricing? Research partnership?
13. Trust: "Won't get acquired" as differentiator — viable?
14. Competition: Gladia/AssemblyAI at 100-300ms, SonicStore at different latency/philosophy?

---

## 6. What We Know vs. What We Don't

### Confirmed (High Confidence)
- Technical feasibility of <50ms with edge+native (Technical Feasibility)
- Market demand for real-time audio features (Competitive Intel)
- Human body-knowledge is vital, pre-verbal, tacit (Composer-Ethnographer)
- Gen AI models generate without understanding (Gen AI Landscape)
- ISMIR research rarely reaches production (MIR Landscape)

### Hypothesized (Medium Confidence)
- SonicStore as agentic prosthetic (Agentic Prosthetic document)
- Four-way entanglement as creative paradigm (conversation)
- The sensorial/sonorous as translation layer (conversation)
- "Backtest for beats" as product opportunity (Synthesis)

### Unknown (Requires Validation)
- Can humans feel what models generate through SonicStore?
- Does SonicStore's agency enhance or interfere with creativity?
- What representation enables both human body-knowledge and model processing?
- Is this a product, platform, instrument, or something else?

---

## 7. Spec Phase Success Criteria

Spec is complete when:
1. **Latency decision made**: <50ms, <2s, or both with clear architectural separation
2. **Human role defined**: Leader, entangled partner, curator, or discoverer
3. **SonicStore agency specified**: What it does, doesn't do, how it surprises
4. **Representation chosen**: Token-based, continuous, or hybrid; preserves "envelope"
5. **Use case prioritized**: Composer co-creation, Gen AI evaluation, or research bridge
6. **Business model viable**: Revenue path that supports "ungovernable by design" if chosen

---

## 8. Research Artifacts

All supporting research in:
```
/home/d-tuned/projects/sonic-store/research/
├── competitive-intel.md
├── quant-music-mapping.md
├── technical-feasibility.md
├── mir-landscape.md
├── gen-ai-landscape.md
├── user-research.md
├── archive-contrarian.md
├── archive-pattern-archaeologist.md
├── archive-composer-ethnographer.md
├── archive-technical-poet.md
├── archive-adjacent-possible.md
├── 00-SYNTHESIS.md
├── THREADS.md
├── NOVEL-ANGLES.md
├── MAJOR-TOM-OBSERVATIONS.md
└── AGENTIC-PROSTHETIC.md
```

Total: ~92KB across 16 documents

---

*Intake document prepared by: Major Tom*  
*Based on: 6 parallel research streams, 5 archive explorations, conversational synthesis*  
*Status: Ready for spec pipeline — decisions required on tensions, hypotheses to validate*
