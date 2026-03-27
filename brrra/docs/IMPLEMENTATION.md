# brrr for Android — Implementation Plan

## 1. Project Structure

```
brrra/
├── docs/
│   ├── DESIGN.md                # Architecture & design decisions
│   └── IMPLEMENTATION.md        # This file
├── backend/
│   ├── wrangler.jsonc            # Cloudflare Worker config (KV + DO bindings)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── index.ts              # Hono app, routing, export with DO class
│   │   ├── types.ts              # Shared types, Bindings, request/response interfaces
│   │   ├── routes/
│   │   │   ├── register.ts       # POST /api/register
│   │   │   ├── webhook.ts        # POST /api/webhook/:deviceId/:secret
│   │   │   ├── rotate.ts         # POST /api/rotate/:deviceId
│   │   │   └── stream.ts         # GET /api/stream/:deviceId (WS upgrade → DO)
│   │   ├── services/
│   │   │   ├── crypto.ts         # SHA-256 digest, constant-time compare
│   │   │   └── fcm.ts            # FCM HTTP v1 API client (wake-up pings)
│   │   └── durable/
│   │       └── device.ts         # Durable Object: WebSocket + Hibernation + buffer
│   └── test/
│       ├── crypto.test.ts
│       ├── webhook.test.ts
│       └── register.test.ts
├── android/
│   ├── build.gradle.kts           # Root build file
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   ├── gradle/libs.versions.toml  # Version catalog
│   └── app/
│       ├── build.gradle.kts
│       ├── google-services.json   # Firebase config (FCM only)
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── kotlin/com/brrr/app/
│           │   ├── BrrrApp.kt                  # Application class
│           │   ├── MainActivity.kt
│           │   ├── ui/
│           │   │   ├── theme/
│           │   │   │   ├── Theme.kt
│           │   │   │   ├── Color.kt
│           │   │   │   └── Type.kt
│           │   │   ├── navigation/
│           │   │   │   └── BrrrNavHost.kt
│           │   │   ├── home/
│           │   │   │   ├── HomeScreen.kt
│           │   │   │   └── HomeViewModel.kt
│           │   │   ├── history/
│           │   │   │   ├── HistoryScreen.kt
│           │   │   │   └── HistoryViewModel.kt
│           │   │   └── settings/
│           │   │       ├── SettingsScreen.kt
│           │   │       └── SettingsViewModel.kt
│           │   ├── crypto/
│           │   │   ├── SecretManager.kt
│           │   │   └── DigestUtil.kt
│           │   ├── network/
│           │   │   ├── ApiClient.kt             # HTTP client for registration/rotation
│           │   │   └── BrrrWebSocket.kt         # OkHttp WebSocket client
│           │   ├── service/
│           │   │   ├── WebSocketService.kt      # Foreground service
│           │   │   └── BrrrFirebaseMessaging.kt # FCM receiver (wake-up handler)
│           │   ├── data/
│           │   │   ├── db/
│           │   │   │   ├── BrrrDatabase.kt
│           │   │   │   ├── NotificationDao.kt
│           │   │   │   └── NotificationEntity.kt
│           │   │   └── repository/
│           │   │       ├── DeviceRepository.kt
│           │   │       └── NotificationRepository.kt
│           │   └── worker/
│           │       └── CleanupWorker.kt
│           └── res/
│               ├── values/strings.xml
│               └── drawable/
```

## 2. Implementation Phases

### Phase 1: Backend — Cloudflare Worker

#### 1.1 Project Setup

```bash
npm create cloudflare@latest brrr-backend -- --type hello-world --ts --git --deploy false --framework none
cd brrr-backend
npm install hono
npm install -D @cloudflare/vite-plugin vite
```

**wrangler.jsonc:**
```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "brrr-backend",
  "main": "src/index.ts",
  "compatibility_date": "2025-11-11",
  "observability": { "enabled": true },

  // KV for device registry
  "kv_namespaces": [
    { "binding": "DEVICES", "title": "brrr-devices" }
  ],

  // Durable Objects for per-device WebSocket connections
  "durable_objects": {
    "bindings": [
      { "name": "DEVICE_CONNECTION", "class_name": "DeviceConnection" }
    ]
  },

  // DO needs a migration to create the class
  "migrations": [
    { "tag": "v1", "new_classes": ["DeviceConnection"] }
  ],

  // FCM service account key (stored as secret, not in config)
  // Set via: wrangler secret put FCM_SERVICE_ACCOUNT_KEY
  // Set via: wrangler secret put FCM_PROJECT_ID
}
```

#### 1.2 Type Definitions (`src/types.ts`)

