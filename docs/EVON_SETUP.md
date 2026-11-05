# Evon v3.3 Setup & vLLM Deployment Guide

> **Model Card Naming & Hardware Requirements**:  
> The Great Indian AI Internship challenge references the model as `gnani/gnani-evon-v3.3`.  
> On Hugging Face, the official checkpoint is published as **`gnani/gnani-evon-v3.3-30B-A3B`**. When launching vLLM or downloading weights, use `gnani/gnani-evon-v3.3-30B-A3B`.  
> The official model card lists **NVIDIA H100 80GB, H200, and A100 (80GB-class)**. Hardware with less VRAM (such as 40GB GPUs) is insufficient for single-GPU serving without quantization.

> [!IMPORTANT]
> **GPU Execution Status (Truth in Reporting)**:  
> **None of this was run on a GPU during our local evaluation.** All Evon benchmarks reported in `reports/extractor_comparison.json` and in this repository were run against the local mock engine (`mock_evon.py`) or rule-based fallback. Live vLLM execution on GPU hardware is marked as **PENDING USER**.

---

## 1. Architectural Role in Pakka

In accordance with Pakka Agent Safety Rules:
- **Evon v3.3 is strictly an intent and entity slot extractor.**
- Evon **never** generates conversational replies, drives dialog flow, or speaks directly to callers.
- All conversational utterances, bargaining floor policies, safety emergency halts, and confirmations remain **100% deterministic** inside `BookingFSM`, `DispatchFSM`, and `CollectionFSM`.

---

## 2. Serving Evon with vLLM on NVIDIA H100 80GB, H200, or A100 (80GB-class)

### Prerequisites
- GPU: 1× NVIDIA H100 (80GB), NVIDIA H200 (141GB), or NVIDIA A100 (80GB SXM/PCIe)
- Driver: CUDA 12.2+
- Python 3.10+ / Docker with vLLM

### Recommended vLLM CLI Command

```bash
# Install vLLM
pip install vllm>=0.6.0

# Launch OpenAI-compatible API server on port 8001
python -m vllm.entrypoints.openai.api_server \
  --model gnani/gnani-evon-v3.3-30B-A3B \
  --served-model-name model \
  --port 8001 \
  --host 0.0.0.0 \
  --max-model-len 8192 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.92 \
  --trust-remote-code \
  --dtype bfloat16 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser nano_v3
```

> **Note on Flags**:
> - `--served-model-name model`: Sets alias to `model` so that `EVON_MODEL=model` in config matches seamlessly.
> - `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser nano_v3`: Optional flags supported by the Evon model card for advanced tool call and reasoning parsing.

---

## 3. Pakka Backend Configuration

Configure `apps/api/.env` (or environment variables) to point to the vLLM instance:

```env
# Extractor choice: 'rules' (default), 'evon', or 'hybrid'
EXTRACTOR=hybrid

# Evon OpenAI-compatible endpoint
EVON_BASE_URL=http://localhost:8001/v1
EVON_MODEL=model
EVON_TIMEOUT_SECONDS=2.0
```

### Extractor Modes:
1. **`rules`** *(Default)*: Pure deterministic regex engine. Runs in < 2ms with zero external network overhead.
2. **`evon`**: Calls Evon v3.3 on every turn with structured JSON schema. If the vLLM server is unreachable, throws an error, or exceeds 2.0s timeout, it **instantly falls back** to `RuleBasedExtractor`.
3. **`hybrid`**: First evaluates deterministic rules. If the problem is recognized with high confidence, returns in < 2ms. Evon is invoked **only** if the problem is unrecognized or required slots remain empty after caller speech.

---

## 4. Connectivity Probe

Test your live or local Evon deployment using the automated probe script:

```bash
python scripts/evon_probe.py --url http://localhost:8001/v1
```

The probe validates:
1. HTTP connectivity and model list (`GET /v1/models`).
2. Structured extraction parsing with temperature `0.6`, `top_p: 0.95`, and `enable_thinking: false`.
3. Round-trip inference latency (target < 500ms on A100/H100).
