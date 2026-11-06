# Two apps, talking in tones

https://github.com/user-attachments/assets/f3697d93-78ae-4490-98b9-f49c6d5dcf72

[Download the 15.94-second MP4](audio-handshake-explained.mp4) ·
[editable SVG overview](overview.svg) · [source/timing manifest](manifest.json)

The original **actual live exchange** plays once, at normal speed, with no
speech or sound effects added. Seven arrows light up at the start/end times
independently decoded from the original stereo WAV. Cyan is initiator→responder
(left audio channel); amber is responder→initiator (right). A moving playhead
shows where you are in the recording. This is an explanation of a recorded
causal exchange, not a new simulated run or a new protocol implementation.

1. **HELLO:** A starts a fresh session with a random session identifier.
2. **CHALLENGE:** B adds its fresh random challenge.
3. **CONFIRM:** A proves knowledge of the derived session key.
4. **READY:** B acknowledges the pairing before A sends application data.
5. **DATA:** A sends its real application bytes through tones.
6. **RECEIPT:** B returns the same bytes and their digest. A checks both, as
   well as the authentication tag. The operation is an idempotent echo, not a
   booking or another external action.
7. **CLOSE:** A closes after verifying the receipt. This is **best effort**;
   there is no final acknowledgement or atomic shared completion guarantee.

Both apps were provisioned with the same private key beforehand. Authentication
establishes membership in that shared-key domain, **not a public identity**.
The payload is **not encrypted**. This is the custom experimental **AIP-FSK2**
profile, not T.30/V.21 fax compatibility. No browser, HTTP handoff or actual
telephone call was used. See the [runnable prototype](../README.md) for code,
independent clock/fault tests and exact limitations.

## Re-render

Requires Node 24, FFmpeg with **librsvg**, libx264 and AAC support, and the
DejaVu Sans font. No npm packages, browser, raster-art generator or GPU needed.
From this directory:

```sh
node render.mjs
```

The script reads these existing files, verifies that the decoded timing source
matches the WAV SHA-256, then regenerates the SVG, MP4 and provenance manifest:

- `../evidence/live-exchange-2026-11-06.wav` — original 8 kHz stereo capture.
- `../evidence/live-exchange-decoded.json` — blind, CRC-confirmed frame times.
- `../evidence/live-exchange-manifest.json` — capture conditions/endpoint results.

SVG-to-PNG rendering uses FFmpeg's librsvg decoder. Temporary frame SVGs/PNGs,
the overview PNG and a mid-video `preview-receipt.png` are kept in ignored
`.render/` for visual inspection. The overview source is generated from the
shared layout in `render.mjs`; edit that layout to retain edits on the next run.
The retained SVG is also directly editable as a standalone asset.

Animation boundaries come from exact audio metadata and are quantized by at
most one 30 fps frame. They depict **waveform bursts**, not the precise moment
an endpoint finishes decoding/authentication. AAC/video container padding can
make the reported MP4 duration a few milliseconds longer than the 15.943125 s
PCM source. The only audio processing is AAC compression and resampling from
8 to 48 kHz; channel order and playback speed are preserved.

The layout and synchronization are deterministic for the same input files.
Pixel/bitstream identity across machines requires matching FFmpeg/librsvg/font
versions; toolchain versions and output hashes are recorded in `manifest.json`.
No wall-clock creation time or random values are added to the output.

## Export check

The render script extracts the finished MP4's audio back to 8 kHz PCM and runs
the independent blind receiver. It then requires **7/7 original packet hashes,
types and directions to match**. No key, expected message or timing metadata
is passed to that receiver. This checks that the downloadable artifact retains
real decodable modem data, not merely a similar sound.

An initial 80 kbit/s AAC export recovered only six CRC-confirmed packets and
was discarded. The retained **192 kbit/s stereo AAC** export passes all seven.
This result concerns this exact export, not a general claim about codec/carrier
robustness. The compressed audio is not bit-identical to the original PCM.
