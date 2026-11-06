# Gnani API Notes

Verified facts from Gnani Vachana API documentation (https://docs.gnani.ai/api/TTS/tts-inference).
All parameters and headers here reflect the exact production REST and WebSocket contracts.

---

## 1. STT REST API — Prisma v3.0

**Endpoint:** `POST https://api.vachana.ai/stt/v3`  
**Header:** `X-API-Key-ID: <your-api-key>`  
**Content-Type:** `multipart/form-data`

### Form Fields (Multipart)

| Field | Type | Required | Description / Verified Value |
|---|---|---|---|
| `audio_file` | File | Yes | Audio file binary (16-bit linear PCM WAV, 8000–48000 Hz, mono). |
| `model` | string | Yes | `prisma-v3.0` |
| `language_code` | string | Yes | `hi-IN` \| `indic-auto` \| `hi-IN,en-IN` |
| `format` | string | No | `codemix` \| `verbatim` \| `transcribe` \| `transliterate` |
| `keyterms` | string | No | Optional comma-separated boost terms (e.g. `geyser,leak,plumber`) |

### Successful Response (JSON, HTTP 200)

```json
{
  "success": true,
  "request_id": "req_stt_0192abc",
  "transcript": "नमस्ते, मैं पाक्का की digital सहायक बोल रही हूँ।",
  "model": "prisma-v3.0",
  "processing_time": 0.124,
  "end_to_end_latency": 0.380,
  "detected_language_code": "hi-IN"
}
```

### Error Responses & Status Codes

- `401 Unauthorized`: Invalid or missing `X-API-Key-ID`
- `402 Payment Required`: Insufficient account credits
- `403 Forbidden`: Scope or model not permitted for key
- `429 Too Many Requests`: Rate limit reached ("Only 1 active request is allowed at a time")
- `5xx Server Error`: Gnani internal service or gateway error

---

## 2. TTS REST API — Timbre v2.5 / v3.0

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

### Request Parameters

| Parameter | Type | Required | Description / Verified Value |
|---|---|---|---|
| `text` | string | Yes | Text to synthesize. Numbers should be written as spoken words. |
| `voice` | string | Yes | e.g. `Poorvi` |
| `model` | string | Yes | `timbre-v2.5` \| `timbre-v3.0` |
| `language` | string | Yes | `hi-en` (Hinglish) \| `hi-IN` |
| `speed` | float | Yes | `1.0` (range 0.5–2.0) |
| `audio_config` | object | Yes | Audio format configuration object |
| `audio_config.sample_rate` | int | Yes | `8000` (telephony) \| `16000` (browser voice) |
| `audio_config.num_channels` | int | Yes | `1` (mono) |
| `audio_config.sample_width` | int | Yes | `2` (16-bit linear PCM) |
| `audio_config.encoding` | string | Yes | `linear_pcm` |
| `audio_config.container` | string | Yes | `wav` \| `raw` |

### Response

- **Returns BINARY audio** (raw audio file bytes, `Content-Type: audio/wav`), NOT base64-encoded strings or JSON envelopes.
- On HTTP 200, response body is the complete WAV binary.

---

## 3. Realtime Telephony WebSockets (Exotel Bridge)

### STT Streaming
**Endpoint:** `wss://api.vachana.ai/stt/v3/stream`  
**Upgrade Headers:** `x-api-key-id`, `model: prisma-v3.0`, `language_code: hi-IN`, `x-sample-rate: 8000`, `x-vad-threshold: 0.7`  
**Payloads:** Raw binary PCM chunks of 1024 bytes every 64ms (8 kHz mono 16-bit).

### TTS Streaming
**Endpoint:** `wss://api.vachana.ai/api/v1/tts`  
**Upgrade Header:** `X-API-Key-ID`  
**Send:** JSON configuration and phrase text  
**Receive:** Base64 audio chunks in JSON streaming protocol with final `"complete"` sentinel.

---

## 4. Evon v3.3 (Extraction Only)

- **Endpoint:** Configurable OpenAI-compatible endpoint (vLLM `/v1/chat/completions`)
- **Role:** Post-transcript slot extraction and classification fallback. Zero audio or telephony control.
