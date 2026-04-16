# GitHub MIR & Music AI Discovery Report

**Research Date:** April 9, 2026  
**Scope:** Music Information Retrieval, Audio DSP, and Music Generation Implementations  
**Output:** Comprehensive analysis of production-ready vs research-only repositories

---

## Executive Summary

This report documents a comprehensive survey of GitHub repositories spanning Music Information Retrieval (MIR), Audio DSP, and Music Generation. The landscape shows a clear divide between mature, production-ready libraries (librosa, Essentia, Spleeter) and cutting-edge research implementations that often lack maintenance (OpenAI Jukebox, Magenta). Meta/Facebook and Spotify have emerged as major corporate contributors, while academic institutions (UPF Barcelona, JKU Linz) maintain critical foundational tools.

**Key Finding:** The most valuable repositories for production use combine: (1) active maintenance within the last 6 months, (2) comprehensive documentation, (3) Python bindings for accessibility, and (4) pretrained models available out-of-the-box.

---

## 1. Core MIR Libraries

### 1.1 Librosa ⭐⭐⭐⭐⭐ (ESSENTIAL)

| Attribute | Details |
|-----------|---------|
| **Repository** | [librosa/librosa](https://github.com/librosa/librosa) |
| **Stars** | ~7,000+ (industry standard) |
| **License** | ISC License |
| **Maintenance** | ✅ ACTIVE - Regular releases, CI/CD |
| **Python** | 3.7+ supported |

**Key Features:**
- De facto standard for music analysis in Python
- Comprehensive feature extraction: MFCCs, chromagrams, spectrograms, tempograms
- Beat tracking, onset detection, pitch estimation
- Display and visualization tools
- Seamless NumPy/SciPy integration

**What Makes It Valuable:**
Librosa is the "NumPy of audio" - every MIR pipeline starts here. The API is stable, well-documented, and has a massive community. The library abstracts away the complexity of audio processing while maintaining flexibility for researchers.

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- Extensive test coverage via codecov
- Automated CI/CD workflows
- Published in SciPy proceedings (academic credibility)
- Used by Spotify, Pandora, and countless research labs

**Code Quality Indicators:**
- Comprehensive documentation at librosa.org
- Example gallery with advanced use cases
- Type hints throughout
- Zenodo DOI for citation

---

### 1.2 Essentia ⭐⭐⭐⭐⭐ (ESSENTIAL)

| Attribute | Details |
|-----------|---------|
| **Repository** | [MTG/essentia](https://github.com/MTG/essentia) |
| **Organization** | Music Technology Group, UPF Barcelona |
| **License** | AGPLv3 |
| **Maintenance** | ✅ ACTIVE - Master branch regularly updated |
| **Platforms** | Linux, macOS, Windows, iOS, Android |

**Key Features:**
- C++ core with Python bindings for performance
- 200+ audio analysis algorithms
- Vamp plugin for Sonic Visualiser
- TensorFlow integration (essentia-tensorflow)
- Prebuilt command-line extractors
- Docker images available

**What Makes It Valuable:**
Essentia bridges the gap between research and production. The C++ core provides computational efficiency while Python bindings enable rapid prototyping. The MTG group is a respected academic institution ensuring algorithmic rigor.

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- Cross-platform support including mobile
- Docker containers for deployment
- Vamp plugin ecosystem integration
- Used in commercial applications (BMAT, AcousticBrainz)

**Academic Credibility:**
- Published research backing algorithms
- Extensive documentation and tutorials
- Jupyter notebook tutorials included

---

### 1.3 Madmom ⭐⭐⭐⭐ (HIGHLY RECOMMENDED)

| Attribute | Details |
|-----------|---------|
| **Repository** | [CPJKU/madmom](https://github.com/CPJKU/madmom) |
| **Organization** | Johannes Kepler University / OFAI Vienna |
| **License** | BSD (code), CC BY-NC-SA 4.0 (models) |
| **Maintenance** | ⚠️ MODERATE - Academic project |
| **Python** | 2.7, 3.5+ |

**Key Features:**
- Reference implementations of state-of-the-art MIR algorithms
- Beat tracking, onset detection, key detection
- Deep learning models (RNNs) for beat tracking
- Real-time audio processing capabilities
- MIREX-winning algorithms included

**What Makes It Valuable:**
Madmom provides reference implementations of algorithms that won MIREX competitions. If you need the absolute best beat tracker or onset detector, this is where to look. The code quality is academic-grade.

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- PyPI installation available
- Pre-trained models included
- Command-line tools provided
- ⚠️ Models are non-commercial license

**Limitations:**
- Non-commercial restriction on models limits commercial use
- Academic maintenance pace
- Python 2.7 legacy support adds complexity

---

### 1.4 mir_eval ⭐⭐⭐⭐ (ESSENTIAL FOR RESEARCH)

| Attribute | Details |
|-----------|---------|
| **Repository** | [mir-evaluation/mir_eval](https://github.com/mir-evaluation/mir_eval) |
| **License** | MIT |
| **Maintenance** | ✅ STABLE - Reference implementation |
| **Last Release** | February 2022 |

**Key Features:**
- Standardized evaluation metrics for MIR tasks
- Beat detection, chord estimation, melody extraction, onset detection
- Structure analysis, tempo estimation evaluation
- Used in MIREX evaluations

**What Makes It Valuable:**
This is the reference implementation for MIR evaluation. If you're publishing research or comparing algorithms, you must use mir_eval metrics. The library ensures your results are comparable to the literature.

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- Stable API (mature project)
- Well-documented metrics
- Used by MIREX (Music Information Retrieval Evaluation eXchange)

---

## 2. Music Generation Models

### 2.1 AudioCraft / MusicGen ⭐⭐⭐⭐⭐ (PRODUCTION-READY)

| Attribute | Details |
|-----------|---------|
| **Repository** | [facebookresearch/audiocraft](https://github.com/facebookresearch/audiocraft) |
| **Organization** | Meta/Facebook AI Research |
| **License** | MIT |
| **Maintenance** | ✅ VERY ACTIVE - Continuous updates |
| **Python** | 3.9+, PyTorch 2.1.0 |

**Key Features:**
- **MusicGen:** Text-to-music generation with melody conditioning
- **AudioGen:** Text-to-sound effects
- **EnCodec:** State-of-the-art neural audio codec
- **MAGNeT:** Non-autoregressive music generation
- **AudioSeal:** Audio watermarking
- **JASCO:** Chord/melody/drum conditioned generation
- Training code provided for all models

**What Makes It Valuable:**
AudioCraft is the most comprehensive open-source audio generation framework. Unlike research-only releases, this includes full training pipelines, not just inference. The EnCodec codec is particularly valuable for any audio ML pipeline.

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- Full training code (not just inference)
- HuggingFace integration
- API documentation
- Active community support
- Used in production at Meta

**Models Available:**
- musicgen-small, musicgen-medium, musicgen-large, musicgen-melody
- audiogen-medium
- encodec-32khz

**Code Quality:**
- Comprehensive documentation
- Type hints
- CI/CD with tests and linting
- Example notebooks

---

### 2.2 Stable Audio Tools ⭐⭐⭐⭐ (PROMISING)

| Attribute | Details |
|-----------|---------|
| **Repository** | [Stability-AI/stable-audio-tools](https://github.com/Stability-AI/stable-audio-tools) |
| **Organization** | Stability AI |
| **License** | Not specified (check repo) |
| **Maintenance** | ⚠️ UNCERTAIN - Stability AI instability |

**Key Features:**
- Diffusion-transformer architecture
- 44.1kHz stereo sound effects generation
- Long-form music generation with coherent structure
- Latent rate of 21.5 Hz (highly downsampled)

**What Makes It Valuable:**
The first open-source model capable of generating full-length, coherent music tracks at professional audio quality (44.1kHz stereo). The architecture is innovative - diffusion-transformer on continuous latents.

**Production Readiness:** ⭐⭐⭐ MODERATE
- High-quality generation
- ⚠️ Company instability concerns
- Community fork available: [friendly-stable-audio-tools](https://github.com/yukara-ikemiya/friendly-stable-audio-tools)

**Recommendation:** Monitor the community fork for long-term viability.

---

### 2.3 AudioLDM / AudioLDM-2 ⭐⭐⭐⭐ (RESEARCH-TO-PRODUCTION)

| Attribute | Details |
|-----------|---------|
| **Repository** | [haoheliu/AudioLDM](https://github.com/haoheliu/AudioLDM) / [AudioLDM2](https://github.com/haoheliu/AudioLDM2) |
| **License** | Check repository |
| **Maintenance** | ✅ ACTIVE - Regular checkpoint updates |

**Key Features:**
- Text-to-audio generation
- Audio-to-audio generation (same event, different sound)
- Text-guided audio style transfer
- Multiple model sizes (S, M, L)
- Fine-tuned versions on AudioCaps/MusicCaps

**What Makes It Valuable:**
AudioLDM was one of the first high-quality text-to-audio models. The ability to do style transfer and audio-to-audio generation enables creative applications beyond simple text prompting.

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- HuggingFace Diffusers integration
- Gradio web app included
- Multiple checkpoints for different use cases
- Command-line interface

---

### 2.4 OpenAI Jukebox ⭐⭐ (RESEARCH LEGACY)

| Attribute | Details |
|-----------|---------|
| **Repository** | [openai/jukebox](https://github.com/openai/jukebox) |
| **Status** | ⚠️ ARCHIVED - No updates expected |
| **License** | Check repository |

**Key Features:**
- Raw audio generation at 44.1kHz
- Lyrics-conditioned generation
- Artist/style conditioning
- VQ-VAE + Transformer architecture

**What Makes It Valuable:**
Historically significant - first large-scale music generation model with vocals. The paper introduced important techniques for long-form audio generation.

**Production Readiness:** ⭐⭐ POOR
- ⚠️ ARCHIVED - No maintenance
- Requires V100 GPU minimum (11.5GB for 5B model)
- 3 hours to generate 20 seconds of audio
- Python 3.7.5, PyTorch 1.4 (very outdated)

**Verdict:** Study for historical context, but use AudioCraft for production.

---

### 2.5 Magenta ⭐⭐ (TRANSITIONED)

| Attribute | Details |
|-----------|---------|
| **Repository** | [magenta/magenta](https://github.com/magenta/magenta) |
| **Organization** | Google Brain (now Google Research) |
| **Status** | ⚠️ ARCHIVED - Read only |
| **License** | Apache 2.0 |

**Key Features:**
- MusicVAE: Latent space music generation
- MelodyRNN, DrumsRNN: Sequential models
- NSynth: Neural audio synthesis
- DDSP: Differentiable Digital Signal Processing
- Magenta.js: Browser-based models

**What Makes It Valuable:**
Pioneering work in ML for music. MusicVAE and NSynth introduced important concepts. The project has transitioned to individual repositories.

**Production Readiness:** ⭐⭐ POOR
- ⚠️ Main repo archived
- See [Magenta GitHub Organization](https://github.com/magenta) for active projects
- DDSP still maintained separately

**Current Status:**
- Individual models moved to separate repos
- Magenta.js still active for browser use
- DDSP maintained at [magenta/ddsp](https://github.com/magenta/ddsp)

---

### 2.6 Riffusion ⭐⭐⭐ (EXPERIMENTAL)

| Attribute | Details |
|-----------|---------|
| **Repository** | [riffusion/riffusion-hobby](https://github.com/riffusion/riffusion-hobby) |
| **Concept** | Stable Diffusion for spectrograms |
| **Maintenance** | ⚠️ HOBBY PROJECT |

**Key Features:**
- Real-time music generation via spectrogram diffusion
- Interpolation between styles
- Web app for interactive generation

**What Makes It Valuable:**
Innovative approach using image diffusion on spectrograms. Good for experimental/artistic applications.

**Production Readiness:** ⭐⭐⭐ MODERATE
- Real-time capable
- ⚠️ Quality limitations of spectrogram approach
- Hobby project maintenance level

---

## 3. Audio Feature Extraction & Analysis Tools

### 3.1 PyAudioAnalysis ⭐⭐⭐ (SOLID)

| Attribute | Details |
|-----------|---------|
| **Repository** | [tyiannak/pyAudioAnalysis](https://github.com/tyiannak/pyAudioAnalysis) |
| **License** | Apache 2.0 |
| **Maintenance** | ✅ ACTIVE |

**Key Features:**
- Feature extraction (MFCCs, spectrogram, chromagram)
- Audio classification and segmentation
- Speaker diarization
- Visualization tools
- Command-line interface

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- Well-documented
- Multiple use case examples
- Good for prototyping

---

### 3.2 Spotify Basic Pitch ⭐⭐⭐⭐ (SPECIALIZED)

| Attribute | Details |
|-----------|---------|
| **Repository** | [spotify/basic-pitch](https://github.com/spotify/basic-pitch) |
| **Organization** | Spotify |
| **License** | Check repository |
| **Maintenance** | ✅ ACTIVE |

**Key Features:**
- Audio-to-MIDI conversion
- Pitch bend detection
- Lightweight neural network
- TypeScript version available (basic-pitch-ts)

**What Makes It Valuable:**
Best-in-class audio-to-MIDI conversion. The pitch bend detection is particularly valuable for realistic instrument transcription.

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- Used in Spotify products
- Fast inference
- Easy-to-use API

---

## 4. Audio DSP & Effects

### 4.1 Pedalboard ⭐⭐⭐⭐⭐ (PRODUCTION-READY)

| Attribute | Details |
|-----------|---------|
| **Repository** | [spotify/pedalboard](https://github.com/spotify/pedalboard) |
| **Organization** | Spotify Audio Intelligence Lab |
| **License** | Check repository |
| **Maintenance** | ✅ VERY ACTIVE |
| **Python** | 3.10, 3.11, 3.12, 3.13, 3.14 |

**Key Features:**
- Audio I/O: AIFF, FLAC, MP3, OGG, WAV (no dependencies)
- Built-in effects: Reverb, Delay, Compressor, EQ, Distortion, Chorus, Phaser
- VST3® plugin support (Linux, macOS, Windows)
- Audio Unit support (macOS)
- Live audio streaming via AudioStream
- TensorFlow integration (tf.data compatible)

**What Makes It Valuable:**
The only Python library that can load and use professional VST3 plugins programmatically. Used in production for Spotify's AI DJ and AI Voice Translation features.

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- Used heavily in production at Spotify
- Thread-safe, memory-efficient
- 300x faster than pySoX for single transforms
- 4x faster than librosa for file reading
- Platform wheels for easy installation

**Performance Claims:**
- Releases Python GIL for multicore processing
- O(1) memory usage for resampling
- Tested compatibility with TensorFlow

---

### 4.2 DDSP (Differentiable Digital Signal Processing) ⭐⭐⭐⭐ (RESEARCH)

| Attribute | Details |
|-----------|---------|
| **Repository** | [magenta/ddsp](https://github.com/magenta/ddsp) |
| **Organization** | Google Magenta |
| **License** | Apache 2.0 |
| **Maintenance** | ✅ ACTIVE |

**Key Features:**
- Combines classical DSP with neural networks
- Sinusoidal modeling, filtered noise synthesis
- Differentiable audio effects
- Training pipelines for timbre transfer

**What Makes It Valuable:**
Enables neural networks to learn interpretable audio representations. The timbre transfer capabilities are impressive - make a flute sound like a violin while preserving pitch and dynamics.

**Production Readiness:** ⭐⭐⭐ MODERATE
- Research-oriented API
- Requires training for new instruments
- Powerful but complex

---

## 5. Source Separation

### 5.1 Spleeter ⭐⭐⭐⭐⭐ (INDUSTRY STANDARD)

| Attribute | Details |
|-----------|---------|
| **Repository** | [deezer/spleeter](https://github.com/deezer/spleeter) |
| **Organization** | Deezer Research |
| **License** | MIT |
| **Maintenance** | ✅ ACTIVE |

**Key Features:**
- 2 stems (vocals/accompaniment)
- 4 stems (vocals/drums/bass/other)
- 5 stems (adds piano)
- 100x faster than real-time on GPU
- Pre-trained models included
- Command-line and Python API

**What Makes It Valuable:**
The most widely used open-source source separation tool. Integrated into professional software (iZotope RX, SpectralLayers, VirtualDJ, Algoriddim djay).

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- Used in commercial products
- Docker support
- Google Colab notebook
- Spleeter Pro available for enterprise

**Commercial Adoption:**
- iZotope RX 8 (Music Rebalance)
- Steinberg SpectralLayers 7
- Acon Digital Acoustica 7
- VirtualDJ (stem isolation)
- Algoriddim NeuralMix

---

### 5.2 Demucs ⭐⭐⭐⭐⭐ (STATE-OF-THE-ART)

| Attribute | Details |
|-----------|---------|
| **Repository** | [facebookresearch/demucs](https://github.com/facebookresearch/demucs) |
| **Fork** | [adefossez/demucs](https://github.com/adefossez/demucs) (new official) |
| **Organization** | Meta/Facebook AI (now community) |
| **License** | MIT |
| **Maintenance** | ⚠️ TRANSITIONING - See fork |

**Key Features:**
- Hybrid Transformer architecture (v4)
- 9.00 dB SDR on MUSDB HQ (state-of-the-art)
- 6 sources model (adds guitar and piano)
- Sparse attention for extended receptive field
- Real-time capable (via Neutone plugin)

**What Makes It Valuable:**
Currently the best quality source separation available open-source. The Hybrid Transformer approach outperforms all competitors on standard benchmarks.

**Production Readiness:** ⭐⭐⭐⭐⭐ EXCELLENT
- PyPI package
- VST/AU plugin via Neutone
- Used in professional workflows
- MVSep integration

**⚠️ Important Note:**
Original author left Meta. Development continues at adefossez/demucs with important bug fixes only.

---

## 6. DAW Integration & Production Tools

### 6.1 Ableton Live Remote Scripts

| Attribute | Details |
|-----------|---------|
| **Repository** | [gluon/AbletonLive10.1_MIDIRemoteScripts](https://github.com/gluon/AbletonLive10.1_MIDIRemoteScripts) |
| **Type** | Decompiled reference |
| **License** | Unofficial |

**Key Features:**
- Decompiled Ableton Live MIDI remote scripts
- Reference for building custom controllers
- Python-based control surface API

**Production Readiness:** ⭐⭐⭐ MODERATE
- Unofficial/decompiled
- Useful for learning the API
- See also: [j74/Generic-Python-Remote-Script](https://github.com/j74/Generic-Python-Remote-Script)

---

### 6.2 Spleeter4Max

| Attribute | Details |
|-----------|---------|
| **Repository** | [diracdeltas/spleeter4max](https://github.com/diracdeltas/spleeter4max) |
| **Type** | Ableton Live integration |

**Key Features:**
- Spleeter integration for Ableton Live
- Max for Live device
- Real-time stem separation

---

## 7. Real-World Music AI Applications

### 7.1 Wav2Lip ⭐⭐⭐⭐ (SPECIALIZED)

| Attribute | Details |
|-----------|---------|
| **Repository** | [Rudrabha/Wav2Lip](https://github.com/Rudrabha/Wav2Lip) |
| **Paper** | ACM Multimedia 2020 |
| **License** | Check repository |

**Key Features:**
- Lip-sync video to audio
- Works "in the wild" (any face, any voice)
- HD variants available (Wav2Lip-HD)
- Real-time variants exist

**Production Readiness:** ⭐⭐⭐⭐ GOOD
- Pre-trained models available
- Multiple community forks with improvements
- Commercial version: Sync Labs

---

## 8. Patterns & Analysis

### 8.1 Production-Ready vs Research-Only

| Production-Ready | Research-Only/Archived |
|------------------|------------------------|
| Librosa | OpenAI Jukebox (archived) |
| Essentia | Magenta main repo (archived) |
| AudioCraft | Riffusion (hobby) |
| Pedalboard | Many academic repos |
| Spleeter | |
| Demucs | |
| Basic Pitch | |

### 8.2 Maintenance Status Summary

| Repository | Status | Recommendation |
|------------|--------|----------------|
| librosa | ✅ Active | Use for all MIR |
| essentia | ✅ Active | Use for performance-critical apps |
| audiocraft | ✅ Active | Use for music generation |
| pedalboard | ✅ Active | Use for audio effects |
| spleeter | ✅ Active | Use for source separation |
| demucs | ⚠️ Transitioning | Use adefossez fork |
| madmom | ⚠️ Academic | Check license for commercial use |
| magenta | ❌ Archived | Use individual model repos |
| jukebox | ❌ Archived | Study only |

### 8.3 Corporate vs Academic

**Corporate (better maintenance, production focus):**
- Meta: AudioCraft, Demucs
- Spotify: Pedalboard, Basic Pitch
- Deezer: Spleeter
- Google: Magenta (transitioned)

**Academic (cutting-edge algorithms, less maintenance):**
- UPF Barcelona: Essentia
- JKU Linz: Madmom
- Various universities: mir_eval

### 8.4 Code Quality Indicators

**Excellent (CI/CD, docs, type hints):**
- librosa, audiocraft, pedalboard, spleeter

**Good (documented, stable):**
- essentia, demucs, basic-pitch

**Moderate (functional, less polish):**
- madmom, pyaudioanalysis

**Legacy (archived/outdated):**
- jukebox, magenta main repo

---

## 9. Recommendations by Use Case

### For MIR Research
1. **librosa** - Foundation for all analysis
2. **mir_eval** - Standardized evaluation
3. **madmom** - State-of-the-art algorithms (check license)
4. **essentia** - Performance and additional descriptors

### For Music Production/DAW Integration
1. **pedalboard** - Audio effects and VST support
2. **basic-pitch** - Audio-to-MIDI
3. **spleeter** / **demucs** - Stem separation
4. **spleeter4max** - Ableton integration

### For Music Generation
1. **audiocraft** - Most comprehensive, production-ready
2. **stable-audio-tools** - Full-length music (monitor fork)
3. **audioldm** - Sound effects and style transfer
4. **ddsp** - Timbre transfer and synthesis

### For Source Separation
1. **demucs** - Best quality (use adefossez fork)
2. **spleeter** - Fastest, most widely adopted

### For Audio DSP Education
1. **ddsp** - Learn differentiable DSP
2. **librosa** - Learn feature extraction
3. **pedalboard** - Learn effects processing

---

## 10. Community & Collaboration Patterns

### Active Communities
- **librosa**: Google Groups forum, GitHub discussions
- **audiocraft**: GitHub issues, active PR review
- **pedalboard**: Spotify engineering blog, active development

### Academic Collaboration
- **essentia**: MTG UPF, used in AcousticBrainz
- **madmom**: JKU/OFAI, MIREX participation
- **mir_eval**: MIREX standardization

### Commercial Adoption
- **spleeter**: Integrated into 5+ commercial products
- **pedalboard**: Powers Spotify AI features
- **demucs**: Used in professional audio workflows

---

## 11. Links & Resources

### Essential Documentation
- Librosa: https://librosa.org/doc/
- Essentia: https://essentia.upf.edu/
- AudioCraft: https://facebookresearch.github.io/audiocraft/
- Pedalboard: https://spotify.github.io/pedalboard/

### Model Hubs
- HuggingFace Audio: https://huggingface.co/models?pipeline_tag=audio-to-audio
- AudioCraft Models: Available via HuggingFace
- Stable Audio: Check Stability AI resources

### Datasets
- MUSDB: https://sigsep.github.io/datasets/musdb.html
- AudioCaps: Text-audio pairs
- MusicCaps: Text-music pairs

---

## 12. Conclusion

The Music Information Retrieval and AI-generated music landscape has matured significantly. For production use:

**Start with:** librosa + audiocraft + pedalboard

**Add for specific needs:**
- Source separation: demucs (adefossez fork) or spleeter
- Audio-to-MIDI: basic-pitch
- Advanced analysis: essentia
- Evaluation: mir_eval

**Avoid for production:**
- OpenAI Jukebox (archived, slow)
- Magenta main repo (archived)
- Any repo without updates in 2+ years

The field is consolidating around a few well-maintained corporate-backed tools (Meta's AudioCraft, Spotify's Pedalboard, Deezer's Spleeter) while academic tools (librosa, essentia, mir_eval) remain essential for research credibility.

---

*Report compiled: April 9, 2026*  
*For updates, check individual repository GitHub pages*