```typescript
import type { KVNamespace, DurableObjectNamespace } from '@cloudflare/workers-types'

export type Bindings = {
  DEVICES: KVNamespace
  DEVICE_CONNECTION: DurableObjectNamespace
  FCM_SERVICE_ACCOUNT_KEY: string  // secret
  FCM_PROJECT_ID: string           // secret
}

export interface DeviceRecord {
  digest: string
  fcmToken: string
  name: string | null
  createdAt: number
}

export interface RegisterRequest {
  deviceId: string
  digest: string
  fcmToken: string
  name?: string
}

export interface RegisterResponse {
  webhookUrl: string
  streamUrl: string
}

export interface WebhookPayload {
  title: string
  body?: string
  image?: string
}

export interface RotateRequest {
  oldSecret: string
  newDigest: string
  fcmToken?: string  // optionally update FCM token during rotation
}

export interface BufferedMessage {
  id: string
  payload: WebhookPayload
  ts: number
}
```

#### 1.3 Crypto Utilities (`src/services/crypto.ts`)

```typescript
export async function computeDigest(secret: string): Promise<string> {
  const encoded = new TextEncoder().encode(secret)
  const hash = await crypto.subtle.digest('SHA-256', encoded)
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function verifySecret(secret: string, storedDigest: string): Promise<boolean> {
  const digest = await computeDigest(secret)
  // Constant-time comparison
  if (digest.length !== storedDigest.length) return false
  const a = new TextEncoder().encode(digest)
  const b = new TextEncoder().encode(storedDigest)
  return crypto.subtle.timingSafeEqual(a, b)
}
```

#### 1.4 FCM Service (`src/services/fcm.ts`)

Sends data-only wake-up pings via FCM HTTP v1 API:

```typescript
export async function sendFcmWakeUp(
  fcmToken: string,
  deviceId: string,
  projectId: string,
  serviceAccountKey: string
): Promise<boolean> {
  const accessToken = await getAccessToken(serviceAccountKey)

  const response = await fetch(
    `https://fcm.googleapis.com/v1/projects/${projectId}/messages:send`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: {
          token: fcmToken,
          data: {
            deviceId: deviceId,  // Only the device ID, no content
          },
          android: {
            priority: 'high',   // Wake the device immediately
          },
        },
      }),
    }
  )

  return response.ok
}

// JWT-based auth for FCM v1 API using service account
async function getAccessToken(serviceAccountKey: string): Promise<string> {
  // Parse service account JSON
  // Create JWT with RS256
  // Exchange for access token at https://oauth2.googleapis.com/token
  // Cache token until expiry
  // Implementation uses Web Crypto API (available in Workers)
}
```

#### 1.5 Hono Router (`src/index.ts`)

```typescript
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { registerRoute } from './routes/register'
import { webhookRoute } from './routes/webhook'
import { rotateRoute } from './routes/rotate'
import { streamRoute } from './routes/stream'
import { DeviceConnection } from './durable/device'
import type { Bindings } from './types'

const app = new Hono<{ Bindings: Bindings }>()

// Middleware
app.use('*', logger())
app.use('/api/*', cors())

// Error handler
app.onError((err, c) => {
  console.error(err)
  return c.json({ error: 'Internal Server Error' }, 500)
})

// Health check
app.get('/api/health', (c) => c.json({ status: 'ok' }))

// Routes
app.route('/api', registerRoute)
app.route('/api', webhookRoute)
app.route('/api', rotateRoute)
app.route('/api', streamRoute)

// Export with Durable Object class
export { DeviceConnection }
export default app
```

#### 1.6 Device Registration (`src/routes/register.ts`)

```typescript
import { Hono } from 'hono'
import type { Bindings, RegisterRequest, DeviceRecord } from '../types'

export const registerRoute = new Hono<{ Bindings: Bindings }>()

registerRoute.post('/register', async (c) => {
  const { deviceId, digest, fcmToken, name } = await c.req.json<RegisterRequest>()

  // Validate deviceId is UUID v4 format
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(deviceId)) {
    return c.json({ error: 'Invalid device ID' }, 400)
  }

  // Validate digest is 64-char hex (SHA-256)
  if (!/^[0-9a-f]{64}$/i.test(digest)) {
    return c.json({ error: 'Invalid digest' }, 400)
  }

  const record: DeviceRecord = {
    digest,
    fcmToken,
    name: name ?? null,
    createdAt: Date.now(),
  }

  await c.env.DEVICES.put(`device:${deviceId}`, JSON.stringify(record))

  const baseUrl = new URL(c.req.url).origin
  return c.json({
    webhookUrl: `${baseUrl}/api/webhook/${deviceId}/{your-secret}`,
    streamUrl: `${baseUrl}/api/stream/${deviceId}`,
  })
})
```

#### 1.7 Webhook Handler (`src/routes/webhook.ts`)

```typescript
import { Hono } from 'hono'
import { verifySecret } from '../services/crypto'
import type { Bindings, DeviceRecord, WebhookPayload } from '../types'

