Example of a spec-conformant OKF concept document (§4):

File path in bundle: `chapters/neural-networks.md`

```markdown
---
type: Textbook Chapter
title: Neural Networks
description: Overview of neural network architecture and training process.
tags:
  - machine-learning
  - neural-networks
  - deep-learning
timestamp: 2026-07-04T00:00:00Z
source:
  document: DeepLearning.pdf
  pages: "25-48"
---

# Neural Networks

A neural network is a computational model composed of interconnected nodes
(neurons). Each neuron receives input, performs a mathematical operation,
and passes the result to the next layer.

## Main Components

### Input Layer

Receives raw data such as images, text, or numerical values.

### Hidden Layers

Perform feature extraction and pattern learning.

### Output Layer

Produces the final prediction or classification.

## Training Process

1. Feed the input data.
2. Calculate the prediction.
3. Measure the error using a loss function.
4. Update the weights through backpropagation.
5. Repeat until the model converges.

## Key Terms

| Term | Description |
|------|-------------|
| Neuron | Basic computational unit |
| Weight | Strength of a connection |
| Bias | Additional learnable parameter |
| Epoch | One complete pass through the dataset |
| Loss Function | Measures prediction error |

## Related Concepts

- prerequisite: [Machine Learning](/chapters/machine-learning.md)
- child: [Backpropagation](/chapters/backpropagation.md)
- related: [Deep Learning](/chapters/deep-learning.md)

# Citations

[1] [DeepLearning.pdf, Chapter 2, Pages 25-48](DeepLearning.pdf)
```

Example of a root `index.md` (§6 — no frontmatter):

```markdown
# Deep Learning Knowledge Base

## Chapters

* [Neural Networks](chapters/neural-networks.md) - Overview of neural network architecture and training process.
* [Backpropagation](chapters/backpropagation.md) - Algorithm for training neural networks via gradient descent.
* [Deep Learning](chapters/deep-learning.md) - Multi-layer neural network architectures and applications.

## Appendices

* [Glossary](appendices/glossary.md) - Key terms and definitions used throughout the textbook.
```
