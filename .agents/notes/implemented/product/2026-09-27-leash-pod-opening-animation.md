# Leash pod opening animation

The trigger is an axial pull on the orange handle. The animation uses
keyframed motion to show the sear release, spring lid, and webbing payout.
The harness attachment remains fixed.

A separate Blender file contains the animation and the three static
scenes. The five-second clip uses 24 frames per second. Camera movement
keeps the closed pod large enough to read, then makes room for the lid and
released handle.

The webbing uses matching ribbon topology and shape keys for controlled
poses. Cloth simulation would add setup and nondeterminism without helping
explain the release. This is a motion concept, not a mechanics simulation.

The closed, pull, opening, and settled poses passed visual review. All
120 frames keep the product inside the camera bounds, and the harness clip
has no animation. `wearable-leash-pod/assets/animation-validation.json`
records the checks.

The MP4 uses H.264 at 1280 × 960 with 24 frames per second. The editable
project opens at frame 1 in `04_Opening_animation`.
