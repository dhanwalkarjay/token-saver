# TokenSaver Enterprise 🚀

> **Cut your LLM API costs by 50–80% without changing a single line of code.**

TokenSaver is an intelligent LLM middleware proxy that automatically applies **semantic caching**, **intelligent model routing**, and **context compression** to every AI request — deployed entirely inside your own infrastructure.

---

## ✨ Key Features

| Feature | How It Works | Typical Savings |
|---|---|---|
| **Semantic Cache** | L1 exact + L2 vector similarity (cosine ≥ 0.85) | 15–70% fewer API calls |
| **Model Router** | Complexity classifier → Tier 1/2/3 selection | 40–70% cost reduction |
| **Context Compressor** | History summarization + token pruning | 15–30% token reduction |
| **Zero Code Changes** | Just change your `base_url` — nothing else | Instant activation |

---

## ⚡ Quickstart (5 Minutes)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- At least one LLM API key (OpenAI, Anthropic, Google, etc.)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/tokensaver
cd tokensaver
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
MASTER_API_KEY=ts-master-your-secret-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start everything

```bash
docker compose up -d
```

This starts:
- `http://localhost:8000` — TokenSaver Proxy (OpenAI-compatible API)
- `http://localhost:3000` — Analytics Dashboard
- Redis Stack (cache) on port 6379
- PostgreSQL (analytics) on port 5432

**First run takes 2–3 minutes** to download the embedding model (~90MB). Subsequent starts are instant.

### 3. Point your app at TokenSaver

```python
# Before (standard OpenAI)
from openai import OpenAI
client = OpenAI(api_key="sk-your-openai-key")

# After (TokenSaver — zero other changes)
from openai import OpenAI
client = OpenAI(
    api_key="ts-master-your-secret-key",  # Your TokenSaver key
    base_url="http://localhost:8000/v1"    # TokenSaver proxy
)

# Everything else is identical!
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 4. See your savings

Open `http://localhost:3000` — the dashboard shows real-time cost savings, cache hit rates, and model routing statistics.

---

## 🔌 Integration Examples

### LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="ts-master-your-secret-key",
    model_name="gpt-4o"
)
```

### LlamaIndex
```python
from llama_index.llms.openai import OpenAI

llm = OpenAI(
    api_base="http://localhost:8000/v1",
    api_key="ts-master-your-secret-key",
    model="gpt-4o"
)
```

### Direct HTTP
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ts-master-your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "What is 2+2?"}]
  }'
```

---

## 🎛️ Control Headers

Fine-tune behavior per-request with headers:

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    extra_headers={
        "X-TokenSaver-Cache": "enabled",    # enabled | disabled | force-miss
        "X-TokenSaver-Route": "auto",        # auto | cheap | balanced | premium | disabled
        "X-TokenSaver-Compress": "enabled",  # enabled | disabled
    }
)
```

---

## 📊 Response Headers

Every response includes savings metadata:

```
X-TokenSaver-Cache-Hit: true
X-TokenSaver-Cache-Level: L2           # L1 (exact) | L2 (semantic) | MISS
X-TokenSaver-Model-Requested: gpt-4o
X-TokenSaver-Model-Used: gpt-4o-mini   # Routed to cheaper model
X-TokenSaver-Cost-USD: 0.0023
X-TokenSaver-Savings-USD: 0.0187
X-TokenSaver-Savings-Percent: 89.05
```

---

## 🏗️ Architecture

```
Your App → TokenSaver Proxy → LLM Provider
              │
              ├─ L1 Cache (exact match, <1ms)
              ├─ L2 Cache (semantic, 2-5ms)
              ├─ Complexity Classifier (<5ms)
              ├─ Model Router (Tier 1/2/3)
              ├─ Context Compressor
              └─ Cost Tracker → Dashboard
```

**Data sovereignty**: Everything runs in your infrastructure. No data leaves your environment.

---

## 🔑 Team Management

### Create a team
```bash
curl -X POST http://localhost:8000/v1/teams \
  -H "Authorization: Bearer ts-master-your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Search Team",
    "tier_limit": 2,
    "monthly_budget_usd": 5000
  }'

# Returns: {"team_id": "team-abc123", "api_key": "ts-team-abc123-xxxx"}
```

Give each team their own API key. Track spending per team in the dashboard.

---

## 📡 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/v1/chat/completions` | POST | OpenAI-compatible chat (main endpoint) |
| `/v1/embeddings` | POST | Generate embeddings |
| `/v1/models` | GET | List all supported models + pricing |
| `/health` | GET | Health check |
| `/v1/stats` | GET | Global savings stats |
| `/v1/stats/teams/{id}` | GET | Per-team stats |
| `/v1/teams` | POST/GET | Create/list teams |
| `/v1/cache` | DELETE | Flush cache (admin) |
| `/docs` | GET | Interactive API documentation |

---

## 🌡️ Model Tiers

| Tier | When Used | Models | Cost |
|---|---|---|---|
| **Tier 1 (Cheap)** | Simple tasks, <200 tokens | GPT-4o-mini, Claude Haiku, Gemini Flash | ~$0.15/1M tokens |
| **Tier 2 (Balanced)** | Moderate tasks, 200–1000 tokens | GPT-4o, Claude Sonnet, Gemini Pro | ~$2.50/1M tokens |
| **Tier 3 (Premium)** | Complex tasks, >1000 tokens | o1, Claude Opus, Gemini Ultra | ~$15.00/1M tokens |

---

## 🏢 Supported LLM Providers

- ✅ OpenAI (GPT-4o, GPT-4o-mini, o1, o1-mini)
- ✅ Anthropic (Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Opus)
- ✅ Google (Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini Ultra)
- ✅ Mistral (Mistral Large, Mistral Small)
- ✅ AWS Bedrock (all supported models)
- ✅ Azure OpenAI Service
- ✅ Cohere

---

## 🛡️ Security

- All connections use TLS 1.3
- API keys never logged or stored in plaintext
- Cache entries encrypted with AES-256-GCM
- Bring Your Own Key (BYOK) support for enterprise deployments
- Full audit log of every request

---

## 📈 Monitoring

The dashboard at `http://localhost:3000` shows:
- Real-time cost savings vs. baseline
- Cache hit rates (L1 and L2 separately)
- Model routing distribution
- Per-team cost chargeback
- Request history and audit log

---

## 🚀 Production Deployment

For production deployment with Kubernetes (Helm):
```bash
helm install tokensaver ./deploy/helm \
  --set proxy.masterApiKey=ts-master-your-prod-key \
  --set proxy.openaiApiKey=sk-... \
  --set redis.password=your-redis-password
```

See [deploy/helm/README.md](deploy/helm/README.md) for full configuration options.

---

## 📄 License

TokenSaver Core (this repo) is open-source under the MIT License.
Enterprise features (BYOK, SSO, RBAC, SOC 2 compliance tools) are available under a commercial license.

---

Built with ❤️ for engineering teams who hate paying more than they should for AI.
