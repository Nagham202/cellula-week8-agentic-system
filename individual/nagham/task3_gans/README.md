# Task 3: Generative Adversarial Networks (GANs)

An IEEE two-column research report on GANs based on four papers, analyzed in depth:

1. Goodfellow et al., "Generative Adversarial Nets" (NIPS 2014): the original GAN and its theory
2. Radford, Metz and Chintala, "Unsupervised Representation Learning with Deep Convolutional GANs" (ICLR 2016): DCGAN
3. Arjovsky, Chintala and Bottou, "Wasserstein GAN" (ICML 2017): WGAN
4. Karras, Laine and Aila, "A Style-Based Generator Architecture for GANs" (CVPR 2019): StyleGAN

Conditional GANs (Mirza and Osindero, 2014) and WGAN-GP (Gulrajani et al., 2017) are covered as extensions.

## Contents of the report

- Fundamental concepts: generator, discriminator, and how they compete (with a diagram)
- Full step-by-step derivations: minimax objective, optimal discriminator, reduction to the Jensen-Shannon
  divergence, global optimum, Nash equilibrium, and the gradients behind vanishing gradients and the
  non-saturating loss
- Training: the algorithm, forward and backward propagation, alternating optimization, convergence problems,
  mode collapse, vanishing gradients, instability, and evaluation (Inception Score, FID)
- Advanced architectures: DCGAN, cGAN, WGAN (Earth Mover distance, Kantorovich-Rubinstein duality),
  WGAN-GP (gradient penalty), StyleGAN (mapping network, AdaIN, with a diagram), and a comparison table
- Applications: image generation, super-resolution, image-to-image translation, data augmentation,
  medical imaging, and synthetic data

## Files

| File | What it is |
|---|---|
| `GANs_Report.pdf` | The final report |
| `main.tex` | LaTeX source (IEEEtran conference template, diagrams drawn with TikZ) |
| `references.bib` | BibTeX references, IEEE style |
