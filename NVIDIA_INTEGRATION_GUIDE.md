# NVIDIA API Integration Guide

This guide shows how to integrate the `NvidiaClient` wrapper into your existing codebase.

## Files Generated

1. **`nvidia_client.py`** — The NVIDIA API wrapper class
2. **`.env.example`** — Configuration template
3. **This file** — Integration instructions

## Setup

### 1. Create `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your NVIDIA API key:

```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Do NOT commit `.env` to git.** Add it to `.gitignore`:

```
.env
.env.local
*.key
```

### 2. Load environment variables

Add this to the top of `agentic_office_comedy.py`:

```python
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
```

Install python-dotenv if needed:

```bash
pip install python-dotenv
```

## Usage Examples

### Non-streaming (simple generation)

```python
from nvidia_client import NvidiaClient

client = NvidiaClient(
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_tokens=150,
    temperature=0.7,
)

result = client.generate_chat(
    system="You are a helpful assistant.",
    user="What is 2+2?"
)
print(result)
```

### With reasoning enabled

```python
client = NvidiaClient(
    api_key=os.getenv("NVIDIA_API_KEY"),
    enable_reasoning=True,
    reasoning_effort="high",
    max_tokens=500,
)

result = client.generate_chat(
    system="Think step-by-step before answering.",
    user="Explain quantum entanglement."
)
```

### Streaming (real-time chunks)

```python
client = NvidiaClient(
    api_key=os.getenv("NVIDIA_API_KEY"),
)

for chunk in client.generate_chat_streaming(
    system="You are a helpful assistant.",
    user="Tell me a joke."
):
    if "reasoning" in chunk:
        print(f"🧠 {chunk['reasoning']}", end="", flush=True)
    elif "content" in chunk:
        print(f"{chunk['content']}", end="", flush=True)
    elif "error" in chunk:
        print(f"❌ Error: {chunk['error']}")
```

## Integrating into SceneOrchestrator

To use NvidiaClient as an alternative to OllamaClient in your scene generation:

### Option A: Replace OllamaClient entirely

In `agentic_office_comedy.py`, replace the OllamaClient initialization:

```python
# OLD:
_ollama = OllamaClient(
    model="google/gemma-4-26b-a4b",
    base_url="http://localhost:1234",
    max_tokens=150,
    temperature=0.7,
    timeout=60.0,
    backend="lmstudio",
)

# NEW:
from nvidia_client import NvidiaClient

_ollama = NvidiaClient(
    api_key=os.getenv("NVIDIA_API_KEY"),
    model="deepseek-ai/deepseek-v4-flash",
    max_tokens=150,
    temperature=0.7,
    timeout=60.0,
)
```

NvidiaClient has the same interface as OllamaClient, so no other changes needed.

### Option B: Support both backends

Create a factory function:

```python
def create_llm_client(backend="lmstudio"):
    """Create appropriate LLM client based on backend selection."""
    if backend == "nvidia":
        return NvidiaClient(
            api_key=os.getenv("NVIDIA_API_KEY"),
            model=os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-flash"),
            max_tokens=150,
            temperature=0.7,
            timeout=60.0,
        )
    else:
        return OllamaClient(
            model="google/gemma-4-26b-a4b",
            base_url="http://localhost:1234",
            max_tokens=150,
            temperature=0.7,
            timeout=60.0,
            backend="lmstudio",
        )

# Usage
_ollama = create_llm_client(backend="nvidia")  # or "lmstudio"
```

## API Key Security

⚠️ **CRITICAL SECURITY NOTES:**

1. **Never hardcode API keys** in source code
2. **Never commit `.env` to git** — add to `.gitignore`
3. **Rotate keys immediately** if accidentally exposed
4. **Use environment variables only** for sensitive credentials
5. Consider using a secrets manager for production (e.g., HashiCorp Vault, AWS Secrets Manager)

## Troubleshooting

### Connection Error: "NVIDIA API unavailable"

- Check your internet connection
- Verify API key is valid: `client.is_available()`
- Check API endpoint is correct in `.env`

### 401 Unauthorized

- API key is invalid or expired
- Regenerate a new key from https://build.nvidia.com/

### 429 Too Many Requests

- You've hit rate limits
- Wait a few seconds and retry
- Check NVIDIA API quota and limits

### Timeout Errors

- Increase `NVIDIA_TIMEOUT` in `.env`
- The API may be overloaded; try again later
- Some reasoning requests take longer

## API Response Format

The streaming endpoint returns chunks with this structure:

```json
{
  "choices": [
    {
      "delta": {
        "reasoning": "...",     // Chain-of-thought reasoning (if enabled)
        "content": "..."        // Generated text output
      }
    }
  ]
}
```

The `NvidiaClient` extracts and yields these separately.

## Testing

```python
# Quick test
import os
from nvidia_client import NvidiaClient

client = NvidiaClient(api_key=os.getenv("NVIDIA_API_KEY"))

# Test availability
if client.is_available():
    print("✅ NVIDIA API is reachable")
    
    # Test generation
    result = client.generate_chat(
        system="You are a comedy writer.",
        user="Write a one-liner about office life."
    )
    print(f"Generated: {result}")
else:
    print("❌ NVIDIA API is not reachable")
```

## Performance Notes

- **Streaming** is recommended for better UX (real-time output)
- **Non-streaming** blocks until full response arrives
- **Reasoning** (thinking tokens) adds latency but improves output quality
- Consider enabling reasoning only when needed

## Next Steps

1. Copy `nvidia_client.py` to your project
2. Create `.env` file with your API key
3. Test with the examples above
4. Integrate into `SceneOrchestrator` using Option A or B
5. Update `GenerationConfig` to expose model/API choice if desired
