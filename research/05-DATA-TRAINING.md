# Music Data, Training Pipelines, and Augmentation
## A Comprehensive Research Report for Generative AI Systems

**Document Version:** 1.0  
**Last Updated:** 2026-04-09  
**Scope:** Masters/PhD-level technical analysis for the SonicStore project

---

## Executive Summary

This report provides an exhaustive analysis of music data resources, training methodologies, and augmentation strategies essential for building high-quality generative music AI systems. We examine the landscape of available datasets, their licensing frameworks, preprocessing requirements, and augmentation techniques that directly impact model performance. Special attention is given to the trade-offs between computational cost, data quality, and commercial viability.

---

## 1. Available Datasets for Music AI

### 1.1 OpenAI Jukebox Dataset

**Overview:** OpenAI's Jukebox (2020) introduced a large-scale generative model for music in the raw audio domain. While the full training dataset composition remains partially proprietary, the project revealed critical insights about data scale requirements.

**Known Characteristics:**
- **Scale:** ~1.2 million songs (approaching the size of the entire commercially recorded music catalog)
- **Sources:** Public web-crawled audio with metadata from LyricWiki and MusicBrainz
- **Metadata:** Artist, genre, year, lyrics alignment data
- **Format:** Raw audio at 44.1kHz, VQ-VAE compressed representations

**Access:**
- Raw dataset: Not publicly distributed (licensing constraints)
- Model weights: Available on GitHub and via OpenAI API
- Metadata: Partial release through research papers

**Citation:** Dhariwal, P., Jun, H., Payne, C., Kim, J. W., Radford, A., & Sutskever, I. (2020). Jukebox: A generative model for music. arXiv:2005.00341.

### 1.2 MAESTRO Dataset

**Overview:** MIDI and Audio Edited for Synchronized TRacks and Organization - the gold standard for piano performance research.

**Specifications:**
| Attribute | Value |
|-----------|-------|
| **Duration** | 172.3 hours |
| **Performances** | 1,184 classical piano pieces |
| **Composers** | 19 (Bach, Beethoven, Chopin, etc.) |
| **Format** | WAV (44.1kHz, 16-bit) + aligned MIDI |
| **Annotation** | Precise note-level alignments |
| **Update Cycle** | V3.0.0 (released 2021) |

**Licensing:** 
- **License:** Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)
- **Commercial Use:** Prohibited without additional licensing
- **Attribution:** Required