export const webhookRoute = new Hono<{ Bindings: Bindings }>()

webhookRoute.post('/webhook/:deviceId/:secret', async (c) => {
  const { deviceId, secret } = c.req.param()

  // Fetch device record
  const raw = await c.env.DEVICES.get(`device:${deviceId}`)
  if (!raw) return c.json({ error: 'Device not found' }, 404)

  const device: DeviceRecord = JSON.parse(raw)

  // Verify secret
  if (!(await verifySecret(secret, device.digest))) {
    return c.json({ error: 'Unauthorized' }, 401)
  }

  // Parse payload from body or query params
  let payload: WebhookPayload
  const contentType = c.req.header('content-type') || ''

  if (contentType.includes('application/json')) {
    payload = await c.req.json<WebhookPayload>()
  } else {
    // Query parameter shorthand
    const title = c.req.query('title')
    if (!title) return c.json({ error: 'title is required' }, 400)
    payload = {
      title,
      body: c.req.query('body') ?? undefined,
      image: c.req.query('image') ?? undefined,
    }
  }

  if (!payload.title) return c.json({ error: 'title is required' }, 400)

  // Forward to Durable Object
  const doId = c.env.DEVICE_CONNECTION.idFromName(deviceId)
  const stub = c.env.DEVICE_CONNECTION.get(doId)
  await stub.fetch(new Request('https://do/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      payload,
      fcmToken: device.fcmToken,
      deviceId,
    }),
  }))

  return c.json({ ok: true })
})
```

#### 1.8 Durable Object — WebSocket + Hibernation (`src/durable/device.ts`)

```typescript
import { DurableObject } from 'cloudflare:workers'
import type { Bindings, BufferedMessage, WebhookPayload } from '../types'
import { sendFcmWakeUp } from '../services/fcm'

const MAX_BUFFER = 50
const BUFFER_TTL_MS = 60 * 60 * 1000 // 1 hour

export class DeviceConnection extends DurableObject<Bindings> {

  // Called when the Worker forwards a WebSocket upgrade request
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)

    if (url.pathname === '/websocket') {
      // WebSocket upgrade
      const pair = new WebSocketPair()
      const [client, server] = Object.values(pair)

      // Accept with Hibernation API
      this.ctx.acceptWebSocket(server)

      return new Response(null, { status: 101, webSocket: client })
    }

    if (url.pathname === '/message') {
      // Incoming webhook message
      const { payload, fcmToken, deviceId } = await request.json() as {
        payload: WebhookPayload
        fcmToken: string
        deviceId: string
      }

      const message: BufferedMessage = {
        id: crypto.randomUUID(),
        payload,
        ts: Date.now(),
      }

      // Try to deliver via active WebSocket
      const websockets = this.ctx.getWebSockets()
      if (websockets.length > 0) {
        for (const ws of websockets) {
          ws.send(JSON.stringify(message))
        }
      } else {
        // No active connection — buffer and send FCM wake-up
        await this.bufferMessage(message)
        await sendFcmWakeUp(
          fcmToken,
          deviceId,
          this.env.FCM_PROJECT_ID,
          this.env.FCM_SERVICE_ACCOUNT_KEY
        )
      }

      return new Response('ok')
    }

    return new Response('Not found', { status: 404 })
  }

  // Hibernation API: called when WS message received from client
  async webSocketMessage(ws: WebSocket, message: string | ArrayBuffer) {
    // Client can send: ping, ack, etc.
    if (message === 'ping') {
      ws.send('pong')
    }
  }

  // Hibernation API: called when WS connection opens (after hibernation wake)
  async webSocketOpen(ws: WebSocket) {
    // Flush buffered messages
    const buffered = await this.getBufferedMessages()
    for (const msg of buffered) {
      ws.send(JSON.stringify(msg))
    }
    await this.clearBuffer()
  }

  // Hibernation API: called when WS closes
  async webSocketClose(ws: WebSocket, code: number, reason: string) {
    ws.close(code, reason)
  }

  // Hibernation API: called on WS error
  async webSocketError(ws: WebSocket, error: unknown) {
    ws.close(1011, 'Unexpected error')
  }

  // --- Buffer management using DO storage ---

  private async bufferMessage(message: BufferedMessage): Promise<void> {
    const buffer = await this.getBufferedMessages()

    // Evict expired messages
    const now = Date.now()
    const active = buffer.filter(m => now - m.ts < BUFFER_TTL_MS)

    // Add new message, cap at MAX_BUFFER
    active.push(message)
    if (active.length > MAX_BUFFER) {
      active.splice(0, active.length - MAX_BUFFER)
    }

    await this.ctx.storage.put('buffer', active)
  }

  private async getBufferedMessages(): Promise<BufferedMessage[]> {
    return (await this.ctx.storage.get<BufferedMessage[]>('buffer')) ?? []
  }

  private async clearBuffer(): Promise<void> {
    await this.ctx.storage.delete('buffer')
  }
}
```

#### 1.9 Stream Route — WebSocket Upgrade (`src/routes/stream.ts`)

```typescript
import { Hono } from 'hono'
import { verifySecret } from '../services/crypto'
import type { Bindings, DeviceRecord } from '../types'

