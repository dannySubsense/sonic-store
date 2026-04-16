# Sonic Store — Archive Exploration Report
## ISMIR, arXiv cs.SD, AIMS 2026 Deep Dive
## Documented 2026-04-05

---

## Exploration Methodology

Five researchers with distinct sensibilities explored paper archives without specific agendas:

| Researcher | Sensibility | Status | Output |
|------------|-------------|--------|--------|
| Pattern Archaeologist | Finds repeating structures across domains | ✅ Complete | Detailed findings |
| Contrarian | Challenges assumptions, surfaces dangers | ✅ Complete | Detailed findings |
| Adjacent Possible | Cross-domain connections | ⏳ Pending | — |
| Composer-Ethnographer | Embodied knowledge, creative practice | ❌ Failed | Truncated output |
| Technical Poet | Aesthetic qualities, beauty | ❌ Failed | File not written |

**Note on failures:** Two agents (Composer-Ethnographer, Technical Poet) produced truncated outputs or failed to complete file writes. This suggests the open-ended exploration task may be too broad for single-pass completion, or the agents encountered token/output limits during synthesis.

---

## Part 1: The Contrarian's Warning

### Core Challenge: Real-Time Feature Extraction as a Service

The contrarian analysis reveals that **our central premise may be flawed** — not invalid, but requiring significant revision.

### Key Assumptions to Question

**1. Real-time without trade-offs is achievable**
- Research shows real-time feature extraction introduces latency that undermines responsiveness
- Example: Talking portrait synthesis (arXiv:2411.13209) shows AFE "introduces latency and limits responsiveness"

**2. Computational resources are sufficient at scale**
- Hardware-aware quantization papers identify "limited computational resources" as primary challenge (arXiv:2507.07903)
- Cloud services cannot universally provide real-time extraction

**3. Feature extraction is lightweight**
- **Critical finding:** FEBench benchmarks reveal real-time feature extraction "often accounts for a huge proportion of execution time of the online machine learning pipeline (e.g., taking 70% time in the sales prediction service)"
- Feature extraction is frequently the **bottleneck**, not a lightweight component

**4. Techniques generalize across applications**
- Significant generalization challenges when moving from controlled datasets to real-world conditions
- Real-time percussive technique recognition (ISMIR 2023) shows domain-specific failures

**5. Real-time is binary**
- Community increasingly acknowledges real-time exists on a **spectrum** with trade-offs between latency, accuracy, resource consumption (ISMIR 2026 CFP)

### Dangers Identified

| Danger | Evidence | Implication for SonicStore |
|--------|----------|---------------------------|
| Latency-induced unresponsiveness | AFE limits responsiveness in real-time apps | Interactive systems may feel broken |
| Resource consumption bottlenecks | 70% of pipeline time in some services | Scaling becomes economically unviable |
| Hardware limitation blindness | FPGA/embedded constraints overlooked | Edge deployments may fail |
| Ethical overpromising | ISMIR warns about "bridging technical innovations with real-world creative practice" | Risk of disappointing users |
| Architectural fragility | Sliding window approaches limit long-term dependency capture | Systems may fail on complex musical structures |

### What Research Explicitly Warns Against

1. **Ignoring hardware-aware optimization** — Quantization and hardware-aware design are necessities, not optional extras
2. **Assuming technique transferability** — Lab techniques fail in real-world conditions
3. **Treating real-time as afterthought** — ISMIR 2026 includes "real-time considerations" as core track; must be first-class design concern
4. **Overlooking real-world evaluation metrics** — Benchmarks measure accuracy without latency, jitter, resource variance
5. **Neglecting failure mode analysis** — Need to study what doesn't work (VLA systems show "task failure rates of up to 96.7%" when feature extraction fails)

### Contrarian Recommendations

**For SonicStore specifically:**

1. **Question the real-time premise** — Consider near-real-time with bounded latency guarantees instead of hard real-time promises
2. **Design for heterogeneous latency** — Graceful degradation when real-time constraints cannot be met
3. **Invest in hardware-aware optimization early** — Make quantization and FPGA adaptation core to design
4. **Create domain-specific extraction pipelines** — One-size-fits-all may be fundamentally flawed
5. **Publish failure case studies** — Document where assumptions broke down

### The Uncomfortable Truth

The research suggests **SonicStore's initial premise needs significant revision** — not abandonment, but a more nuanced, humble approach acknowledging substantial challenges across multiple domains.

**Key tension:** The Pattern Archaeologist found exciting techniques; the Contrarian found those techniques fail in production. Both can be true.

