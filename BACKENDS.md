# LLM Backend Guide

Quick reference for all supported LLM backends.

## Backends at a Glance

| Backend | Type | Setup | Cost | Speed | Quality |
|---------|------|-------|------|-------|---------|
| **Ollama** | Local | Complex | Free | Slow (CPU) | Good |
| **LM Studio** | Local | Medium | Free | Fast (GPU) | Good |
| **NVIDIA NIM** | Cloud API | Easy | Free tier | Fast | Excellent |
| **Google Gemini** | Cloud API | Easy | Free tier | Very Fast | Excellent |

## 1. Ollama (Local)

**Best for:** Full control, privacy, offline

### Setup
```bash
# Install from https://ollama.ai
ollama serve

# In another terminal, pull a model
ollama pull qwen2.5:7b
```

### Configuration
```bash
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

### Recommended Models
- `qwen2.5:7b` (7B, balanced)
- `qwen2.5:4b` (4B, faster, less capable)
- `mistral:7b` (7B, good quality)
- `neural-chat:7b` (7B, conversation-optimized)

### Pros
- Completely private
- No internet required
- Free
- Full control

### Cons
- Slow on CPU (~20-40 sec per line)
- Requires GPU for acceptable speed
- High local disk usage (7B model = ~4GB)

---

## 2. LM Studio (Local)

**Best for:** Easy local GPU setup, development

### Setup
1. Download from https://lmstudio.ai
2. Open the app
3. Load a model in "Local Server" tab
4. Click "Start Server"

### Configuration
```bash
LLM_BACKEND=lmstudio
LM_STUDIO_URL=http://localhost:1234
LM_STUDIO_MODEL=google/gemma-4-26b-a4b
```

### Recommended Models
- `google/gemma-4-26b-a4b` (26B, excellent)
- `google/gemma-2-9b-it` (9B, good)
- `mistral-7b-instruct-v0.2` (7B)

### Pros
- Beautiful UI
- Easy model management
- Works great with GPU
- Free

### Cons
- GUI overhead
- Not ideal for CI/CD
- Requires manual model loading

---

## 3. NVIDIA NIM (Cloud API)

**Best for:** Free powerful models, minimal setup

### Setup
1. Create free account at https://build.nvidia.com/
2. Copy your API key
3. Configure below

### Configuration
```bash
LLM_BACKEND=nim
NIM_API_KEY=nvapi-xxxxxxxxxxxxx
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=meta/llama-3.1-70b-instruct
```

### Recommended Models
- `meta/llama-3.1-70b-instruct` (70B, most capable)
- `nvidia/nemotron-4-340b-instruct` (340B, best quality)
- `mistralai/mistral-7b-instruct-v0.1` (7B, fast)

### Free Tier Limits
- 2 requests/minute
- 1000 requests/day
- Multiple powerful models

### Pros
- Free tier is generous
- Extremely capable models (70B+)
- Fast responses
- No local resources needed

### Cons
- Rate limited on free tier
- Requires internet
- API key needed

---

## 4. Google Gemini (Cloud API)

**Best for:** Fastest, most reliable, research/education

### Setup
1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Copy your API key
4. Configure below

### Configuration
```bash
LLM_BACKEND=gemini
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.0-flash
```

### Available Models
- `gemini-2.0-flash` (fastest, latest)
- `gemini-1.5-pro` (most capable)
- `gemini-1.5-flash` (balanced)

### Free Tier Limits
- 60 requests/minute
- Unlimited requests
- Gemini 1.5 Flash model

### Pros
- Fastest responses (~2-5 sec per line)
- Best reliability (Google's infrastructure)
- Most generous free tier
- Excellent quality
- Easy API

### Cons
- Requires internet
- Data sent to Google
- Less customization than local

---

## Choosing Your Backend

### Recommendation Matrix

**I want complete privacy:**
→ Ollama (with GPU)

**I want easy local GPU setup:**
→ LM Studio

**I want free powerful models:**
→ NVIDIA NIM

**I want fastest responses:**
→ Google Gemini

**I want to minimize cost for production:**
→ Ollama (one-time setup)

**I want minimal DevOps:**
→ Google Gemini

---

## Performance Comparison

### Response Time per Line
- **Ollama (CPU):** 30-60 sec
- **Ollama (GPU RTX 4090):** 3-5 sec
- **LM Studio (GPU RTX 4090):** 3-5 sec
- **NVIDIA NIM:** 3-8 sec
- **Google Gemini:** 2-4 sec

### Quality (subjective)
- **Ollama (7B):** 7/10
- **LM Studio (26B):** 8/10
- **NVIDIA NIM (70B):** 9/10
- **Google Gemini:** 9.5/10

### Cost per 1000 Exchanges
- **Ollama:** $0 (after GPU cost)
- **LM Studio:** $0 (after GPU cost)
- **NVIDIA NIM:** $0 (free tier: ~1000/day)
- **Google Gemini:** $0 (free tier: unlimited Flash)

---

## Quick Start Examples

### Fastest Setup (2 minutes)
```bash
# Get API key from https://ai.google.dev/
echo "LLM_BACKEND=gemini
GEMINI_API_KEY=AIza..." > .env
docker-compose --env-file .env up -d
```

### Cheapest Production (one-time cost)
```bash
# Buy/reuse GPU (~$200-2000)
# Install Ollama
ollama pull qwen2.5:7b
echo "LLM_BACKEND=ollama" > .env
docker-compose --env-file .env up -d
```

### Best Quality
```bash
# Use NVIDIA NIM 70B
echo "LLM_BACKEND=nim
NIM_API_KEY=nvapi-..." > .env
docker-compose --env-file .env up -d
```

### Development/Testing
```bash
# Use Google Gemini (free unlimited)
echo "LLM_BACKEND=gemini
GEMINI_API_KEY=AIza..." > .env
docker-compose --env-file .env up -d
```

---

## Switching Backends

Backends are completely interchangeable — switch anytime:

```bash
# Currently using Gemini, switch to Ollama:
echo "LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434" > .env
docker-compose --env-file .env restart app

# Currently using Ollama, switch to NIM:
echo "LLM_BACKEND=nim
NIM_API_KEY=nvapi-..." > .env
docker-compose --env-file .env restart app
```

No code changes needed — just configuration.

---

## API Key Security

### Keep your keys safe:
- ✅ Store in `.env` file (add to `.gitignore`)
- ✅ Use environment variables in production
- ❌ Never commit API keys to git
- ❌ Never share in logs or screenshots

### Rotate keys:
- Regenerate on your provider website
- Update `.env` or `docker-compose.yml`
- Restart container

---

## Troubleshooting

### Backend not responding
Check the configured URL/API key and restart.

### "Invalid API key"
- Verify key is correct (copy-paste from provider)
- Check quota hasn't been exceeded
- Generate a new key if needed

### Slow responses
- Check network latency (for cloud APIs)
- Check GPU status (for local)
- Try smaller model

### Different response quality between backends
Models vary in capability (see table above). Use appropriate model for your needs.

---

## License

MIT