export const streamRoute = new Hono<{ Bindings: Bindings }>()

streamRoute.get('/stream/:deviceId', async (c) => {
  // Auth via Sec-WebSocket-Protocol header (carries secret)
  const secret = c.req.header('sec-websocket-protocol')
  if (!secret) return c.json({ error: 'Missing auth' }, 401)

  const { deviceId } = c.req.param()
  const raw = await c.env.DEVICES.get(`device:${deviceId}`)
  if (!raw) return c.json({ error: 'Device not found' }, 404)

  const device: DeviceRecord = JSON.parse(raw)
  if (!(await verifySecret(secret, device.digest))) {
    return c.json({ error: 'Unauthorized' }, 401)
  }

  // Forward to Durable Object for WebSocket handling
  const doId = c.env.DEVICE_CONNECTION.idFromName(deviceId)
  const stub = c.env.DEVICE_CONNECTION.get(doId)
  return stub.fetch(new Request('https://do/websocket', {
    headers: c.req.raw.headers,
  }))
})
```

#### 1.10 Secret Rotation (`src/routes/rotate.ts`)

```typescript
import { Hono } from 'hono'
import { verifySecret } from '../services/crypto'
import type { Bindings, DeviceRecord, RotateRequest } from '../types'

export const rotateRoute = new Hono<{ Bindings: Bindings }>()

rotateRoute.post('/rotate/:deviceId', async (c) => {
  const { deviceId } = c.req.param()
  const { oldSecret, newDigest, fcmToken } = await c.req.json<RotateRequest>()

  const raw = await c.env.DEVICES.get(`device:${deviceId}`)
  if (!raw) return c.json({ error: 'Device not found' }, 404)

  const device: DeviceRecord = JSON.parse(raw)
  if (!(await verifySecret(oldSecret, device.digest))) {
    return c.json({ error: 'Unauthorized' }, 401)
  }

  // Update digest (and optionally FCM token)
  device.digest = newDigest
  if (fcmToken) device.fcmToken = fcmToken
  await c.env.DEVICES.put(`device:${deviceId}`, JSON.stringify(device))

  return c.json({ ok: true })
})
```

---

### Phase 2: Android App — Core

#### 2.1 Project Setup

- Android Studio project, Kotlin DSL
- Min SDK 26 (Android 8.0)
- Target SDK 35
- Package: `com.brrr.app`

**gradle/libs.versions.toml:**
```toml
[versions]
kotlin = "2.0.0"
compose-bom = "2024.06.00"
room = "2.6.1"
lifecycle = "2.8.0"
navigation = "2.7.7"
okhttp = "4.12.0"
work = "2.9.0"
security-crypto = "1.1.0-alpha06"
firebase-bom = "33.1.0"

[libraries]
# Compose
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "compose-bom" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-ui-tooling-preview = { module = "androidx.compose.ui:ui-tooling-preview" }
compose-ui-tooling = { module = "androidx.compose.ui:ui-tooling" }
activity-compose = { module = "androidx.activity:activity-compose", version = "1.9.0" }
navigation-compose = { module = "androidx.navigation:navigation-compose", version.ref = "navigation" }

# Lifecycle + ViewModel
lifecycle-runtime-compose = { module = "androidx.lifecycle:lifecycle-runtime-compose", version.ref = "lifecycle" }
lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycle" }

# Room
room-runtime = { module = "androidx.room:room-runtime", version.ref = "room" }
room-ktx = { module = "androidx.room:room-ktx", version.ref = "room" }
room-compiler = { module = "androidx.room:room-compiler", version.ref = "room" }

# Network
okhttp = { module = "com.squareup.okhttp3:okhttp", version.ref = "okhttp" }

# Security
security-crypto = { module = "androidx.security:security-crypto", version.ref = "security-crypto" }

# Background
work-runtime = { module = "androidx.work:work-runtime-ktx", version.ref = "work" }

# Firebase (FCM only)
firebase-bom = { module = "com.google.firebase:firebase-bom", version.ref = "firebase-bom" }
firebase-messaging = { module = "com.google.firebase:firebase-messaging-ktx" }

