/**
 * Client-side 16-bit Linear PCM Mono WAV recorder & Web Audio visualizer.
 * Supports auto-silence detection and produces compliant WAV blobs for Gnani STT REST.
 */

export interface AudioRecorderOptions {
  sampleRate?: number;
  silenceThresholdMs?: number;
  silenceRmsFloor?: number;
  maxDurationMs?: number;
  onRmsUpdate?: (rms: number) => void;
  onSilenceTimeout?: () => void;
  onMaxDuration?: () => void;
}

export class BrowserAudioRecorder {
  private audioCtx: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private analyserNode: AnalyserNode | null = null;
  private pcmChunks: Float32Array[] = [];
  private totalSamples = 0;
  private isRecording = false;
  private silenceTimer: number | null = null;
  private maxDurationTimer: number | null = null;
  private lastSoundTimestamp = 0;

  constructor(private options: AudioRecorderOptions = {}) {
    this.options.sampleRate = options.sampleRate ?? 16000;
    this.options.silenceThresholdMs = options.silenceThresholdMs ?? 1300;
    this.options.silenceRmsFloor = options.silenceRmsFloor ?? 0.015;
    this.options.maxDurationMs = options.maxDurationMs ?? 30000;
  }

  async start(): Promise<void> {
    if (this.isRecording) return;

    this.pcmChunks = [];
    this.totalSamples = 0;
    this.isRecording = true;

    // Request microphone access (mono preferred)
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.audioCtx = new AudioContextClass();

    this.sourceNode = this.audioCtx.createMediaStreamSource(this.mediaStream);
    this.analyserNode = this.audioCtx.createAnalyser();
    this.analyserNode.fftSize = 256;

    // ScriptProcessor to capture raw PCM samples
    this.processorNode = this.audioCtx.createScriptProcessor(4096, 1, 1);

    this.lastSoundTimestamp = Date.now();

    this.processorNode.onaudioprocess = (e: AudioProcessingEvent) => {
      if (!this.isRecording) return;
      const input = e.inputBuffer.getChannelData(0);
      const chunk = new Float32Array(input.length);
      chunk.set(input);
      this.pcmChunks.push(chunk);
      this.totalSamples += input.length;

      // Compute RMS
      let sumSquares = 0;
      for (let i = 0; i < input.length; i++) {
        sumSquares += input[i] * input[i];
      }
      const rms = Math.sqrt(sumSquares / input.length);
      this.options.onRmsUpdate?.(rms);

      const now = Date.now();
      if (rms >= (this.options.silenceRmsFloor ?? 0.015)) {
        this.lastSoundTimestamp = now;
      } else {
        // Only trigger silence detection after at least 1.0s of recording
        const durationSoFar = (this.totalSamples / (this.audioCtx?.sampleRate || 16000)) * 1000;
        if (
          durationSoFar > 1000 &&
          now - this.lastSoundTimestamp >= (this.options.silenceThresholdMs ?? 1300)
        ) {
          this.options.onSilenceTimeout?.();
        }
      }
    };

    this.sourceNode.connect(this.analyserNode);
    this.analyserNode.connect(this.processorNode);
    // Connect to destination to keep ScriptProcessor alive in Chromium/Safari
    this.processorNode.connect(this.audioCtx.destination);

    // Max duration timeout
    this.maxDurationTimer = window.setTimeout(() => {
      if (this.isRecording) {
        this.options.onMaxDuration?.();
      }
    }, this.options.maxDurationMs);
  }

  getAnalyser(): AnalyserNode | null {
    return this.analyserNode;
  }

  async stop(): Promise<Blob> {
    this.isRecording = false;

    if (this.silenceTimer) {
      window.clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    if (this.maxDurationTimer) {
      window.clearTimeout(this.maxDurationTimer);
      this.maxDurationTimer = null;
    }

    const nativeSampleRate = this.audioCtx?.sampleRate || 44100;
    const targetSampleRate = this.options.sampleRate || 16000;

    // Disconnect audio nodes
    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode.onaudioprocess = null;
    }
    if (this.analyserNode) {
      this.analyserNode.disconnect();
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
    }
    if (this.audioCtx && this.audioCtx.state !== "closed") {
      await this.audioCtx.close();
    }

    // Merge captured chunks
    const merged = new Float32Array(this.totalSamples);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Resample if necessary to 16000 Hz
    const resampled = this.resampleAudio(merged, nativeSampleRate, targetSampleRate);

    // Encode to 16-bit Mono WAV
    return this.encodeWav(resampled, targetSampleRate);
  }

  cancel(): void {
    this.isRecording = false;
    if (this.silenceTimer) window.clearTimeout(this.silenceTimer);
    if (this.maxDurationTimer) window.clearTimeout(this.maxDurationTimer);
    if (this.processorNode) this.processorNode.disconnect();
    if (this.mediaStream) this.mediaStream.getTracks().forEach((t) => t.stop());
    if (this.audioCtx && this.audioCtx.state !== "closed") this.audioCtx.close();
  }

  private resampleAudio(
    input: Float32Array,
    inputRate: number,
    outputRate: number
  ): Float32Array {
    if (inputRate === outputRate || input.length === 0) return input;
    const ratio = inputRate / outputRate;
    const newLength = Math.round(input.length / ratio);
    const result = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
      const srcIndex = i * ratio;
      const index0 = Math.floor(srcIndex);
      const index1 = Math.min(index0 + 1, input.length - 1);
      const frac = srcIndex - index0;
      result[i] = input[index0] * (1 - frac) + input[index1] * frac;
    }
    return result;
  }

  private encodeWav(samples: Float32Array, sampleRate: number): Blob {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (view: DataView, offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    // RIFF chunk descriptor
    writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, "WAVE");

    // fmt sub-chunk
    writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 = PCM)
    view.setUint16(22, 1, true); // NumChannels (1 = Mono)
    view.setUint32(24, sampleRate, true); // SampleRate
    view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * 1 * 2)
    view.setUint16(32, 2, true); // BlockAlign (1 * 2)
    view.setUint16(34, 16, true); // BitsPerSample (16 bits)

    // data sub-chunk
    writeString(view, 36, "data");
    view.setUint32(40, samples.length * 2, true);

    // Write PCM 16-bit samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }

    return new Blob([view], { type: "audio/wav" });
  }
}

