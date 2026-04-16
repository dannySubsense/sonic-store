# Adjacent Possible Hunting: Cross-Domain Connections for SonicStore

## ISMIR 2024 Insights

From browsing ISMIR 2024 proceedings and related materials, several themes emerged that connect to adjacent fields:

### Audio Source Separation & Robotics
- The CLaMP 3 (Contrastive Language-Music Pre-training) work shows how cross-modal pretraining techniques from vision-language models (like CLAP) can be adapted for music understanding
- This represents a direct transfer of vision-language pretraining strategies to the music domain
- The paper demonstrates how robotic audition systems could benefit from unified audio-language representations

### Jazz Audio Analysis & Computer Vision
- The ICLR 2025 paper on automated annotation of jazz piano trio recordings uses audio source separation techniques that have clear parallels to:
  - Object detection in computer vision (separating instruments = separating objects in a scene)
  - Semantic segmentation (assigning temporal labels to audio segments = pixel-level labeling)
  - Multi-object tracking (following instruments over time = tracking objects in video)

## arXiv cs.SD Recent Trends

### Deep Learning Transfers
- The tutorial on deep learning for MIR (arXiv:1709.04396) explicitly notes inspiration from CV and NLP
- Key transfers:
  - CNNs for spectrogram processing → directly adapted from image classification
  - RNNs/Transformers for sequential modeling → adapted from NLP language modeling
  - Contrastive learning → adapted from CV representation learning (SimCLR, MoCo)

### Language Modeling for Audio
- The Codified audio language modeling paper (arXiv:2107.05677) applies:
  - Tokenization techniques from NLP to audio
  - Language model pretraining strategies to audio sequences
  - This suggests music could benefit from the same scaling laws that transformed NLP

### Semi-Supervised Learning
- Scaling up MIR with semi-supervised learning (arXiv:2310.01353) shows:
  - Pseudo-labeling techniques from CV applied to audio
  - Consistency regularization adapted from vision
  - This approach could be particularly powerful for SonicStore's user-generated content

## AIMS 2026 Foresight

The "Crossroads" theme for ISMIR 2026 in Abu Dhabi suggests intentional focus on:
- Interdisciplinary methods
- Cultural fusion techniques
- This aligns perfectly with adjacent possible hunting - looking for techniques that work at the boundaries

## Unexpected Connections & Almost-Right Techniques

### From Robotics: SLAM for Music Structure
- Simultaneous Localization and Mapping (SLAM) algorithms could be adapted for:
  - Music structure analysis (localizing repeated sections, mapping musical form)
  - Real-time accompaniment systems (localizing position in a score while mapping to audio)
  - Almost-right: Current MIR uses HMMs and CRFs for structure, but SLAM offers probabilistic loop closure detection

### From NLP: Attention Mechanisms for Timbre
- Transformer attention could be applied to:
  - Timbre similarity (attending to salient spectral features)
  - Instrument identification (focusing on discriminative frequency bands)
  - Almost-right: Some work uses attention, but not systematically exploring different attention heads for different timbral aspects

### From CV: Uncertainty Estimation in Music Transcription
- Techniques like Monte Carlo Dropout or Deep Ensembles from CV could provide:
  - Confidence estimates for onset detection
  - Uncertainty-aware chord recognition
  - Almost-right: Some probabilistic models exist, but not leveraging modern CV uncertainty quantification

### From Graphics: Neural Rendering for Audio Synthesis
- Neural radiance fields (NeRF) concepts could inspire:
  - Continuous audio representation learning
  - View synthesis analog → "position synthesis" in audio space
  - Almost-right: Neural audio synthesis exists, but not explicitly borrowing rendering frameworks

### From Reinforcement Learning: Reward Shaping for Playlist Generation
- Inverse reinforcement learning from robotics could:
  - Learn user preferences from listening behavior
  - Shape rewards for diverse yet coherent playlists
  - Almost-right: Some RL for playlists, but not using advanced IRL techniques from robotics

## Recommendations for SonicStore

1. **Create a cross-domain technique tracker** - systematically review CV/NLP/robotics papers for adaptable methods
2. **Build prototyping pipelines** - quick implementation of promising adjacent techniques
3. **Focus on uncertainty-aware MIR** - borrowing from CV safety-critical applications
4. **Explore SLAM-inspired structure analysis** - novel approach to musical form
5. **Develop cross-modal pretraining benchmarks** - evaluate how well vision-language pretraining transfers to music tasks

The most promising adjacent possibilities appear to be:
- Uncertainty quantification methods from computer vision applied to onset/chord detection
- SLAM-like algorithms for robust music structure analysis under noise
- Cross-modal pretraining strategies that leverage large-scale vision-language corpora for music understanding