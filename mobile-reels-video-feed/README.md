# Mobile web short-video feed

**Stage:** Research / idea · **Researched:** 2026-11-15

## Idea and question

Build a mobile-web, vertical, swipe-up/down short-video feed that feels responsive even on modest networks, without building a video infrastructure company. The initial product assumption is on-demand public short clips; content ownership, authentication, moderation and geographic audience are undecided. This is a research proposal, not a measured implementation.

**Conclusion:** standard HTML video, HTTP, browser media decoders and, if needed, HLS/MSE are sufficient for a first version. WebAssembly is not needed for networking, decoding, scrolling or preloading; using a software decoder can cost battery and lose hardware acceleration. Introduce it only for a measured, unsupported computation. Native-app parity is not guaranteed, especially under iOS browser restrictions.

## What the primary sources actually say

These sources describe different products and snapshots in time. They are not interchangeable, nor proof of current production settings on every device or network.

### TikTok: five videos ahead in a 2023 measurement

[Dashlet, USENIX NSDI 2023](https://www.usenix.org/system/files/nsdi23-li-zhuqi.pdf) reverse-engineered TikTok network traffic and reported that, in the studied app, the **first chunk of each of the next five videos** was prefetched, including out of order. That is an observed native-app policy at the time of the study, not an official current guarantee and not five seconds per video. The paper’s key insight is scheduling: protect the current video against rebuffering while hedging against early swipes; overfetching the current clip or distant clips both waste data. It evaluates a research scheduler using user swipe traces; its experimental improvements should not be read as a production benchmark for our web app. A [2026 follow-up measurement](https://aqualab.cs.northwestern.edu/publication/2026/yzhang-conext26/YZhang-CoNEXT26.pdf) cites that five-video observation and estimates around 10 seconds of buffered content based on its own observed chunk sizes and assumed 1 Mbit/s. This is an estimate, not a direct current measurement of the same policy.

[Swipe Along, ACM MMSys 2022](https://par.nsf.gov/servlets/purl/10382657) compared TikTok, Instagram Reels, YouTube Shorts and Facebook Watch, examining preloading, quality and network conditions. It demonstrates that short-video services prioritize startup and use distinct strategies; measurements are snapshots and should not be assumed to apply unchanged today. It is useful for designing repeatable network and swipe experiments, not as an authoritative present-day configuration.

### TikTok’s documented web player: five seconds per video

[TikTok Minis Player documentation](https://developers.tiktok.com/docs/en/minis-player) describes a **specific Minis/VePlayer SDK**, not necessarily the main TikTok app or website. Its documented defaults include `preloadTime: 5` seconds, `prevCount: 1`, `nextCount: 2` in feed mode, and an LRU cache limit of 15 videos. The page’s prose describes the direction of `prevCount` and `nextCount` inconsistently; treat the numeric settings as documented and test actual direction instead of guessing.

This SDK’s architecture is especially relevant: it supports MP4 preloading using MSE, uses GOP/range-based initial downloads, maintains a shared cache decoupled from player instances, and reuses data at startup. It reports preload-hit metrics and avoids spawning extra video decoders for each prefetched item. The documentation lists a Managed Media Source path for supported iOS environments (iOS 17.1+) and MSE on supported desktop/Android environments. This is an example of **existing web technology with a deliberate JS media stack**, not evidence that `preload="auto"` alone achieves the same result. Check actual SDK availability, licensing and integration scope before selecting it.

### Instagram/Meta: prefetch plus careful codec economics

[Meta’s 2023 AV1 engineering account](https://engineering.fb.com/2023/02/21/video-engineering/av1-codec-facebook-instagram-reels/) says it prefetched multiple Reels earlier to offset software-decoder startup costs, without stating an exact number or duration. It also describes multiple ABR renditions, content-dependent encoding effort, device benchmarking, and codec choice. Its AV1 decoder integration described native applications, not a browser implementation. Meta’s [2022 Instagram encoding article](https://engineering.fb.com/2022/11/04/video-engineering/instagram-video-processing-encoding-reduction/) explains separating compatible baseline encodes from more expensive advanced encodes for watch-time economics. A [2025 Instagram iOS study](https://engineering.fb.com/2025/11/17/ios/enhancing-hdr-on-instagram-for-ios-with-dolby-vision/) found additional HDR metadata increased loading time and reduced watch time in its first test; reducing the overhead changed the result. These examples show why delivery size, decoder startup and actual device telemetry matter alongside network prefetching.

### Practical translation for a small mobile website

- Build an explicit feed scheduler, not a pile of `<video preload>` elements: current playback first; then fetch an initialization/index and first independently decodable segment/range of likely neighbours; cancel work when the queue changes. Keep byte and concurrency budgets.
- For precise reuse, a compatible MP4-over-MSE or segmented HLS player must own both preload cache and playback consumption. Merely issuing a `fetch` and then setting a native video `src` can duplicate requests. Verify with a network trace. On native HLS/iOS paths, exact prefetch control and reuse are implementation-dependent; provide a functional native fallback rather than promising equal behavior.
- Five seconds × 1 next, 2 next and 5 next should all be benchmark variants alongside 2–4 second alternatives. A real five-second target can exceed one segment due to GOP/segment boundaries. On backward navigation retain a small bounded previous window, not an unlimited history.
- Byte cache, decoded frame/decoder readiness and poster readiness are separate. Data in memory avoids network latency but does not prove a frame is decoded or ready for display; warm decoders cost memory/power. Measure first displayed frame, not just data downloaded.
- Separate a feed API/recommendation queue from CDN video delivery and offline encoding. Meta-scale custom encoders, native decoders and predictive models are not prerequisites for a small site. Reproduce the **principles** and measure on real browsers rather than claiming to clone the native apps.

## What should be preloaded?

There is no verified universal Instagram rule here. However, TikTok’s documented Minis web player defaults to five seconds per item, and a 2023 paper observed TikTok’s native app prefetching the first chunk of five upcoming videos. These are distinct products and observations, not a current Instagram specification; see the detailed research below. Preloading depends on network, device memory, predicted navigation, startup latency and acceptable wasted bytes. Research on [demand-driven short-video preloading](https://arxiv.org/abs/2510.18459) treats it as a trade-off rather than a constant.

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
2. Include the documented Minis-style 5-second/1-previous/2-next configuration and the research-inspired five-next-first-chunk configuration where technically possible; measure their waste and confirm actual browser cache reuse. Test actual iPhone Safari and Android Chrome on Wi-Fi, constrained mobile, high RTT and intermittent loss; include cold and warm cache, background/foreground and sound activation. Use a representative low-end phone. Avoid judging iOS behavior from desktop emulation alone.
3. Instrument navigation timestamp → `playing`/first rendered frame (where available), startup p50/p95, rebuffer duration, successful play, bytes delivered vs bytes viewed, speculative bytes never watched, request counts, memory, battery/thermal impact and failures. Cross-check with browser network tools and CDN logs; video `playing` is a proxy, not always the first visible frame.
4. Initial targets to validate, not established requirements: p95 swipe-to-first-frame under 500 ms on a defined warm-next mobile profile; no visible stall for 95% of plays; speculative waste under 25% of delivered bytes. Record device/network and sample sizes. Tune or reject targets based on actual user expectations.
5. Compare 0/1/2 next clips and 2/4/5 seconds with the same swipe traces. Only add MSE manual buffering or a more complex cache if measured gains justify complexity. Service-worker/cache APIs have quota and eviction constraints; don't assume reliable offline persistence or seamless range reuse.

## Open questions

- Expected clip length, upload volume, geographic audience and peak concurrency?
- Public or private video, acceptable content moderation and retention requirements?
- Can the feed start muted, and is vertical-only sufficient?
- What startup latency and wasted data do real users accept, especially on cellular?
- Which exact player and iOS versions permit controllable prefetch without duplicate downloads?
