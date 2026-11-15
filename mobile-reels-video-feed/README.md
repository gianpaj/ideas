# Mobile web short-video feed

**Stage:** Research / idea · **Researched:** 2026-11-15

## Idea and question

Build a mobile-web, vertical, swipe-up/down short-video feed that feels responsive even on modest networks, without building a video infrastructure company. The initial product assumption is on-demand public short clips; content ownership, authentication, moderation and geographic audience are undecided. This is a research proposal, not a measured implementation.

**Conclusion:** standard HTML video, HTTP, browser media decoders and, if needed, HLS/MSE are sufficient for a first version. WebAssembly is not needed for networking, decoding, scrolling or preloading; using a software decoder can cost battery and lose hardware acceleration. Introduce it only for a measured, unsupported computation. Native-app parity is not guaranteed, especially under iOS browser restrictions.

## What should be preloaded?

There is no verified universal Instagram rule here: neither “five seconds” nor “N videos ahead” is established by these sources. Preloading depends on network, device memory, predicted navigation, startup latency and acceptable wasted bytes. Research on [demand-driven short-video preloading](https://arxiv.org/abs/2510.18459) treats it as a trade-off rather than a constant.

Initial experiment, **not a claim about Instagram**:

1. Fetch the feed metadata and posters for the next 3–5 items. Posters are cheap and hide unavoidable waits.
2. Play only the active clip. Once its buffer is healthy, attempt to warm the next clip with its initialization data and roughly the first 2–4 seconds, e.g. one or two 2-second segments. Keep the previous clip available for immediate backward scrolling where the browser permits. Initially preload **one next video**, not five complete videos.
3. Cancel stale next-item requests when the user swipes rapidly or reverses. Active playback always has priority; cap concurrent speculative fetches to one and stop on stalls, hidden tab, data-saving preference, or memory pressure. Raise/lower the budget only from measurements. Restart cautiously when returning to the foreground.
4. Use a bounded window of mounted players, for example previous/current/next; release distant sources and listeners. Observe behavior on real devices: browsers may evict media or keep their own buffers, so these are goals, not guarantees.

A 5-second initial budget at **1.5 Mbit/s total** is approximately **0.94 MB per video** (1.5 × 5 ÷ 8); 2 seconds is 0.375 MB. Actual variable-bitrate segment size, audio, manifests, request headers and keyframe boundaries change this. Five speculative clips × 5 seconds ≈ 4.7 MB even if none is watched. Byte/time budgets should be set per segment and rendition; an MP4 byte range does not automatically equal an exact duration.

### Browser reality

`preload` is a **hint**, not a promise of five seconds; browsers may ignore it. Explicit byte-accurate buffering requires a tested segmented player path, and a manual `fetch()` of a range does not guarantee the browser's native video element will reuse those bytes. [web.dev's preload discussion](https://web.dev/articles/fast-playback-with-preload) describes these trade-offs. Test actual network and buffering behavior separately on iOS Safari and Android Chrome, including data saver, backgrounding and low memory.

On iOS use `playsinline` and start muted; `play()` can reject and sound needs a user gesture. Provide tap-to-play/unmute, captions, reduced-motion support and an accessible non-swipe way to navigate. See [Apple's Safari video guidance](https://developer.apple.com/documentation/webkit/delivering-video-content-for-safari). Don't assume autoplay and invisible prebuffering behave the same on all browsers.

## Delivery choices

### A. Smallest viable: progressive MP4

Upload → offline FFmpeg transcode → object storage → CDN → `<video>`. Encode H.264/AAC in MP4 for broad initial compatibility, reasonable mobile resolution/bitrate and `-movflags +faststart` so metadata comes first. Set posters, correct MIME types and immutable cache headers for versioned files. Support real HTTP byte ranges (`206`, `Content-Range`) and test through the CDN, not just origin. [MDN explains range requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests).

This is the simplest starting point for short fixed-quality clips. The browser controls buffering, so precise next-clip preload and bitrate adaptation are limited; measure before inventing a custom cache. A small static file server can serve it, but its network uplink becomes a bottleneck without a CDN.

### B. Recommended when control/adaptation matters: HLS

Upload → background transcode multiple aligned H.264/AAC renditions → HLS playlists + short segments → object storage/CDN → native HLS where available, otherwise a compatible MSE player such as [hls.js](https://github.com/video-dev/hls.js). Feature-detect and test; avoid assuming every iOS browser supports a particular MSE path. Start with 2-second segments and two or three bitrate ladders as a hypothesis; tune startup, request overhead and quality. Segmenting provides explicit units to prefetch, though player APIs and caching must be verified on each target browser. Align keyframes/segments and account for manifest and init-segment dependencies. A managed service can do the transcoding and packaging.

### C. Managed video platform

A managed encoder/storage/CDN is the lowest operational burden when creators upload arbitrary files. Evaluate whether its player or HLS access exposes the control necessary for feed prefetch; a managed iframe alone may not. [Cloudflare Stream pricing](https://developers.cloudflare.com/stream/pricing/) lists $5 per 1,000 stored minutes capacity monthly and $1 per 1,000 delivered minutes; preloaded segments count as delivery. Example: 1,000 stored minutes and 10,000 delivered minutes ≈ **$15/month**, excluding other services/taxes and subject to billing/rounding rules. This is delivered minutes, not merely minutes watched; verify current pricing before purchasing.

## Minimum infrastructure and sizing

**Small MVP:** a static web app, a tiny feed API (or static JSON initially), a background encoder that runs only on upload, object storage and HTTPS CDN. No always-on streaming server, GPU, live-video server, or transcoding on each view is required for on-demand pre-encoded media. One modest shared CPU VM with 1–2 vCPU and 1–2 GB RAM can be a *starting hypothesis* for a small API and occasional serial encoding, not a capacity guarantee: benchmark actual source resolution, codec, encoding speed, queues and burst uploads. Managed encoding removes that VM requirement. Limit uploads and queue work; do not transcode in the request path.

For direct delivery, estimate **egress Mbit/s ≈ concurrent viewers × average total rendition bitrate × (1 + speculative overhead)** before CDN cache effects. Example: 100 concurrent viewers × 1.5 Mbit/s × 1.2 = **180 Mbit/s** at the delivery edge, not a guarantee of origin traffic. Monthly illustrative consumption: 10,000 sessions × 10 minutes × 60 × 1.5 / 8 = **1,125,000 MB ≈ 1.125 TB decimal** watched at the stated rate, plus speculative downloads and protocol overhead. Concurrent swipes can create burst request rates; measure origin cache misses, not just averages.

For a DIY cost comparison, [Cloudflare R2](https://developers.cloudflare.com/r2/pricing/) lists standard storage, request pricing and free direct egress, with a free tier; CDN/worker and other services may add charges. Storage includes all renditions and source files, not just final watch duration. Public assets can use long-lived immutable URLs; private assets need authorization/signed URLs, careful cache keys and expiry. Apply upload limits, validate and sandbox untrusted media, and consider moderation if uploads are public.

## Experiment before committing to architecture

1. Prepare 20 diverse portrait clips, posters, fast-start MP4s and aligned HLS ladders. Compare MP4 native playback, HLS with no prefetch, then HLS with one-next 2 seconds and 4 seconds. Include reverse swipes and fast skips.
2. Test actual iPhone Safari and Android Chrome on Wi-Fi, constrained mobile, high RTT and intermittent loss; include cold and warm cache, background/foreground and sound activation. Use a representative low-end phone. Avoid judging iOS behavior from desktop emulation alone.
3. Instrument navigation timestamp → `playing`/first rendered frame (where available), startup p50/p95, rebuffer duration, successful play, bytes delivered vs bytes viewed, speculative bytes never watched, request counts, memory, battery/thermal impact and failures. Cross-check with browser network tools and CDN logs; video `playing` is a proxy, not always the first visible frame.
4. Initial targets to validate, not established requirements: p95 swipe-to-first-frame under 500 ms on a defined warm-next mobile profile; no visible stall for 95% of plays; speculative waste under 25% of delivered bytes. Record device/network and sample sizes. Tune or reject targets based on actual user expectations.
5. Compare 0/1/2 next clips and 2/4/5 seconds with the same swipe traces. Only add MSE manual buffering or a more complex cache if measured gains justify complexity. Service-worker/cache APIs have quota and eviction constraints; don't assume reliable offline persistence or seamless range reuse.

## Open questions

- Expected clip length, upload volume, geographic audience and peak concurrency?
- Public or private video, acceptable content moderation and retention requirements?
- Can the feed start muted, and is vertical-only sufficient?
- What startup latency and wasted data do real users accept, especially on cellular?
- Which exact player and iOS versions permit controllable prefetch without duplicate downloads?
