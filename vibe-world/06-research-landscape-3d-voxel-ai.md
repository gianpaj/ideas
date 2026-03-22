# Research Landscape — 3D and Voxel AI Models

_Last updated: 2026-03-22_

## Executive summary

The current 3D AI landscape is strong for **high-fidelity asset generation**, but still weaker for **fast, constrained, multiplayer-safe chunky voxel drafting**.

The most important takeaway for this project is:

> Do not depend on one end-to-end “text to perfect voxel object” model as the core mechanic.

A better near-term approach is:

> use AI to generate structured object operations inside a world-native voxel grammar.

## Categories that matter

### 1. Large 3D asset generation models

These models are impressive and relevant, but they are usually optimized for generating polished assets rather than playful block-world objects.

#### TRELLIS

Microsoft’s TRELLIS is a large 3D asset generation system that takes text or image prompts and can generate 3D assets in multiple output formats, including radiance fields, 3D Gaussians, and meshes.

Repository:
- https://github.com/microsoft/TRELLIS

Key relevance:
- shows the state of open 3D generation,
- emphasizes structured latent representations,
- useful reference for controllable 3D generation pipelines.

Main limitation for this project:
- oriented more toward high-quality asset generation than instantly editable chunky public-world objects.

#### TRELLIS.2

TRELLIS.2 extends this direction using a sparse voxel-based representation called **O-Voxel** and targets high-fidelity image-to-3D generation with textured meshes and PBR materials.

Resources:
- https://github.com/microsoft/TRELLIS.2
- https://microsoft.github.io/TRELLIS.2/

Key relevance:
- strong evidence that sparse voxel representations are becoming serious 3D latent structures,
- interesting for internal representation design,
- useful inspiration for structured 3D compression and conversion.

Main limitation for this project:
- still focused on producing high-quality assets, not necessarily low-latency social-world object drafting.

#### Hunyuan3D-2 / 2.1

Tencent’s Hunyuan3D line focuses on open 3D asset creation. Hunyuan3D-2 uses a two-stage pipeline that first generates a mesh and then textures it. Hunyuan3D-2.1 emphasizes a fully open-source framework and PBR texture synthesis.

Resources:
- https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- https://github.com/tencent-hunyuan/hunyuan3d-2.1

Key relevance:
- practical reference for open 3D asset pipelines,
- strong benchmark for what “current open asset generation” looks like,
- useful for studying prompt-to-asset workflows.

Main limitation for this project:
- again, the target is polished asset creation more than chunky multiplayer-safe voxel objects.

## 2. Part-aware and modular 3D generation

This category is especially relevant.

The project needs objects that are:

- editable,
- interpretable,
- structurally decomposable,
- safe to remix,
- suitable for UGC.

That makes part-aware and modular methods more relevant than purely monolithic 3D generators.

#### OmniPart

OmniPart focuses on part-aware 3D generation with explicit editable part structure and strong structural cohesion.

Resources:
- https://arxiv.org/abs/2507.06165
- https://omnipart.github.io/

Why it matters:
- directly addresses the problem of monolithic 3D generation,
- points toward controllable object decomposition,
- aligns with interactive editing and remixing better than monolithic outputs.

#### AssetFormer

AssetFormer targets modular 3D asset generation with an autoregressive Transformer, explicitly framed around modular assets and UGC scenarios.

Resources:
- https://arxiv.org/abs/2602.12100
- https://openreview.net/forum?id=ODB82HDp0V

Why it matters:
- modular generation is much closer to a game-friendly object grammar,
- especially relevant if the project shifts toward structured object parts and constrained assembly.

## 3. Voxel-art stylization and abstraction

This is also relevant, especially for the chosen chunky visual style.

#### Voxify3D

Voxify3D is a 2025 framework focused on generating stylized voxel art from 3D meshes while preserving semantic structure and discrete color coherence.

Resources:
- https://arxiv.org/abs/2512.07834
- https://yichuanh.github.io/Voxify-3D/

Why it matters:
- directly relevant to voxel-art aesthetics,
- useful for understanding abstraction and palette control,
- could become relevant if the pipeline ever includes mesh-to-voxel conversion or stylized import workflows.