[plugins]
android-application = { id = "com.android.application", version = "8.5.0" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
compose-compiler = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version = "2.0.0-1.0.22" }
google-services = { id = "com.google.gms.google-services", version = "4.4.2" }
```

**app/build.gradle.kts:**
```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.ksp)
    alias(libs.plugins.google.services)
}

android {
    namespace = "com.brrr.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.brrr.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }
}

dependencies {
    // Compose
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.material3)
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling.preview)
    debugImplementation(libs.compose.ui.tooling)
    implementation(libs.activity.compose)
    implementation(libs.navigation.compose)

    // Lifecycle + ViewModel
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)

    // Room
    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)

    // Network
    implementation(libs.okhttp)

    // Security
    implementation(libs.security.crypto)

    // Background
    implementation(libs.work.runtime)

    // Firebase (FCM only)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
}
```

#### 2.2 Crypto Module

**SecretManager.kt**
```kotlin
class SecretManager(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "brrr_secrets",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun getOrCreateDeviceId(): String {
        return prefs.getString("device_id", null)
            ?: UUID.randomUUID().toString().also { prefs.edit().putString("device_id", it).apply() }
    }

    fun generateSecret(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it) }
    }

    fun storeDeviceSecret(secret: String) {
        prefs.edit().putString("device_secret", secret).apply()
    }

    fun getDeviceSecret(): String? = prefs.getString("device_secret", null)

    fun getBackendUrl(): String = prefs.getString("backend_url", DEFAULT_BACKEND_URL) ?: DEFAULT_BACKEND_URL

    fun getWebhookUrl(): String? = prefs.getString("webhook_url", null)
    fun storeWebhookUrl(url: String) { prefs.edit().putString("webhook_url", url).apply() }

    companion object {
        const val DEFAULT_BACKEND_URL = "https://brrr-backend.workers.dev"
    }
}
```

**DigestUtil.kt**
```kotlin
object DigestUtil {
    fun sha256(input: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(input.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
    }
}
```

#### 2.3 WebSocket Client (`network/BrrrWebSocket.kt`)

```kotlin
class BrrrWebSocket(
    private val url: String,
    private val secret: String,
    private val onMessage: (BufferedMessage) -> Unit,
    private val onConnected: () -> Unit,
    private val onDisconnected: () -> Unit,
) {
    private val client = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private var ws: WebSocket? = null
    private var reconnectDelay = 1000L

    fun connect() {
        val request = Request.Builder()
            .url(url)
            .header("Sec-WebSocket-Protocol", secret)
            .build()

        ws = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                reconnectDelay = 1000L  // Reset backoff
                onConnected()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val message = Json.decodeFromString<BufferedMessage>(text)
                onMessage(message)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onDisconnected()
                scheduleReconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onDisconnected()
                scheduleReconnect()
            }
        })
    }

    fun disconnect() {
        ws?.close(1000, "App closing")
        ws = null
    }

    private fun scheduleReconnect() {
        // Exponential backoff: 1s → 2s → 4s → ... → 60s max
        Handler(Looper.getMainLooper()).postDelayed({
            connect()
        }, reconnectDelay)
        reconnectDelay = (reconnectDelay * 2).coerceAtMost(60_000L)
    }
}
```

#### 2.4 FCM Receiver (`service/BrrrFirebaseMessaging.kt`)

```kotlin
class BrrrFirebaseMessaging : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        // This is a wake-up ping — no notification content
        val deviceId = remoteMessage.data["deviceId"] ?: return

        // Start/reconnect the WebSocket service to fetch real messages
        val intent = Intent(this, WebSocketService::class.java).apply {
            action = WebSocketService.ACTION_FCM_WAKE
        }
        startForegroundService(intent)
    }

    override fun onNewToken(token: String) {
        // FCM token refreshed — update backend
        // Use WorkManager to ensure this completes even if app is killed
        val data = workDataOf("fcm_token" to token)
        val request = OneTimeWorkRequestBuilder<TokenUpdateWorker>()
            .setInputData(data)
            .build()
        WorkManager.getInstance(this).enqueue(request)
    }
}
```

#### 2.5 Foreground Service (`service/WebSocketService.kt`)

```kotlin
class WebSocketService : Service() {
    private var brrrWebSocket: BrrrWebSocket? = null
    private lateinit var secretManager: SecretManager
    private lateinit var notificationRepo: NotificationRepository

    override fun onCreate() {
        super.onCreate()
        secretManager = SecretManager(this)
        notificationRepo = NotificationRepository(BrrrDatabase.getInstance(this).notificationDao())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(FOREGROUND_ID, buildPersistentNotification())

        when (intent?.action) {
            ACTION_FCM_WAKE -> {
                // Woken by FCM — reconnect immediately
                brrrWebSocket?.disconnect()
                connectWebSocket()
            }
            else -> {
                // Normal start
                if (brrrWebSocket == null) connectWebSocket()
            }
        }

        return START_STICKY
    }