**Access:** [magenta.tensorflow.org/datasets/maestro](https://magenta.tensorflow.org/datasets/maestro)

**Citation:** Hawthorne, C., Stasyuk, A., Roberts, A., Simon, I., Huang, C. Z. A., Dieleman, S., ... & Eck, D. (2018). Enabling factorized piano music modeling and generation with the MAESTRO dataset. ICLR 2019.

**Quality Assessment:** ⭐⭐⭐⭐⭐ (5/5) - Industry benchmark for alignment accuracy and audio quality

### 1.3 FSD50K Dataset

**Overview:** Freesound Dataset 50k - a large-scale audio event dataset derived from Freesound.org, suitable for broader audio understanding beyond just music.

**Specifications:**
| Attribute | Value |
|-----------|-------|
| **Audio Clips** | 51,197 |
| **Labels** | 200 classes (Sound Event classes) |
| **Audio Duration** | 108.3 hours total |
| **Avg Clip Length** | 7.6 seconds |
| **Format** | OGG (Vorbis), 44.1kHz |
| **Annotation** | Weak labels (clip-level) + validation subset |
| **Vocabulary** | AudioSet Ontology subset |

**Licensing:**
- **License:** Creative Commons (varies by clip)
  - CC0: ~18,000 clips
  - CC BY: ~33,000 clips  
  - CC BY-NC: ~200 clips
- **Commercial Use:** Allowed for CC0 and CC BY; prohibited for CC BY-NC

**Access:** [zenodo.org/record/4060432](https://zenodo.org/record/4060432)

**Citation:** Fonseca, E., Favory, X., Ferraro, P., Tagliasacchi, M., Arzt, F., Oramas, S., ... & Serra, X. (2022). FSD50K: an open dataset of human-labeled sound events. IEEE/ACM Transactions on Audio, Speech, and Language Processing, 30, 829-852.

**Use Case:** Best suited for audio event detection, not high-fidelity music generation

### 1.4 MusicNet Dataset

**Overview:** A large-scale dataset of classical music recordings with fine-grained annotations, designed for music information retrieval research.

**Specifications:**
| Attribute | Value |
|-----------|-------|
| **Recordings** | 330 freely-licensed classical recordings |
| **Duration** | ~34 hours (30 GB) |
| **Labels** | 1,129,048 labels across 583 composers |
| **Instruments** | 11 instrument classes |
| **Format** | WAV (44.1kHz,PCM) |
| **Annotation granularity** | Note-by-note (onset, offset, instrument, measure position, beat) |
| **Composer coverage** | 19th-century European orchestral works |

**Licensing:**
- **License:** Public Domain (CC0) for most recordings
- **Commercial Use:** Permitted
- **Attribution:** Not required but encouraged

**Access:** [zenodo.org/record/5120004](https://zenodo.org/record/5120004)

**Citation:** Thickstun, J., Harchaoui, Z., & Kakade, S. (2017). Learning features of music from scratch. ICLR 2017.

**Quality Assessment:** ⭐⭐⭐⭐ (4/5) - Excellent annotations but limited genre diversity (classical only)

### 1.5 AudioSet Dataset

**Overview:** Google's large-scale dataset of audio events with human-annotated labels, sourced from YouTube videos.

**Specifications:**
| Attribute | Value |
|-----------|-------|
| **Segments** | 5.8 million (10-second clips) |
| **Video hours** | ~5,800 hours |
| **Classes** | 632 audio event classes |
| **Music classes** | ~80 classes (instrument-specific, genre) |
| **Format** | YouTube video IDs (audio extraction required) |
| **Annotation** | Weak labels (presence/absence per segment) |
| **Ontology** | Hierarchical AudioSet Ontology |

**Data Splits:**
- **Balanced Train:** 22,176 segments (unbalanced→balanced via sampling)
- **Unbalanced Train:** 2,063,825 segments
- **Evaluation:** 20,371 segments
- **Validation:** 20,383 segments

**Licensing:**
- **License:** YouTube Terms of Service; varies by content
- **Commercial Use:** Restricted by YouTube's policies
- **Research Use:** Generally permitted with attribution

**Access:** [research.google.com/audioset](https://research.google.com/audioset)

**Citation:** Gemmeke, J. F., Ellis, D. P., Freedman, D., Jansen, A., Lawrence, W., Moore, R. C., ... & Ritter, M. (2017). Audio Set: An ontology and human-labeled dataset for audio events. ICASSP 2017.

**Quality Assessment:** ⭐⭐⭐ (3/5) - Massive scale but noisy labels and variable audio quality

### 1.6 Additional Notable Datasets

#### Slakh2100 (Synthesized Lakh MIDI Dataset)
- **Description:** 2,100 multi-instrument MIDI files rendered with high-quality synthesizers
- **Audio:** FLAC, 44.1kHz, 16-bit
- **Use:** Multi-instrument separation, source separation training
- **License:** Creative Commons BY 4.0
- **Citation:** Manilow, E., Wichern, G., Seetharaman, P., & Le Roux, J. (2019). Cutting the Error by Half: Investigation of Very Deep CNN for Sound Event Detection. DCASE Workshop.

#### Lakh MIDI Dataset
- **Description:** 176,581 unique MIDI files matched to metadata
- **Size:** ~4.5 GB
- **Use:** Symbolic music generation, style transfer
- **License:** Variable (mostly permissive but check individual files)
- **Citation:** Raffel, C. (2016). Learning-based methods for comparing sequences, with applications to audio-to-MIDI alignment and matching. PhD Thesis, Columbia University.

#### NSynth Dataset
- **Description:** 305,979 musical notes from 1,006 instruments
- **Duration:** ~10-second samples per note
- **Format:** WAV (16kHz)
- **Use:** Instrument synthesis, timbre transfer
- **License:** Creative Commons BY 4.0
- **Citation:** Engel, J., Resnick, C., Roberts, A., Dieleman, S., Norouzi, M., Eck, D., & Simonyan, K. (2017). Neural Audio Synthesis of Musical Notes with WaveNet Autoencoders. ICML 2017.

---