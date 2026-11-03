# Exotel Telephony & WebSocket Protocol Notes

Source: [Exotel AgentStream WebSocket Protocol](https://developer.exotel.com/docs/agentstream/websocket-protocol) and Exotel Getting Started guides.

---

## 1. Overview
Exotel Voicebot applet connects to our public `wss://` endpoint (`PUBLIC_WSS_URL/ws/exotel`) and establishes a full-duplex bidirectional audio stream over WebSocket.

- **Audio encoding:** Raw PCM linear16, signed, little-endian, mono (`s16le`).
- **Sample rate:** Default **8000 Hz** (telephony standard). Also supports 16000 Hz and 24000 Hz.
- **Session limit:** Maximum call duration: 60 minutes.
- **Transport:** WebSocket payload is JSON-formatted; audio is base64-encoded.

---

## 2. Inbound Events (Exotel → Our API)

### `connected`
Sent immediately after the WebSocket handshake completes.
```json
{
  "event": "connected",
  "protocol": "Call",
  "version": "1.0.0"
}
```

### `start`
Provides call metadata and media stream identifier.
```json
{
  "event": "start",
  "sequence_number": "1",
  "stream_sid": "stream_12345678",
  "call_sid": "call_abcdef12345",
  "account_sid": "exotel_acc_sid",
  "from": "+919876543210",
  "to": "+918000012345",
  "call_type": "inbound",
  "custom_parameters": {},
  "media_format": {
    "encoding": "audio/x-l16",
    "sample_rate": 8000,
    "channels": 1
  }
}
```

### `media`
Carries caller audio chunks every ~100 ms (~1600 bytes at 8 kHz / 16-bit linear PCM).
```json
{
  "event": "media",
  "sequence_number": "2",
  "stream_sid": "stream_12345678",
  "media": {
    "chunk": "1",
    "timestamp": "100",
    "payload": "<base64-encoded-pcm>"
  }
}
```

### `mark`
Sent when a marker we requested has finished playing to the caller.
```json
{
  "event": "mark",
  "sequence_number": "3",
  "stream_sid": "stream_12345678",
  "mark": {
    "name": "greeting_complete"
  }
}
```

### `dtmf`
Dual-tone multi-frequency keypress events.
```json
{
  "event": "dtmf",
  "stream_sid": "stream_12345678",
  "dtmf": {
    "digit": "1"
  }
}
```

### `stop`
Sent when the call ends or stream is closed.
```json
{
  "event": "stop",
  "stream_sid": "stream_12345678",
  "call_sid": "call_abcdef12345",
  "stop": {
    "reason": "callended"
  }
}
```

---

## 3. Outbound Events (Our API → Exotel)

### `media`
Streams assistant audio to the caller.
```json
{
  "event": "media",
  "stream_sid": "stream_12345678",
  "media": {
    "payload": "<base64-encoded-pcm>"
  }
}
```
**Constraints:**
- Chunk size must be between **3,200 bytes** and **100,000 bytes**.
- Chunk size MUST be an **exact multiple of 320 bytes** (at 8 kHz, 320 bytes = 20 ms of audio; 3,200 bytes = 200 ms).

### `mark`
Place a marker in the playback queue to be notified when audio finishes playing.
```json
{
  "event": "mark",
  "stream_sid": "stream_12345678",
  "mark": {
    "name": "playback_chunk_1"
  }
}
```

### `clear` (Barge-in / Interruption)
Flushes Exotel's internal playback buffer immediately when the caller speaks while the assistant is speaking.
```json
{
  "event": "clear",
  "stream_sid": "stream_12345678"
}
```

---

## 4. Exotel Outbound Call API
To initiate outbound calls (for technician dispatch in Phase 6 or testing):
- **Endpoint:** `POST https://api.in.exotel.com/v1/Accounts/{SID}/Calls/connect`
- **Auth:** HTTP Basic Auth (`EXOTEL_API_KEY : EXOTEL_API_TOKEN`)
- **Parameters:**
  - `From`: Destination phone number
  - `CallerId`: Your virtual ExoPhone number
  - `StreamUrl`: `wss://your-public-url.ngrok-free.app/ws/exotel`
  - `StreamType`: `bidirectional`

---

## 5. Exotel Dashboard Applet Configuration Steps
1. Log in to your Exotel dashboard at `https://my.exotel.com/`.
2. Navigate to **App Bazaar** → **Create App**.
3. Drag and drop the **Stream & Voicebot** applet.
4. Set **Stream Type** to `Bidirectional`.
5. Enter **Stream URL**: `wss://<your-public-domain>/ws/exotel`.
6. Select audio format `PCM 8000 Hz, 16-bit linear`.
7. Link your virtual ExoPhone number to this Flow.

