# React Chat Pet Companion

## Purpose

Add a small animated companion beside a React chat window. The companion reflects the assistant's live state—resting, thinking, waiting for input, succeeding, or failing—without competing with the conversation.

The initial asset is a Hatch Pet v2 sprite atlas: 8 columns by 11 rows, with 192 by 208 pixel cells. Rows 0–8 are activity animations. Rows 9–10 provide the 16 look directions.

## Recommended runtime

Use a dedicated `<ChatPet />` React component backed by one canvas. The canvas renderer crops one atlas cell per frame, draws it at integer-scaled pixels, and uses `requestAnimationFrame` for timing. Canvas keeps pixel edges crisp, avoids creating dozens of DOM nodes, and makes directional changes cheap.

Keep React responsible for state and layout. Keep the renderer responsible for atlas geometry, frame timing, sprite drawing, and device-pixel-ratio scaling.

```text
Chat events → Pet controller → Pet state + look target → Canvas renderer
```

## Component boundaries

### ChatPet

Public React component. It receives a pet definition, a semantic state, an optional look target, size, and reduced-motion preference. It owns the canvas lifecycle and passes normalized state to the renderer.

```tsx
<ChatPet
  pet={codexPet}
  activity="working"
  lookAt={{ x: pointerX, y: pointerY }}
  size={96}
/>
```

### Pet controller

Maps chat and tool lifecycle events to stable semantic states. It debounces fast changes so the pet does not flicker between idle and working.

| Chat signal | Pet activity | Atlas row |
|---|---|---:|
| No active request | `idle` | 0 |
| Assistant/tool streaming | `working` | 7 |
| Dragged beside a pane | `moveRight` / `moveLeft` | 1 / 2 |
| Assistant requests user action | `waiting` | 6 |
| User opens or focuses chat | `wave` | 3 |
| Successful completion | short `jump`, then `idle` | 4, then 0 |
| Error or cancelled request | `failed` | 5 |
| Reviewing a response or attachment | `reviewing` | 8 |

The controller should expose an event API rather than coupling directly to one chat SDK:

```ts
petController.dispatch({ type: "assistant:stream-start" });
petController.dispatch({ type: "assistant:needs-input" });
petController.dispatch({ type: "assistant:complete" });
```

### Atlas renderer

Loads `pet.json` and `spritesheet.webp`. It verifies `spriteVersionNumber: 2`, uses the 192 by 208 cell grid, and looks up the correct row/frame from a small animation registry. It uses nearest-neighbor image smoothing disabled for pixel art.

The renderer holds a per-state frame duration table. Looped states cycle indefinitely; one-shot states such as jump complete, then fall back to idle. State changes restart only when required by the animation contract.

### Look controller

Converts a pointer or focus target into an angle relative to the pet's center. The angle is quantized to the nearest one of the 16 v2 directions. Apply a deadzone around the center so neutral attention remains on the idle animation. Smooth target changes over roughly 120–180 ms to avoid rapid direction flicker.

Direction rows are an attention overlay, not a replacement for activity animation. Start with this priority order:

1. One-shot activity states.
2. Directional drag movement.
3. Gaze direction when the pet is idle, waiting, working, or reviewing.
4. Neutral idle fallback.

For the first release, use gaze only while the main state is idle, waiting, working, or reviewing. The renderer may render the current activity row in the main canvas and use a future separate head/display layer only if a later atlas format supports it. Do not mix unrelated full-body rows in one draw call.

## Layout beside chat

Place the pet in a non-scrolling sidebar or a fixed corner of the chat shell. On wide layouts, use a 96–128 px visual footprint with 16–24 px spacing from the chat edge. On small screens, reduce it to 56–72 px or hide it behind an accessibility-respecting user preference.

The pet must not block typing, messages, buttons, or text selection. Use `pointer-events: none` by default. Add an optional focusable toggle only when interaction is intentionally introduced.

## Accessibility and preferences

- Respect `prefers-reduced-motion`: render a static idle cell and disable gaze smoothing/loops.
- Provide a user setting to hide the pet.
- Mark the decorative canvas `aria-hidden="true"` unless it becomes interactive.
- Do not encode essential chat status only through the pet; retain textual status and normal controls.

## Performance

- Preload the atlas once and share it through a React context or asset cache.
- Draw at the CSS size multiplied by `devicePixelRatio`, then scale the canvas context.
- Disable image smoothing and align draw coordinates to whole pixels.
- Pause animation when the tab is hidden or the pet is outside the viewport.
- Avoid React state updates every frame. Keep frame time in the renderer and update React only for semantic state changes.

## Delivery plan

### Phase 1: Asset and renderer

Create a small `pet-runtime` package with a manifest loader, animation registry, canvas renderer, and unit tests for row/frame selection. Render Codex beside a static mock chat window.

### Phase 2: Chat-state integration

Add the event-driven pet controller. Wire idle, working, waiting, complete, failed, and review states to the chat lifecycle. Add debouncing and one-shot fallbacks.

### Phase 3: Direction and interaction polish

Add pointer/focus look targets, 16-direction quantization, deadzone, reduced-motion behavior, visibility pause, and responsive placement.

### Phase 4: Product hardening

Add telemetry-free local diagnostics, visual regression snapshots for every atlas row, keyboard/accessibility review, and a pet-picker API for future custom pets.

## Acceptance criteria

- Codex loads from a v2 `pet.json` and atlas without hard-coded asset paths.
- The companion visibly follows chat lifecycle states without flicker.
- Pixel art remains crisp at supported sizes and does not degrade scrolling or typing.
- Reduced-motion and hide-pet preferences work.
- The pet never obstructs the chat UI.
- Unit tests cover mapping, state priority, one-shot completion, direction quantization, and v2 manifest rejection.
