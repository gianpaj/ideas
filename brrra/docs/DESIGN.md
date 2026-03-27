# brrr for Android — Design Document

## 1. Overview

brrr is a minimalist, privacy-first push notification service. Users get a webhook URL, call it via HTTP, and their devices receive push notifications instantly. No accounts, no dashboards, no backend storage of message content.

This document describes the design of the Android client and its standalone backend, inspired by the [iOS brrr app](https://brrr.now/how-it-works/).

## 2. Design Principles

- **No accounts** — device identity only, no sign-up or login
- **Privacy-first** — raw secrets never leave the device; notification content is never stored server-side; FCM carries only wake-up pings, never message content
- **Reliable delivery** — dual transport ensures notifications arrive whether the app is active or asleep
- **Simple** — no dashboard, no team features, just a webhook and notifications

## 3. Architecture

```
┌──────────────┐       HTTPS POST        ┌─────────────────────┐
│  Any HTTP     │ ─────────────────────► │  Cloudflare Worker   │
│  Client       │    (webhook call)       │  (Hono router)       │
└──────────────┘                          │                      │
                                          │  1. Verify digest     │
                                          │  2. Route to device   │
                                          └─────────┬────────────┘
                                                    │
                                                    ▼
                                          ┌─────────────────────┐
                                          │  Durable Object      │
                                          │  (per device)        │
                                          │                      │
                                          │  - WebSocket conn    │
                                          │  - Hibernation API   │
                                          │  - Message buffer    │
                                          └──┬──────────────┬───┘
                                             │              │
                              ┌──────────────┘              └──────────────┐
                              │                                            │
                              ▼                                            ▼
                    ┌───────────────────┐                      ┌──────────────────┐
                    │  WebSocket         │                      │  FCM (wake-up)    │
                    │  (app is active)   │                      │  (app is asleep)  │
                    │                    │                      │                   │
                    │  Full message      │                      │  Content-free     │
                    │  delivered inline   │                      │  data message     │
                    │  via WS frame      │                      │  {deviceId only}  │
                    └────────┬──────────┘                      └────────┬─────────┘
                             │                                          │
                             └──────────────┬───────────────────────────┘
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │  Android App       │
                                  │                    │
                                  │  - Show notif      │
                                  │  - Store history   │
                                  │  - Reconnect WS    │
                                  └───────────────────┘
```

### 3.1 Dual Transport: WebSocket + FCM

Android aggressively kills background processes and severs network connections (Doze mode, OEM battery optimizations). No persistent connection from an app can reliably survive the background. This is why FCM exists — Google Play Services maintains a single OS-level connection exempt from all restrictions.

**Our approach (same as Signal, ntfy):**

| State | Transport | What's delivered |
|---|---|---|
| App active (foreground) | **WebSocket** | Full notification content via WS frame |
| App in background / closed | **FCM wake-up** | Content-free data message (`{deviceId}` only) |
| App woken by FCM | **WebSocket reconnect** | App reconnects WS, DO flushes buffered messages |
| Device offline | **DO buffer** | Messages held for up to 1 hour, delivered on reconnect |

**Privacy guarantee:** FCM never carries notification content. Google sees only that a device was pinged. The actual title/body/image is delivered exclusively through the WebSocket connection to the Durable Object.

### 3.2 Why WebSocket (not SSE)

| Factor | SSE | WebSocket |
|---|---|---|
| DO Hibernation | Not possible | Supported (near-zero idle cost) |
| Connection lifetime on CF | ~10 min max | Indefinite |
| Dead connection detection | Manual | Automatic (ping/pong) |
| Direction | One-way | Bidirectional |
| CF ecosystem fit | Against the grain | Native support |

Durable Objects were built for WebSocket. The Hibernation API allows DOs to sleep while the CF edge maintains the connection — the DO only wakes when a message arrives or the socket closes. This makes idle connections essentially free.

### 3.3 Components

| Component | Technology | Role |
|---|---|---|
| **Webhook Receiver** | Cloudflare Worker + Hono | Accepts webhook calls, verifies digests, routes messages |
| **Connection Manager** | Cloudflare Durable Objects (Hibernation API) | Per-device WebSocket + message buffer |
| **Device Registry** | Cloudflare KV | Stores device ID → digest + FCM token mappings |
| **FCM Relay** | CF Worker → FCM HTTP v1 API | Sends content-free wake-up pings |
| **Android App** | Kotlin + Jetpack Compose | UI, crypto, WebSocket client, notification display |
| **WebSocket Client** | OkHttp | Persistent connection to DO when app is active |
| **FCM Receiver** | Firebase Messaging SDK | Receives wake-up pings, triggers WS reconnect |
| **Local Storage** | Room (SQLite) | On-device notification history (14-day TTL) |
| **Secret Storage** | Android Keystore / EncryptedSharedPreferences | Stores raw webhook secrets securely |

## 4. Security Model

### 4.1 Secret Lifecycle

```
┌──────────────────────────────────────────────────────────┐
│  ON DEVICE (never leaves)                                 │
│                                                           │
│  SecureRandom → 32-byte secret → EncryptedSharedPrefs     │
│                        │                                  │
│                        ▼                                  │
│                  SHA-256(secret) = digest                  │
└──────────────────────────┬───────────────────────────────┘
                           │ only the digest + FCM token
                           ▼
┌──────────────────────────────────────────────────────────┐
│  BACKEND (Cloudflare)                                     │
│                                                           │
│  Stores: { deviceId, digest, fcmToken, createdAt }        │
│  Never stores: raw secret, notification content           │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Webhook Verification

1. Caller includes the raw secret in the webhook URL path: `POST /webhook/{deviceId}/{secret}`
2. Worker computes `SHA-256(secret)` and compares to the stored digest (constant-time)
3. If match → deliver; if not → 401

### 4.3 Secret Rotation

1. App generates a new secret on-device
2. App calls the backend rotation endpoint with `old_secret` + `new_digest`
3. Backend verifies `old_secret` against stored digest, then replaces digest
4. App updates local EncryptedSharedPreferences
5. Old webhook URL stops working immediately

### 4.4 What the Backend Stores

| Data | Stored | Purpose |
|---|---|---|
| Device ID | Yes | Route messages to correct Durable Object |
| Secret digest | Yes | Verify webhook requests |
| FCM token | Yes | Send wake-up pings when app is not connected via WS |
| Notification content | **No** | Never persisted, forwarded in-memory only |
| Raw secret | **No** | Only the digest |

### 4.5 FCM Privacy Model

- FCM messages are **data-only** (no `notification` key) to avoid Google's notification display
- Payload: `{ "deviceId": "uuid" }` — no title, body, or image
- Google can see: "device X was pinged at time T" — nothing else
- The app receives the wake-up, reconnects the WebSocket, and fetches the real content from the DO

## 5. Data Flow

### 5.1 Device Registration

```
App                          Worker                    KV
 │                              │                       │
 │  POST /api/register          │                       │
 │  { deviceId, digest,         │                       │
 │    fcmToken }                │                       │
 │ ──────────────────────────►  │                       │
 │                              │  PUT device:{id}      │
 │                              │  { digest, fcmToken } │
 │                              │ ─────────────────────►│
 │                              │                       │
 │  200 OK                      │                       │
 │  { webhookUrl }              │                       │
 │ ◄──────────────────────────  │                       │
```

### 5.2 Receiving a Notification (App Active — WebSocket)

```
Caller                    Worker              Durable Object          App
  │                          │                      │                   │
  │ POST /webhook/{id}/{s}   │                      │                   │
  │ { title, body, image? }  │                      │                   │
  │ ────────────────────────►│                      │                   │
  │                          │ verify digest        │                   │
  │                          │                      │                   │
  │                          │ forward message      │                   │
  │                          │ ────────────────────►│                   │
  │                          │                      │ WS has active conn│
  │                          │                      │ send WS frame     │
  │                          │                      │ ────────────────► │
  │                          │                      │                   │ show notification
  │  200 OK                  │                      │                   │ save to Room DB
  │ ◄────────────────────────│                      │                   │
```

### 5.3 Receiving a Notification (App Asleep — FCM Wake-up)

```
Caller                Worker            DO                FCM             App
  │                      │               │                  │               │
  │ POST /webhook/…      │               │                  │               │
  │ ────────────────────►│               │                  │               │
  │                      │ verify digest │                  │               │
  │                      │ forward msg   │                  │               │
  │                      │ ─────────────►│                  │               │
  │                      │               │ no active WS     │               │
  │                      │               │ buffer message   │               │
  │                      │               │                  │               │
  │                      │               │ send FCM ping    │               │
  │                      │               │ {deviceId}       │               │
  │                      │               │ ────────────────►│               │
  │                      │               │                  │ wake app      │
  │                      │               │                  │ ─────────────►│
  │                      │               │                  │               │
  │  200 OK              │               │                  │    connect WS │
  │ ◄────────────────────│               │◄─────────────────────────────────│
  │                      │               │                  │               │
  │                      │               │ flush buffer     │               │
  │                      │               │ via WS frames    │               │
  │                      │               │ ────────────────────────────────►│
  │                      │               │                  │               │ show notif
```

### 5.4 WebSocket Connection

```
App                              Durable Object
 │                                     │
 │  GET /api/stream/{deviceId}         │
 │  Upgrade: websocket                 │
 │  Sec-WebSocket-Protocol: {secret}   │
 │ ───────────────────────────────────►│
 │                                     │ verify digest
 │  101 Switching Protocols            │
 │ ◄───────────────────────────────────│
 │                                     │
 │  WS frame: {"id":"..","title":".."}│
 │ ◄───────────────────────────────────│  (on webhook trigger)
 │                                     │
 │  ping                               │
 │ ◄───────────────────────────────────│  (CF edge handles during hibernation)
 │  pong                               │
 │ ────────────────────────────────────►│
 │                                     │
```

## 6. Android App Design

### 6.1 UI Screens

**Home Screen**
- Webhook URL displayed prominently
- Copy button + share button
- Connection status indicator (Connected / Reconnecting / Disconnected)
- "How to use" expandable section with curl example
- 3 most recent notifications as a preview

**History Screen**
- Chronological list of notifications received in last 14 days
- Each entry: title, body, timestamp, optional image thumbnail
- Grouped by date
- Swipe to delete individual entries
- "Clear all" option

**Settings Screen**
- Device name (editable)
- Rotate webhook secret (with confirmation dialog)
- Clear history
- Battery optimization guidance (link to disable for brrr)
- About / version

### 6.2 Notification Display

- Standard Android notification with title + body
- Support for optional image (BigPictureStyle)
- Tap opens the app to the history screen
- Notification channel: "brrr notifications" (user can configure importance)
- Separate channel for the foreground service: "brrr connection" (silent, low importance)

### 6.3 First-Run / Onboarding Flow

1. Request `POST_NOTIFICATIONS` permission (required on Android 13+)
2. Generate device ID (UUID v4) and secret (32 random bytes)
3. Obtain FCM token
4. Register with backend (send deviceId + digest + fcmToken)
5. Start WebSocket foreground service
6. Show Home screen with webhook URL

### 6.4 Foreground Service

- Persistent notification: "brrr is listening" (low-importance channel, minimal)
- Maintains WebSocket connection to Durable Object
- Automatic reconnection with exponential backoff (1s → 2s → 4s → ... → 60s max)
- Reset backoff on successful connection
- On FCM wake-up: immediately reconnect if disconnected

### 6.5 App Architecture (MVVM)

```
┌────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Composable │ ◄── │  ViewModel   │ ◄── │  Repository       │
│  Screens    │     │  (StateFlow) │     │                   │
└────────────┘     └──────────────┘     │  - SecretManager  │
                                         │  - ApiClient      │
                                         │  - Room DAO       │
                                         │  - SseService     │
                                         └──────────────────┘
```

Each screen has a ViewModel exposing a `StateFlow<UiState>`, collected via `collectAsStateWithLifecycle()`.

## 7. Offline Behavior

- When the device loses connectivity, the WebSocket drops
- The Durable Object buffers messages (up to 50 messages, 1-hour TTL)
- If the app is in the background, FCM wake-up attempts are queued by Google and delivered when connectivity returns
- On reconnect, the DO flushes all buffered messages immediately
- Messages older than 1 hour are discarded (webhook caller gets 200 OK regardless — fire-and-forget)

## 8. Multi-Device Support (v2)

Deferred to v2. Design notes for future:

- Each device gets its own webhook URL: `/webhook/{deviceId}/{secret}`
- A **user webhook** targets all devices: `/webhook/user/{userId}/{userSecret}`
- The user secret is generated on the first device and shared via QR code or manual entry
- Each device independently maintains its own WebSocket connection
- KV stores device→user mapping for fan-out

## 9. Webhook API Format

### Send a notification

```
POST /webhook/{deviceId}/{secret}
Content-Type: application/json

{
  "title": "Build complete",           // required
  "body": "main branch deployed",      // optional
  "image": "https://example.com/a.png" // optional, cached on device
}
```

**Response:** `200 OK` (always, fire-and-forget)
**Errors:** `401 Unauthorized` (bad secret), `404 Not Found` (unknown device)

### Minimal call (title only)

```
POST /webhook/{deviceId}/{secret}
Content-Type: application/json

{"title": "ping"}
```

### Query parameter shorthand

```
POST /webhook/{deviceId}/{secret}?title=ping&body=hello
```

## 10. Technology Choices Summary

| Choice | Rationale |
|---|---|
| **Kotlin** | Modern Android standard, concise, null-safe |
| **Jetpack Compose** | Declarative UI, no XML, built-in |
| **ViewModel + StateFlow** | Standard MVVM, survives config changes |
| **Room** | Type-safe SQLite wrapper, part of Jetpack |
| **EncryptedSharedPreferences** | Secret storage backed by Android Keystore |
| **OkHttp** | WebSocket client, de-facto Android HTTP library |
| **Firebase Messaging** | Wake-up pings only (no content), reliable background delivery |
| **Cloudflare Workers + Hono** | Edge deployment, typed routing, generous free tier |
| **Durable Objects (Hibernation)** | Stateful per-device WebSocket, near-zero idle cost |
| **WebSocket** | Native DO support, bidirectional, survives indefinitely |
| **FCM (data-only)** | Background wake-up, zero notification content through Google |

## 11. v1 Scope

**In scope:**
- Single device registration
- Webhook → notification delivery (WebSocket + FCM wake-up)
- On-device notification history (14-day TTL)
- Secret rotation
- Home + History + Settings screens

**Deferred to v2:**
- Multi-device / user webhook
- QR code pairing
- Image support in notifications
- Home screen widget