    private fun connectWebSocket() {
        val deviceId = secretManager.getOrCreateDeviceId()
        val secret = secretManager.getDeviceSecret() ?: return
        val baseUrl = secretManager.getBackendUrl()
        val wsUrl = baseUrl.replace("https://", "wss://") + "/api/stream/$deviceId"

        brrrWebSocket = BrrrWebSocket(
            url = wsUrl,
            secret = secret,
            onMessage = { message -> handleMessage(message) },
            onConnected = { updateNotification("Connected") },
            onDisconnected = { updateNotification("Reconnecting...") },
        )
        brrrWebSocket?.connect()
    }

    private fun handleMessage(message: BufferedMessage) {
        // 1. Show Android notification
        showNotification(message)

        // 2. Save to Room database
        CoroutineScope(Dispatchers.IO).launch {
            notificationRepo.insert(message.toEntity())
        }
    }

    private fun showNotification(message: BufferedMessage) {
        val notification = NotificationCompat.Builder(this, CHANNEL_NOTIFICATIONS)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(message.payload.title)
            .setContentText(message.payload.body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(message.id.hashCode(), notification)
    }

    companion object {
        const val ACTION_FCM_WAKE = "com.brrr.app.FCM_WAKE"
        const val FOREGROUND_ID = 1
        const val CHANNEL_SERVICE = "brrr_service"
        const val CHANNEL_NOTIFICATIONS = "brrr_notifications"
    }
}
```

#### 2.6 Data Layer

**NotificationEntity.kt**
```kotlin
@Entity(tableName = "notifications")
data class NotificationEntity(
    @PrimaryKey val id: String,
    val title: String,
    val body: String?,
    val imageUrl: String?,
    val imagePath: String?,
    val receivedAt: Long,
)
```

**NotificationDao.kt**
```kotlin
@Dao
interface NotificationDao {
    @Query("SELECT * FROM notifications ORDER BY receivedAt DESC")
    fun getAll(): Flow<List<NotificationEntity>>

    @Query("SELECT * FROM notifications ORDER BY receivedAt DESC LIMIT :limit")
    fun getRecent(limit: Int): Flow<List<NotificationEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(notification: NotificationEntity)

    @Delete
    suspend fun delete(notification: NotificationEntity)

    @Query("DELETE FROM notifications WHERE receivedAt < :cutoff")
    suspend fun deleteOlderThan(cutoff: Long)

    @Query("DELETE FROM notifications")
    suspend fun deleteAll()
}
```

**BrrrDatabase.kt**
```kotlin
@Database(entities = [NotificationEntity::class], version = 1)
abstract class BrrrDatabase : RoomDatabase() {
    abstract fun notificationDao(): NotificationDao

    companion object {
        @Volatile private var INSTANCE: BrrrDatabase? = null

        fun getInstance(context: Context): BrrrDatabase {
            return INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context, BrrrDatabase::class.java, "brrr.db")
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
```

#### 2.7 API Client (`network/ApiClient.kt`)

```kotlin
class ApiClient(private val secretManager: SecretManager) {
    private val client = OkHttpClient()
    private val json = Json { ignoreUnknownKeys = true }
    private val baseUrl get() = secretManager.getBackendUrl()

    suspend fun register(deviceId: String, digest: String, fcmToken: String): RegisterResponse {
        val body = json.encodeToString(RegisterRequest(deviceId, digest, fcmToken))
        val request = Request.Builder()
            .url("$baseUrl/api/register")
            .post(body.toRequestBody("application/json".toMediaType()))
            .build()

        return withContext(Dispatchers.IO) {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) throw ApiException(response.code, response.body?.string())
            json.decodeFromString(response.body!!.string())
        }
    }

    suspend fun rotate(deviceId: String, oldSecret: String, newDigest: String, fcmToken: String?) {
        val body = json.encodeToString(RotateRequest(oldSecret, newDigest, fcmToken))
        val request = Request.Builder()
            .url("$baseUrl/api/rotate/$deviceId")
            .post(body.toRequestBody("application/json".toMediaType()))
            .build()

        withContext(Dispatchers.IO) {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) throw ApiException(response.code, response.body?.string())
        }
    }
}
```

---

### Phase 3: Android App — UI (ViewModels + Compose)

#### 3.1 UI State Classes

```kotlin
// Home
data class HomeUiState(
    val webhookUrl: String = "",
    val connectionStatus: ConnectionStatus = ConnectionStatus.Disconnected,
    val recentNotifications: List<NotificationEntity> = emptyList(),
    val isRegistering: Boolean = false,
    val error: String? = null,
)

enum class ConnectionStatus { Connected, Reconnecting, Disconnected }

// History
data class HistoryUiState(
    val notifications: List<NotificationEntity> = emptyList(),
    val isEmpty: Boolean = true,
)

// Settings
data class SettingsUiState(
    val deviceName: String = "",
    val webhookUrl: String = "",
    val isRotating: Boolean = false,
    val rotateSuccess: Boolean = false,
    val error: String? = null,
)
```

#### 3.2 HomeViewModel

```kotlin
class HomeViewModel(
    private val deviceRepository: DeviceRepository,
    private val notificationRepository: NotificationRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        // Load webhook URL
        viewModelScope.launch {
            val url = deviceRepository.getWebhookUrl()
            _uiState.update { it.copy(webhookUrl = url ?: "") }
        }

        // Observe recent notifications
        viewModelScope.launch {
            notificationRepository.getRecent(3).collect { recent ->
                _uiState.update { it.copy(recentNotifications = recent) }
            }
        }
    }