Main limitation:
- this is more about stylized voxelization from meshes than prompt-native multiplayer object generation.

## 4. Consistency in AI-generated games

This is highly relevant to the overall game concept, even if not specific to voxel object generation.

#### MaaG (Model as a Game)

Microsoft’s MaaG framework focuses on consistency in AI-generated games, especially numerical and spatial consistency. One key idea is separating stable game memory/logic from purely visual generation.

Resources:
- https://www.microsoft.com/en-us/research/articles/maag-a-new-framework-for-consistent-ai-generated-games/
- https://www.microsoft.com/en-us/research/publication/model-as-a-game-on-numerical-and-spatial-consistency-for-generative-games/

Why it matters:
- validates the need for decoupled authoritative world state,
- strongly supports the idea that multiplayer worlds need stable memory and rules independent of generative rendering,
- conceptually aligned with this project’s authoritative state model.

## 5. Voxel engine substrate

#### Cubiquity

Cubiquity is an experimental micro-voxel engine written in C++ and released into the public domain.

Resource:
- https://github.com/DavidWilliams81/cubiquity

Why it matters:
- relevant if the project needs a voxel-native substrate for editable world matter,
- aligns well with terrain, destructible environment, and chunk-based world logic.

Main caveat:
- the project explicitly describes itself as experimental and not production-ready, with no releases and limited expectations around support.

## 6. Evaluation and benchmarking

#### 3DGen-Bench

3DGen-Bench is a benchmark suite for 3D generative models with human preference data and automated evaluators.

Resources:
- https://arxiv.org/abs/2503.21745

Why it matters:
- reminds us that 3D generation evaluation is still immature,
- useful if benchmarking multiple candidate model pipelines later,
- important for avoiding “cool demo, bad product fit” traps.

## What the research suggests for this project

### Strong conclusion 1

The project should not start by trying to generate arbitrary polished 3D models directly into the multiplayer world.

### Strong conclusion 2

The most promising fit is a **structured object grammar** where AI maps player intent into:

- categories,
- parts,
- size tier,
- material palette,
- behavior tags,
- structured voxel operations.

### Strong conclusion 3

Part-aware and modular generation research is strategically more relevant than chasing maximum photoreal fidelity.

### Strong conclusion 4

A voxel-native world substrate may make multiplayer synchronization, rollback, diffing, and archive snapshots more manageable.

## Recommended research direction for prototype stage

### Most relevant to track closely

- TRELLIS / TRELLIS.2
- Hunyuan3D-2 / 2.1
- OmniPart
- AssetFormer
- Voxify3D
- MaaG

### Most practical prototype posture

Use:

- LLM/VLM for intent parsing,
- constrained object grammar,
- deterministic voxel builder,
- optional future use of stronger 3D models for offline or assisted asset authoring.

Do not use a raw state-of-the-art 3D model as the single live runtime core.

## Reference list

- Microsoft TRELLIS — https://github.com/microsoft/TRELLIS
- Microsoft TRELLIS.2 — https://github.com/microsoft/TRELLIS.2
- TRELLIS.2 project page — https://microsoft.github.io/TRELLIS.2/
- Tencent Hunyuan3D-2 — https://github.com/Tencent-Hunyuan/Hunyuan3D-2
- Tencent Hunyuan3D-2.1 — https://github.com/tencent-hunyuan/hunyuan3d-2.1
- Microsoft MaaG article — https://www.microsoft.com/en-us/research/articles/maag-a-new-framework-for-consistent-ai-generated-games/
- MaaG publication page — https://www.microsoft.com/en-us/research/publication/model-as-a-game-on-numerical-and-spatial-consistency-for-generative-games/
- Cubiquity — https://github.com/DavidWilliams81/cubiquity
- OmniPart — https://arxiv.org/abs/2507.06165
- OmniPart project page — https://omnipart.github.io/
- AssetFormer — https://arxiv.org/abs/2602.12100
- AssetFormer OpenReview — https://openreview.net/forum?id=ODB82HDp0V
- Voxify3D — https://arxiv.org/abs/2512.07834
- Voxify3D project page — https://yichuanh.github.io/Voxify-3D/
- 3DGen-Bench — https://arxiv.org/abs/2503.21745