---

## Part 2: The Pattern Archaeologist's Discovery

### Recurring Methodologies Across Domains

#### 1. Transformer Architectures and Variants
- **ISMIR 2023-2024:** Audio transformers for music representation learning, Nested Music Transformer for symbolic generation
- **arXiv cs.SD 2024-2025:** TRAMBA (Hybrid Transformer-Mamba), AudioGen-Omni (Unified Multimodal Diffusion Transformer), METEOR (Transformer VAE)
- **Pattern:** Progressive specialization of transformers for musical tasks while maintaining core self-attention

#### 2. Self-Supervised and Contrastive Learning
- **ISMIR:** PESTO (Pitch Estimation with Self-supervised Transposition-equivariant Objective)
- **arXiv:** METEOR uses VAE, general trend toward representation learning without labels
- **Pattern:** Pre-training on large unlabeled corpora using predictive or contrastive objectives

#### 3. Masked Modeling Approaches
- **ISMIR 2023:** VampNet — Music Generation via Masked Acoustic Token Modeling
- **Connection:** BERT-style masking from NLP applied to audio tokens
- **Pattern:** Learning by predicting masked portions of sequential data

#### 4. Hybrid Architectures
- **arXiv cs.SD 2024:** TRAMBA combines Transformer and Mamba architectures
- **Pattern:** Combining complementary strengths (Transformer's global attention + Mamba's efficient sequence modeling)

#### 5. Diffusion Models for Generation
- **arXiv cs.SD 2025:** AudioGen-Omni — Unified Multimodal Diffusion Transformer
- **Pattern:** Adapting successful image generation techniques to audio/music

### Structural Patterns in Problem Solving

| Pattern | Description | Example |
|---------|-------------|---------|
| **Representation-First** | Learn robust representations first, then apply to tasks | ISMIR decoupling representation from task heads |
| **Cross-Modal Learning** | Leverage audio-text/video relationships | CLaMP (Contrastive Language-Music Pre-Training) |
| **Progressive Refinement** | Coarse-to-fine generation | Nested Music Transformer sequential decoding |
| **Equivariant Design** | Build domain knowledge into architecture | PESTO's transposition-equivariant objective |
| **Phase-Aware Processing** | Preserve neglected signal information | Complex-valued CNNs for audio |
| **Token-Based** | Convert continuous to discrete for NLP techniques | VampNet's acoustic tokens |

### Techniques Reappearing in Different Clothing

**Contrastive Learning:**
- Direct contrastive loss (ISMIR)
- Supervised+self-supervised combination (ISMIR 2024)
- Language-music contrastive (CLaMP)

**Transformer Variants:**
- Standard, music-specific, nested, diffusion transformers, transformer VAEs

**Disentanglement:**
- METEOR separates melody and texture
- Style-content separation (from computer vision)

### Implications for SonicStore Design

#### Architectural Recommendations

1. **Hybrid Architecture** — Evaluate Transformer-Mamba hybrids (TRAMBA) for performance/computational efficiency balance
2. **Token-Based Representation** — Implement acoustic tokenization as foundational representation
3. **Progressive Generation** — Design with coarse-to-fine refinement strategies
4. **Phase-Aware Processing** — For high-fidelity applications, consider complex-valued representations
5. **Disentangled Controls** — Separate musical attributes (pitch, rhythm, timbre) for precise control

#### Training Strategy

1. **Self-Supervised Primacy** — Prioritize contrastive or masked prediction objectives for pre-training
2. **Cross-Modal Integration** — Incorporate text/visual modalities during pre-training
3. **Equivariant Objectives** — Build in musical invariances (transposition, time-stretching) directly
4. **Multi-Objective Optimization** — Combine representation learning with task-specific objectives

#### AIMS 2026 Considerations (Humanistic Dimensions)

1. **Inside Knowledge Focus** — Interfaces that help users understand how the system works
2. **Interdisciplinary Accessibility** — Usability across technical and humanities/social science users
3. **Ethical and Copyright Awareness** — Attribution, rights management, ethical use mechanisms
4. **Sustainability** — Computational efficiency and cultural sustainability
5. **Global Inclusivity** — Beyond Western/Global North musical traditions

---

## Part 3: Synthesis — Tensions and Opportunities

### The Central Tension

**Pattern Archaeologist says:** "The techniques exist and are converging toward powerful, flexible architectures."

**Contrarian says:** "Those techniques fail in production when real-time constraints are applied."

