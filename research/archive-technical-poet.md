# Archive: Technical Poet Findings
## Exploring ISMIR, arXiv cs.SD, and AIMS 2026

### Beautiful Solutions That Feel Inevitable

**PESTO: Pitch Estimation with Self-supervised Transposition-equivariant Objective** (ISMIR 2023 Best Paper)
- **Beauty**: Uses equivariance to pitch transposition as a self-supervised objective
- **Inevitability**: The insight that pitch estimation should be equivariant to transposition is mathematically elegant - if you shift the input pitch, the output should shift correspondingly. This mirrors how humans perceive pitch relationships.
- **Technical Elegance**: Combines VQT (Variable-Q Transform) with a Siamese architecture and Toeplitz fully-connected layer to naturally preserve transposition properties. Achieves SOTA performance with minimal labeled data.

**Combining audio control and style transfer using latent diffusion** (arXiv:2408.00196, ISMIR 2024)
- **Beauty**: Separates local (structure/rhythm) and global (timbre) information in latent space
- **Inevitability**: Artists naturally think about music in terms of "what notes are played" vs "what instrument/sound". This decomposition aligns with intuitive musical understanding.
- **Technical Elegance**: Uses diffusion autoencoders with adversarial disentanglement and two-stage training. Enables cover version generation by transferring rhythmic/melodic content to different genre styles.

### Inelegant Hacks That Reveal Deeper Truths

**Audio Prompt Adapter: Unleashing Music Editing Abilities for Text-to-Music with Lightweight Finetuning**
- **Hack**: Lightweight finetuning approach for text-to-music models
- **Deeper Truth**: Reveals that large music generation models contain rich internal representations that can be accessed with minimal adaptation - the model already "knows" music editing concepts, we just need to point to them.
- **Aesthetic Quality**: Suggests that musical understanding in LLMs is more about accessing latent knowledge than learning new capabilities.

**DEEP RECOMBINANT TRANSFORMER: ENHANCING LOOP COMPATIBILITY IN DIGITAL MUSIC PRODUCTION**
- **Hack**: Uses transformer architecture to model loop compatibility in digital music production
- **Deeper Truth**: Reveals that musical loops have learnable compatibility patterns that transcend simple BPM/key matching - there's a deeper structural harmony that makes certain loops work well together.
- **Aesthetic Quality**: Connects abstract ML concepts to the very concrete, visceral experience of a DJ or producer selecting complementary loops.

### Papers Where Technique Has Aesthetic Qualities

**GraphMuse: A Library for Symbolic Music Graph Processing**
- **Technique**: Graph-based representation of symbolic music
- **Aesthetic Quality**: Music naturally lends itself to graph representation (notes as nodes, temporal/harmonic relationships as edges). The technique feels discovered rather than invented - it unveils the inherent graph structure already present in musical theory.

**Formal Modeling of Structural Repetition using Tree Compression**
- **Technique**: Applies tree compression algorithms to model musical structure
- **Aesthetic Quality**: Reveals that musical repetition has a compressible, hierarchical structure - the beauty of musical form lies in its efficient encoding. Techniques like ZIP compression accidentally capture musical aesthetics.

**Human Pose Estimation for Expressive Movement Descriptors in Vocal Musical Performance**
- **Technique**: Computer vision for analyzing singer's body movements
- **Aesthetic Quality**: Connects the invisible (vocal expression) to the visible (body movement), revealing that musical expression is fundamentally embodied. The technique makes tangible the intangible quality of vocal expressiveness.

### What the Aesthetics of MIR Suggest About SonicStore's Soul

The patterns I observe suggest SonicStore should embody:

1. **Equivariance as Core Principle**: Like PESTO, SonicStore's features should exhibit natural symmetries - shifting inputs should produce predictably shifted outputs. This creates intuitive, mathematically honest interactions.

2. **Disentangled Representations**: Separate concerns like the latent diffusion model - isolate timbre (sound quality) from structure (rhythm/melody) so users can manipulate each independently. This mirrors how musicians actually think about music.

3. **Lightweight Adaptation Over Retraining**: Like the Audio Prompt Adapter, SonicStore should reveal that powerful capabilities already exist within foundation models - our job is to provide the right "prompts" or interfaces to access them, not to rebuild from scratch.

4. **Embodied Interaction**: Take inspiration from human pose estimation - musical expression is physical. SonicStore should consider how gestures, movement, and physical interaction contribute to the musical experience, not just abstract parameters.

5. **Discover, Don't Invent**: The most beautiful MIR techniques feel like discoveries of underlying musical structure (graph representations, tree compression). SonicStore should aim to unveil inherent patterns in sound rather than imposing artificial frameworks.

6. **Loop Compatibility as Musical Harmony**: The Deep Recombinant Transformer reveals that aesthetic judgments (what loops "go well together") can be learned. SonicStore should develop similar intuition for what sonic elements complement each other.

The soul of SonicStore lies in creating tools that feel less like software and more like natural extensions of musical intuition - where the technology recedes and the musician's direct connection to sound emerges.