# Gnani API Notes

Verified facts from Gnani Vachana API documentation. If actual docs differ from this file, the actual docs take precedence — update this file and note the deviation.

---

## STT — Prisma v3.0

**Endpoint:** `wss://api.vachana.ai/stt/v3/stream`

### Connection / Upgrade Headers

| Header | Value / Notes |
|---|---|
| `x-api-key-id` | Your Gnani API key |
| `model` | `prisma-v3.0` |
| `language_code` | e.g. `hi-IN,en-IN` or `indic-auto` |
| `x-sample-rate` | `8000` (for telephony) |
| `x-vad-threshold` | `0.7` |
| `x-min-speech-ms` | `200` |
| `x-min-silence-ms` | `500` |
| `keyterms` | Optional comma-separated key terms for boosting |
| `format` | `verbatim` \| `transcribe` \| `codemix` \| `transliterate` |

### Audio Format

- **Encoding:** Raw PCM, signed 16-bit little-endian (s16le), mono
- **Sample rate:** 8000 Hz (telephony)
- **Frame size:** Exactly **1024 bytes** per frame
- **Cadence:** Real-time — send each frame at the correct wall-clock interval (64 ms at 8 kHz)
- **DO NOT** batch frames or send ahead of real time

### Control Frames (JSON messages)

| Frame | Purpose |
|---|---|
| `{ "type": "update_settings", "settings": { ... } }` | Update VAD/format settings mid-session |
| `{ "type": "commit" }` | Signal end of utterance / flush |

### Session Limits

- Maximum session length: **15 minutes**
- Concurrent session cap: check current quota with Gnani support

### Proxy Rule

> **Browsers cannot set WebSocket upgrade headers.** All STT connections from the frontend must be proxied through the API backend (the API opens the WS to Gnani, the browser connects to the API's WS endpoint).

---

## TTS — Timbre

**Endpoint:** `wss://api.vachana.ai/api/v1/tts`

**Header:** `X-API-Key-ID: <your-api-key>`

### Send (JSON)

```json
{
  "text": "Namaste, aapki booking pakki ho gayi",
  "voice": "<voice-id>",
  "model": "timbre-v3.0",
  "language": "hi-en",
  "speed": 1.0,
  "audio_config": {
    "sample_rate": 8000,
    "container": "raw",
    "encoding": "linear_pcm"
  }
}
```

**Model options:** `timbre-v2.5` | `timbre-v3.0`

**Container options:** `raw` | `wav` | `mulaw` | `alaw`

**Language codes for Hinglish:** `hi-en`

### Receive

- Audio arrives as **base64-encoded chunks** in JSON messages
- A `"complete"` message signals end of the audio stream

### Important Content Rules

- Write **numbers and amounts as spoken words**, not digits  
  ✅ `"do sau rupaye"` ❌ `"200 rupaye"`
- Avoid punctuation that might be read aloud incorrectly

---

## STT REST API — Prisma v3.0

**Endpoint:** `POST https://api.vachana.ai/stt/v3`  
**Header:** `x-api-key-id: <your-api-key>`  
**Content-Type:** `multipart/form-data`

### Form Fields (Multipart)

| Field | Type | Required | Description / Verified Value |
|---|---|---|---|
| `audio_file` | File | Yes | Audio file binary (WAV, MP3, OGG, FLAC, AAC, M4A). 8–44.1 kHz, max 30 s. |
| `model` | string | Yes | `prisma-v3.0` |
| `language_code` | string | Yes | e.g. `indic-auto` (Auto-LID) or `hi-IN` / `hi-IN,en-IN` |
| `format` | string | No | `codemix` \| `verbatim` \| `transcribe` \| `transliterate` |
| `keyterms` | string | No | Optional comma-separated boost terms (e.g. `geyser,leak,plumber`) |

### Successful Response (JSON, HTTP 200)

```json
{
  "transcript": "Mera geyser leak kar raha hai",
  "detected_language_code": "hi-IN",
  "processing_time": 0.45
}
```

### Error Responses & Status Codes

- `401 Unauthorized`: `MISSING/INVALID_API_KEY`
- `402 Payment Required`: `insufficient credit`
- `403 Forbidden`: `SCOPE_NOT_ALLOWED`
- `429 Too Many Requests`: `RATE_LIMITED` ("Only 1 active request is allowed at a time")
- `500 / 503 Internal Server Error`: Gnani service or gateway error

---

## TTS REST API — Timbre v2.5 / v3.0

**Endpoint:** `POST https://api.vachana.ai/api/v1/tts/inference`  
**Header:** `X-API-Key-ID: <your-api-key>`, `Content-Type: application/json`

### JSON Request Body

```json
{
  "text": "Namaste, main Pakka ki digital sahayak bol rahi hoon.",
  "voice": "Poorvi",
  "model": "timbre-v2.5",
  "language": "hi-en",
  "speed": 1.0,
  "audio_config": {
    "sample_rate": 16000,
    "num_channels": 1,
    "sample_width": 2,
    "encoding": "linear_pcm",
    "container": "wav"
  }
}
```

### Response

- Binary WAV audio bytes (`Content-Type: audio/wav`).

---

- **Deployment:** Self-hosted via vLLM (separate process)
- **Base URL:** Configurable via `EVON_BASE_URL` env var (default: `http://localhost:8001/v1`)
- **OpenAI-compatible API** (via vLLM)
- **Allowed uses:** Extraction, classification, slot-filling from transcripts
- **Prohibited uses:** Real-time call-flow control, telephony decisions

### Python SDK Note

The `gnani-vachana` Python SDK exists but **does not expose VAD tuning parameters for STT**. Therefore, use **raw WebSockets** (the `websockets` library) for STT integration, not the SDK.

---

## Open Questions / To Verify

- [ ] Exact Exotel Voicebot WebSocket frame format (bidirectional audio) — read Exotel docs in Phase 1
- [ ] Voice IDs available in Timbre for male/female Hinglish voices
- [ ] Concurrent STT session cap for our quota tier
- [ ] Whether `indic-auto` language_code works reliably for Hinglish (may need `hi-IN,en-IN`)
- [ ] TTS `language` field: verify accepted values for Hinglish (`hi-en` vs `hi-IN`)