**Synthesis:** SonicStore exists at the intersection of **capability** and **constraint**. The research shows what's possible; the failures show what happens when we ignore constraints.

### Three Potential Responses

#### Response A: Embrace the Constraint
Accept that real-time feature extraction as a service is harder than assumed. Pivot to:
- Near-real-time with bounded latency (not hard real-time)
- Batch processing for non-interactive applications
- Edge-first architecture (client-side processing, not cloud API)

#### Response B: Solve the Constraint
Treat the contrarian warnings as engineering challenges to overcome:
- Hardware-aware optimization as core competency
- Domain-specific pipelines (not general-purpose)
- Graceful degradation architectures
- Publish failure modes and learn from them

#### Response C: Redefine the Problem
Question whether "feature extraction as a service" is the right framing:
- Maybe it's "representation learning infrastructure"
- Maybe it's "composer tooling" (Thread 1 from earlier synthesis)
- Maybe it's "research bridge" (operationalizing ISMIR advances)

### What the Archives Reveal About SonicStore's Moment

The research trajectory is clear: **from supervised task-specific models toward general representation learning via self-supervised objectives.**

This is SonicStore's opportunity:
- The research community has converged on representation-first approaches
- But the Contrarian shows these fail in production due to real-time constraints
- SonicStore could be the **production-grade implementation** of research-grade techniques

**The gap:** Research has the techniques; production needs the infrastructure. SonicStore bridges them — but only if we take the constraints seriously.

### Unanswered Questions from Failed Explorations

The Composer-Ethnographer and Technical Poet agents failed to complete. This leaves gaps:

- **Embodied knowledge:** How do composers actually work? What tacit knowledge does research miss?
- **Aesthetic qualities:** What makes a solution feel inevitable vs. forced? What is the "soul" of MIR?

These may require human exploration or different research methods.

---

## Part 4: Recommendations for Next Phase

### Immediate Actions

1. **Reconcile the tension** — Decide whether to embrace, solve, or redefine the real-time constraint
2. **Investigate the failed explorations** — Retry Composer-Ethnographer and Technical Poet with narrower scope, or explore these questions through different methods
3. **Deep dive on specific techniques** — The Pattern Archaeologist surfaced specific papers (TRAMBA, VampNet, PESTO, CLaMP) that deserve detailed analysis

### Open Research Questions

1. Can token-based representations (VampNet) achieve real-time performance, or is the conversion overhead too high?
2. Do Transformer-Mamba hybrids (TRAMBA) actually solve the efficiency problem, or just shift it?
3. What is the minimum viable feature set for "composer-as-quant" (Thread 1) applications?
4. How do AIMS 2026's humanistic concerns (accessibility, ethics, inclusivity) translate to technical architecture?

### The Deeper Question

The archives reveal a field in transition: from task-specific supervised learning to general representation learning via self-supervised objectives. SonicStore could ride this wave — or be crushed by it if we build for the old paradigm.

**The choice:** Build infrastructure for today's MIR (task-specific, supervised) or tomorrow's MIR (representation-first, self-supervised)?

---

## Appendix: Source Documents

All research materials stored in:
```
/home/d-tuned/projects/sonic-store/research/
├── archive-contrarian.md                    (this analysis)
├── archive-pattern-archaeologist.md         (this analysis)
├── archive-adjacent-possible.md             (pending)
├── archive-composer-ethnographer.md         (failed — truncated)
├── archive-technical-poet.md                (failed — not written)
└── ARCHIVE-EXPLORATION-REPORT.md            (this file)
```

### Key Papers Referenced

**From Contrarian:**
- arXiv:2411.13209 — Talking portrait synthesis latency issues
- arXiv:2507.07903 — Hardware-aware quantization challenges
- arXiv:2505.20894 — Sliding window limitations
- arXiv:2309.10519 — VLA system failure rates
- ISMIR 2023 poster_48 — Real-time percussive technique recognition
- FEBench benchmarks — Feature extraction as bottleneck

**From Pattern Archaeologist:**
- ISMIR 2023-2024 — Audio transformers, Nested Music Transformer
- arXiv cs.SD 2024-2025 — TRAMBA, AudioGen-Omni, METEOR
- ISMIR 2023 — VampNet, PESTO, CLaMP
- ISMIR 2026 CFP — Real-time considerations track

---

*Exploration conducted by: 5 sensibility-driven researchers*  
*Synthesis by: Major Tom*  
*Status: Partial completion (2/5 successful), significant findings despite failures*
