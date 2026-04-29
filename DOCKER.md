# 🐳 Docker Setup

Run the Agentic Office Comedy app in Docker. The app connects to your LLM server (Ollama or LM Studio) running separately.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually included with Docker Desktop
- **LLM Server**: One of:
  - [Ollama](https://ollama.ai) running locally (or on network)
  - [LM Studio](https://lmstudio.ai) running locally (or on network)

## Quick Start

Choose one of four LLM backends:

### Local Backends

#### Option 1: Ollama
```bash
# 1. Start Ollama
ollama serve

# 2. In another terminal, pull a model
ollama pull qwen2.5:7b

# 3. Configure and start the app
# In docker-compose.yml or .env:
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434

docker-compose up -d
```

#### Option 2: LM Studio
```bash
# 1. Download and open LM Studio (https://lmstudio.ai)
# 2. Load a model in "Local Server" tab
# 3. Click "Start Server" (listens on :1234)

# 4. Configure and start the app
# In docker-compose.yml or .env:
LLM_BACKEND=lmstudio
LM_STUDIO_URL=http://localhost:1234

docker-compose up -d
```

### Cloud Backends

#### Option 3: NVIDIA NIM (Free)
```bash
# 1. Get free API key from https://build.nvidia.com/
# 2. Create .env file:
LLM_BACKEND=nim
NIM_API_KEY=nvapi-xxxxx...
NIM_MODEL=meta/llama-3.1-70b-instruct

# 3. Start the app
docker-compose --env-file .env up -d
```

Available models: `meta/llama-3.1-70b-instruct`, `nvidia/nemotron-4-340b-instruct`, `mistralai/mistral-7b-instruct-v0.1`, and more

#### Option 4: Google Gemini (Free tier available)
```bash
# 1. Get free API key from https://ai.google.dev/
# 2. Create .env file:
LLM_BACKEND=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash

# 3. Start the app
docker-compose --env-file .env up -d
```

Available models: `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`

---

### Open the app
```bash
# All backends
# Open http://localhost:7860
```

## Configuration

All settings are in `docker-compose.yml` or `.env`:

### Backend Selection
| Variable | Values | Purpose |
|----------|--------|---------|
| `LLM_BACKEND` | `ollama` \| `lmstudio` \| `nim` \| `gemini` | Which LLM backend to use |

### Ollama Backend
| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model in Ollama (must be pre-pulled) |

### LM Studio Backend
| Variable | Default | Purpose |
|----------|---------|---------|
| `LM_STUDIO_URL` | `http://localhost:1234` | LM Studio server URL |
| `LM_STUDIO_MODEL` | `google/gemma-4-26b-a4b` | Model name loaded in LM Studio |

### NVIDIA NIM Backend
| Variable | Purpose |
|----------|---------|
| `NIM_API_KEY` | **Required** — Get from https://build.nvidia.com/ |
| `NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` (default) |
| `NIM_MODEL` | `meta/llama-3.1-70b-instruct` (default) — see available models below |

**Available NIM Models:**
- `meta/llama-3.1-70b-instruct`
- `nvidia/nemotron-4-340b-instruct`
- `mistralai/mistral-7b-instruct-v0.1`
- `meta/llama-3-8b-instruct`
- And more at https://build.nvidia.com/

### Google Gemini Backend
| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | **Required** — Get from https://ai.google.dev/ |
| `GEMINI_MODEL` | `gemini-2.0-flash` (default) — see available models below |

**Available Gemini Models:**
- `gemini-2.0-flash` (fastest, latest)
- `gemini-1.5-pro` (most capable)
- `gemini-1.5-flash` (cost-effective)

### Generation Parameters
| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_MAX_TOKENS` | `150` | Max tokens per exchange |
| `LLM_TEMPERATURE` | `0.7` | Creativity (0–1, higher = wilder) |
| `LLM_TIMEOUT` | `60.0` | Request timeout (seconds) |

### Storage & UI
| Variable | Default | Purpose |
|----------|---------|---------|
| `CHARACTERS_DIR` | `characters` | Character JSON directory |
| `OUTPUTS_DIR` | `outputs` | Output directory (TTS audio) |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Server binding (0.0.0.0 = all interfaces) |
| `GRADIO_SERVER_PORT` | `7860` | Server port |

## Common Tasks

### Switch Backends

Edit `docker-compose.yml` or `.env`:

**To Ollama:**
```yaml
LLM_BACKEND: ollama
OLLAMA_BASE_URL: http://localhost:11434
```

**To LM Studio:**
```yaml
LLM_BACKEND: lmstudio
LM_STUDIO_URL: http://localhost:1234
```

**To NVIDIA NIM:**
```yaml
LLM_BACKEND: nim
NIM_API_KEY: nvapi-xxxxx
NIM_MODEL: meta/llama-3.1-70b-instruct
```

**To Google Gemini:**
```yaml
LLM_BACKEND: gemini
GEMINI_API_KEY: AIza...
GEMINI_MODEL: gemini-2.0-flash
```

Then restart:
```bash
docker-compose restart app
```

### Use Local LLM Server from Docker (Host Machine)

**Windows/Mac with Docker Desktop:**
```yaml
environment:
  LLM_BACKEND: lmstudio
  LM_STUDIO_URL: http://host.docker.internal:1234
```

**Linux:**
```bash
docker-compose up --network host
```

### Use NIM or Gemini from Docker

Simply set your API key in `.env` or `docker-compose.yml`:

```bash
# Create .env file
cat > .env << EOF
LLM_BACKEND=nim
NIM_API_KEY=nvapi-your-key-here
EOF

# Start with .env
docker-compose --env-file .env up -d
```

### Access from Another Machine

Set `GRADIO_SERVER_NAME: 0.0.0.0`, then access via: `http://<your-machine-ip>:7860`

### Compare Backend Costs & Performance

| Backend | Cost | Speed | Quality | Setup |
|---------|------|-------|---------|-------|
| **Ollama** | Free | Slow (CPU) | Good | Complex |
| **LM Studio** | Free | Fast (GPU) | Good | Manual |
| **NIM** | Free tier | Fast | Excellent | Easy |
| **Gemini** | Free tier | Very Fast | Excellent | Easy |

- **Free tier limits:** NIM and Gemini both offer generous free tiers
- **Best for experimentation:** NVIDIA NIM (powerful models, free tier)
- **Best for local control:** Ollama or LM Studio
- **Best for reliability:** Gemini (Google's infrastructure)

### Persist Characters Across Restarts

Characters are automatically saved to `./characters/` (mounted volume). Your edits persist.

To reset to defaults:

```bash
rm -rf characters/
docker-compose restart app
```

### View Logs

```bash
# App logs
docker-compose logs -f app
```

### Stop Everything

```bash
docker-compose down
```

## Troubleshooting

### Connection errors

**"Connection error: unavailable"** for Ollama or LM Studio

**Cause**: The configured LLM server isn't running or the URL is wrong.

**Fix**:
1. Verify your LLM server is running:
   - Ollama: `curl http://localhost:11434/`
   - LM Studio: `curl http://localhost:1234/v1/models`

2. Check the URL in `docker-compose.yml` matches your server

3. If your server is on another machine, use its IP:
   ```yaml
   OLLAMA_BASE_URL: http://192.168.1.100:11434
   ```

4. Restart the app: `docker-compose restart app`

### API Key errors

**"ValueError: NIM_API_KEY is required"** or **"GEMINI_API_KEY is required"**

**Cause**: You set `LLM_BACKEND=nim` or `gemini` but didn't provide the API key.

**Fix**:
1. Get a free API key:
   - NIM: https://build.nvidia.com/
   - Gemini: https://ai.google.dev/

2. Set in `.env` or `docker-compose.yml`:
   ```yaml
   NIM_API_KEY: nvapi-xxxxx
   # OR
   GEMINI_API_KEY: AIza...
   ```

3. Restart: `docker-compose restart app`

### Invalid API key

**"HTTP 401"** or **"Unauthorized"**

**Cause**: The API key is expired, invalid, or quota exceeded.

**Fix**:
1. Verify the API key is correct (copy-paste from provider)
2. Check quota at https://build.nvidia.com/ or https://ai.google.dev/
3. Generate a new API key if needed
4. Restart the app

### Port 7860 already in use

Change the port in `docker-compose.yml`:

```yaml
ports:
  - "8080:7860"  # Access at http://localhost:8080
```

### Can't access http://localhost:7860 from another machine

Edit `docker-compose.yml` and ensure:

```yaml
environment:
  GRADIO_SERVER_NAME: 0.0.0.0
```

Then access via the host's IP: `http://<your-ip>:7860`.

## Performance Notes

- **Generation**: 5–15 sec per exchange (depends on model size and hardware)
- **Memory**: 7B model needs ~8 GB RAM; 4B needs ~4 GB; 2B needs ~2 GB
- **GPU**: 10x faster than CPU (both Ollama and LM Studio support GPU)
- **Network**: If LLM server is on another machine, network latency will add to response time

## Getting API Keys

### NVIDIA NIM (Free Tier)

1. Go to https://build.nvidia.com/
2. Click "Sign In" or "Get Free Account"
3. Complete sign-up
4. Go to your **Credentials** or **API Keys** page
5. Copy your API key (starts with `nvapi-`)
6. Add to `.env`:
   ```
   LLM_BACKEND=nim
   NIM_API_KEY=nvapi-xxxxx
   ```

**Free tier includes:**
- 2 requests per minute
- 1000 requests per day
- Models: Llama 3.1 70B, Mistral 7B, Nemotron 4 340B

### Google Gemini (Free Tier)

1. Go to https://ai.google.dev/
2. Click "Get API Key"
3. Create new project or select existing
4. Copy the API key
5. Add to `.env`:
   ```
   LLM_BACKEND=gemini
   GEMINI_API_KEY=AIza...
   ```

**Free tier includes:**
- 60 requests per minute
- Unlimited requests (Gemini 1.5 Flash)
- Models: Gemini 2.0 Flash, Gemini 1.5 Pro/Flash

### Start with .env

```bash
cp .env.example .env
# Edit .env with your API keys and backend choice
docker-compose --env-file .env up -d
```

## Environment File

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
# Edit .env with your settings
docker-compose --env-file .env up -d
```

## Development

Rebuild the image after code changes:

```bash
docker-compose up -d --build
```

## Examples

### Comedy Scene with NVIDIA NIM
```bash
echo "LLM_BACKEND=nim
NIM_API_KEY=nvapi-xxxxx
NIM_MODEL=meta/llama-3.1-70b-instruct" > .env

docker-compose --env-file .env up -d
# Open http://localhost:7860
# Select: English Office Comedy → Comedy Mode → Generate
```

### Drama Scene with Google Gemini
```bash
echo "LLM_BACKEND=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash" > .env

docker-compose --env-file .env up -d
# Open http://localhost:7860
# Select: English Office Comedy → Drama Mode → Generate
```

### Local LLM with Ollama
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull a model
ollama pull qwen2.5:7b

# Terminal 3: Start the app
echo "LLM_BACKEND=ollama" > .env
docker-compose --env-file .env up -d
```

## License

MIT
