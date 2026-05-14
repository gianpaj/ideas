# Puffy 3D — Gradient Text Renderer

A beautiful real-time 3D text renderer built with Three.js. Create eye-catching 3D extruded text with gradient colors, adjustable puffiness, and interactive lighting.

## Features

- **50+ Google Fonts** — Browse through popular web fonts instantly
- **Font Navigation** — Use left/right arrows to cycle through fonts smoothly
- **Gradient Colors** — Top-to-bottom gradient control with color pickers
- **3D Extrusion** — Adjustable puffiness (bevel depth) for that glossy look
- **Interactive Lighting** — Drag the light angle slider to see highlights move in real-time
- **Material Controls** — Fine-tune glossiness (roughness) and clearcoat effects
- **Auto-rotate** — Toggle automatic spinning for presentations
- **Drag to Orbit** — Full 3D camera control with mouse/touch
- **Scroll to Zoom** — Pinch zoom on touch devices

## How to Use

1. Open `puffy-3d.html` in a modern web browser
2. Type your text in the "Text" field
3. Select a font from the dropdown or use ← → arrows to browse
4. Customize the gradient colors with the color pickers
5. Adjust "Puffiness" for bevel depth
6. Control "Glossiness" for material reflectivity
7. Move the "Light angle" slider to change highlight position
8. Enable "Auto-rotate" for automatic spinning
9. Drag on the canvas to orbit the camera
10. Scroll to zoom in/out

## Technical Details

- **Engine**: Three.js (WebGL rendering)
- **Fonts**: 50+ Google Fonts via jsDelivr CDN
- **Material**: MeshPhysicalMaterial with clearcoat and sheen
- **Lighting**: 4-light setup (ambient + key + rim + back)
- **Camera**: Perspective camera with OrbitControls
- **Text**: TextGeometry with beveled edges

## Font List

Roboto, Open Sans, Lato, Montserrat, Raleway, Playfair Display, Poppins, Inter, Oswald, Ubuntu, Merriweather, Nunito, PT Sans, Quicksand, Dosis, Inconsolata, Caveat, Syne, Work Sans, Manrope, DM Sans, IBM Plex Mono, JetBrains Mono, Courier Prime, Space Mono, Overpass, Outfit, Cabin, Mulish, Varela Round, Barlow, Crimson Text, Source Code Pro, Abril Fatface, Pacifico, Fredoka, Kanit, Kumbh Sans, Aleo, Archivo, Libre Baskerville, Bitter, Noto Serif, Exo 2, Baskervville, Alegreya, Titillium Web, Alkaline, Archivo Black, Antonio

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## research 

https://wcandillon.github.io/redraw/

## Created

May 7, 2026