    fun updateConnectionStatus(status: ConnectionStatus) {
        _uiState.update { it.copy(connectionStatus = status) }
    }
}
```

#### 3.3 HomeScreen (Compose)

```kotlin
@Composable
fun HomeScreen(
    viewModel: HomeViewModel = viewModel(),
    modifier: Modifier = Modifier,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val clipboardManager = LocalClipboardManager.current

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        // Connection status
        ConnectionStatusBadge(status = uiState.connectionStatus)

        Spacer(modifier = Modifier.height(24.dp))

        // Webhook URL card
        Text("Your webhook URL", style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(8.dp))

        WebhookUrlCard(
            url = uiState.webhookUrl,
            onCopy = { clipboardManager.setText(AnnotatedString(uiState.webhookUrl)) },
            onShare = { /* share intent */ },
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Try it section
        TryItSection(webhookUrl = uiState.webhookUrl)

        Spacer(modifier = Modifier.height(24.dp))

        // Recent notifications
        if (uiState.recentNotifications.isNotEmpty()) {
            Text("Recent", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            uiState.recentNotifications.forEach { notif ->
                NotificationPreviewItem(notification = notif)
            }
        }
    }
}
```

#### 3.4 Navigation

```kotlin
@Composable
fun BrrrNavHost(modifier: Modifier = Modifier) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = /* ... */,
                    onClick = { navController.navigate("home") },
                    icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                    label = { Text("Home") },
                )
                NavigationBarItem(
                    selected = /* ... */,
                    onClick = { navController.navigate("history") },
                    icon = { Icon(Icons.Default.List, contentDescription = "History") },
                    label = { Text("History") },
                )
                NavigationBarItem(
                    selected = /* ... */,
                    onClick = { navController.navigate("settings") },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                )
            }
        },
        modifier = modifier,
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(innerPadding),
        ) {
            composable("home") { HomeScreen() }
            composable("history") { HistoryScreen() }
            composable("settings") { SettingsScreen() }
        }
    }
}
```

---

### Phase 4: Polish & Edge Cases

#### 4.1 Cleanup Worker

```kotlin
class CleanupWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        val cutoff = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(14)
        BrrrDatabase.getInstance(applicationContext).notificationDao().deleteOlderThan(cutoff)
        return Result.success()
    }
}

// Schedule in BrrrApp.onCreate():
val cleanupRequest = PeriodicWorkRequestBuilder<CleanupWorker>(1, TimeUnit.DAYS).build()
WorkManager.getInstance(this).enqueueUniquePeriodicWork(
    "cleanup", ExistingPeriodicWorkPolicy.KEEP, cleanupRequest
)
```

#### 4.2 Notification Channels (created in BrrrApp.onCreate)

```kotlin
class BrrrApp : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        scheduleCleanupWorker()
    }

    private fun createNotificationChannels() {
        val notifChannel = NotificationChannel(
            "brrr_notifications",
            "Notifications",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply { description = "Webhook notifications" }

        val serviceChannel = NotificationChannel(
            "brrr_service",
            "Connection",
            NotificationManager.IMPORTANCE_LOW,
        ).apply { description = "Background connection status" }

        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannels(listOf(notifChannel, serviceChannel))
    }
}
```

#### 4.3 AndroidManifest.xml Permissions

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />

<application ...>
    <service
        android:name=".service.WebSocketService"
        android:foregroundServiceType="dataSync"
        android:exported="false" />

    <service
        android:name=".service.BrrrFirebaseMessaging"
        android:exported="false">
        <intent-filter>
            <action android:name="com.google.firebase.MESSAGING_EVENT" />
        </intent-filter>
    </service>

    <receiver
        android:name=".receiver.BootReceiver"
        android:exported="true">
        <intent-filter>
            <action android:name="android.intent.action.BOOT_COMPLETED" />
        </intent-filter>
    </receiver>
</application>
```

