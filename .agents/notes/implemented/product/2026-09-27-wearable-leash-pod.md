# Wearable leash pod

The Blender model uses millimeters, with one scene unit equal to one
millimeter. The closed shell measures 70 × 45 × 22 mm. Named collections
separate the shell, latch, leash, harness, lighting, and cameras.

Three static scenes share the harness and lighting. Each scene selects a
closed, cutaway, or released assembly and its camera. Separate scenes keep
the camera and product state together without animation or visibility
drivers.

An interior cover conceals the latch in the released view. The cutaway
removes the cover and the near shell. The released view excludes latch
parts to keep the internal mechanism specific to the cutaway.

The orange handle is a flattened loop of 16 mm nylon ribbon recessed into
the lid. A guided axial cam lifts the sear, and a solenoid plunger acts on
the same sear. Guide cheeks represent the constraint against lateral
motion. The model illustrates the mechanism, without force or tolerance
validation.

The harness attachment carries the leash load. The pod stores a short
accordion stack and retains the handle. The released scene keeps the
leash clip attached to the harness.

Blender reports closed shell bounds of 70 × 45 × 22 mm and 146.3 mm of
folded webbing. All three camera frames contain the product and harness.
The file contains 109 named objects, six root collections, and no animation
actions. `wearable-leash-pod/assets/validation.json` records the checks.

Flue 1.0.31 and its Blender add-on provide the live connection. The camera
images use Blender's OpenGL viewport capture with scene lighting and
materials. The saved file opens in the closed scene.