#### 4.4 First-Run / Onboarding

```kotlin
// In MainActivity.kt
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            BrrrTheme {
                val isRegistered = remember { secretManager.getDeviceSecret() != null }

                if (isRegistered) {
                    BrrrNavHost()
                } else {
                    OnboardingFlow(
                        onComplete = { /* navigate to BrrrNavHost */ }
                    )
                }
            }
        }
    }
}

// OnboardingFlow:
// 1. Request POST_NOTIFICATIONS permission
// 2. Show "Setting up..." progress
// 3. Generate secret, get FCM token, register with backend
// 4. Store webhook URL, start WebSocket service
// 5. Navigate to Home
```

#### 4.5 Reconnection & Battery

- OkHttp handles WebSocket ping/pong automatically (`pingInterval(30, SECONDS)`)
- Exponential backoff: 1s → 2s → 4s → ... → 60s max
- `NetworkCallback` to detect connectivity changes and reconnect immediately
- Boot receiver restarts the foreground service after device reboot
- In-app battery optimization guidance (link to device settings)

#### 4.6 Error States

| Scenario | Behavior |
|---|---|
| No internet | Show "Disconnected" badge, reconnect via NetworkCallback |
| Backend down | Exponential backoff reconnection |
| Invalid secret | Show error, prompt to re-register |
| POST_NOTIFICATIONS denied | Show guidance to enable in settings |
| FCM token refresh | WorkManager task updates backend |
| OEM kills service | FCM wake-up restarts it on next webhook |

---

## 3. API Contract Summary

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/health` | GET | None | Health check |
| `/api/register` | POST | None | Register a new device |
| `/api/webhook/:deviceId/:secret` | POST | Secret in URL | Send notification to device |
| `/api/stream/:deviceId` | GET (WS) | Secret in WS protocol header | WebSocket connection |
| `/api/rotate/:deviceId` | POST | Old secret in body | Rotate webhook secret |

## 4. Data Models

### Backend KV Entries

```
device:{deviceId} → {
  digest: string,
  fcmToken: string,
  name: string | null,
  createdAt: number
}
```

### Backend DO Storage (per device)

```
buffer → BufferedMessage[]   // up to 50 messages, 1hr TTL
```

### Android Room Schema

```sql
CREATE TABLE notifications (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  body TEXT,
  imageUrl TEXT,
  imagePath TEXT,
  receivedAt INTEGER NOT NULL
);

CREATE INDEX idx_notifications_receivedAt ON notifications(receivedAt);
```

### Android EncryptedSharedPreferences

```
device_id       → UUID string
device_secret   → 64-char hex string
webhook_url     → full URL string
backend_url     → string (default: https://brrr-backend.workers.dev)
device_name     → string
```

## 5. Testing Strategy

### Backend
- Unit tests: digest verification, constant-time comparison
- Integration tests: webhook → DO → WebSocket delivery
- Integration tests: webhook → DO → FCM wake-up (mock FCM)
- Test message buffering: offline device reconnects and receives
- Test secret rotation: old URL fails, new URL works
- Test FCM token refresh flow

### Android
- Unit tests: `DigestUtil`, `SecretManager`
- Unit tests: WebSocket message parsing
- Instrumented tests: Room DAO operations
- UI tests: navigation, onboarding flow (Compose testing)
- Manual tests: foreground service lifecycle, FCM wake-up, Doze behavior

## 6. Deployment

### Backend
```bash
cd backend
npm install
npm run dev                              # Local dev
wrangler secret put FCM_SERVICE_ACCOUNT_KEY  # One-time setup
wrangler secret put FCM_PROJECT_ID           # One-time setup
wrangler deploy                          # Production
```

### Android
- Create Firebase project, download `google-services.json`
- Standard Gradle build: `./gradlew assembleRelease`
- Sign with release keystore
- Distribute via Google Play
- F-Droid possible as a future variant (without FCM, WebSocket-only)

## 7. Build Order (What to Do First)

1. **Backend: scaffold + crypto + register endpoint** — get a deployable worker
2. **Backend: webhook + DO (WebSocket only, no FCM yet)** — end-to-end message flow
3. **Android: project setup + crypto + registration** — device can register
4. **Android: WebSocket service** — can receive messages in foreground
5. **Backend: FCM integration** — wake-up pings
6. **Android: FCM receiver + wake-up reconnect** — background delivery works
7. **Android: UI screens (Home, History, Settings)** — user-facing app
8. **Android: onboarding flow** — first-run experience
9. **Polish: error handling, reconnection, battery guidance**
10. **Testing + deployment**
