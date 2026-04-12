# 🎭 Agentic Workplace Scene Simulator

A fully **offline**, **single-file** Python app that orchestrates multiple LLM-backed agents to improvise workplace scenes in three modes — **Comedy**, **Drama**, and **Debate** — across two cultural settings: English office cringe comedy and Hindi bureaucratic satire.

Powered by [LM Studio](https://lmstudio.ai) (or Ollama) for local LLM inference and optionally [Kokoro](https://github.com/hexgrad/kokoro) for local TTS synthesis.

---

## Demo

```
Gareth Pinnock: I've called this emergency meeting because the printer situation
                is, frankly, a leadership opportunity.
Tim Blankenship: Sure.
Dwight Bramble: False. The printer is not broken. It is on strike. I have filed
                a formal grievance on its behalf.
Parveen Osei: I'll let facilities know you called.
Gareth Pinnock (confessional): Between you and me, I have no idea how printers work.
```

---

## Features

- **3 scene modes** — Comedy, Drama, Debate — each with distinct tone, rules, and escalation logic
- **2 cultural settings** — English office mockumentary, Hindi bureaucratic satire
- **Live streaming** — lines appear one by one as agents generate them
- **Character panel** — add, edit, remove, and toggle agents mid-scene
- **Pause / resume / stop** — full scene flow control
- **Confessional asides** — characters break the fourth wall every 3rd turn (Comedy/Drama)
- **Debate roles** — deterministic moderator + pro/con/pragmatic assignment
- **Hidden scene state** — tension ramp, conflict objective, last shift injected into every prompt
- **Persistent characters** — edits write back to JSON files in `characters/`
- **Optional TTS** — per-character voice synthesis via Kokoro KPipeline
- **Fully offline** — no cloud APIs, no external agent frameworks

---

## Quick Start

### 1. Install dependencies

```bash
pip install gradio
# Optional TTS:
pip install kokoro soundfile
```

### 2. Start LM Studio

1. Open LM Studio → **Local Server** tab
2. Load a model (recommended: `qwen2.5-7b-instruct`, `gemma-3-4b-it`, or `mistral-7b-instruct`)
3. Click **Start Server** (binds to `http://localhost:1234`)

> **Model recommendations by mode:**
> - Debate: works well on 4B models
> - Drama: needs 7B+ for coherent emotional arcs
> - Comedy: 4B is fine, bigger = funnier

### 3. Run

```bash
python agentic_office_comedy.py
```

Open **http://localhost:7860** in your browser.

### Using Ollama instead of LM Studio

Edit the wiring block at the bottom of `agentic_office_comedy.py`:

```python
_ollama = OllamaClient(
    model="qwen2.5:7b",
    base_url="http://localhost:11434",
    max_tokens=150,
    temperature=0.7,
    timeout=60.0,
    backend="ollama",   # ← change this
)
```

---

## Scene Modes

| Mode | Tone | Confessionals | Debate Roles | Tension Ramp |
|------|------|:---:|:---:|:---:|
| **Comedy** | Cringe, absurdity, dry reactions | ✅ every 3rd turn | ❌ | +0.07/turn |
| **Drama** | Emotional pressure, career stakes | ✅ every 3rd turn | ❌ | +0.10/turn |
| **Debate** | Structured argument, rebuttals | ❌ | ✅ moderator + roles | +0.06/turn |

---

## Character System

Characters are JSON files in `characters/`. Eight samples are auto-created on first run.

```json
{
  "name": "Gareth Pinnock",
  "show": "English Office Comedy",
  "personality": "Cringe overconfident manager who desperately wants to be liked",
  "speaking_style": "Rambling, self-aggrandizing, prone to awkward pauses",
  "catchphrases": ["That's what she said", "Would I rather be feared or loved? Easy. Both."],
  "kokoro_voice": "af_heart"
}
```

**Required fields:** `name`, `show`, `personality`, `speaking_style`, `catchphrases` (list), `kokoro_voice`

**`show` values:** `"English Office Comedy"` or `"Hindi Office Comedy"`

Add new characters by dropping JSON files into `characters/` or using the in-app editor.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| VRAM | 4 GB | 8 GB |
| RAM | 16 GB | 32 GB |
| Model size | 4B params | 7B params |

The app makes sequential inference calls — one per exchange — so VRAM usage is bounded by the model size, not the scene length.

---

## Project Structure

```
agentic_office_comedy.py   # entire application — single file
characters/                # character JSON files (auto-created)
outputs/                   # TTS audio output (scene_YYYYMMDD_HHMMSS/)
tests/
  test_properties.py       # Hypothesis property-based tests (12 properties)
  test_unit.py             # Unit tests for error paths
.kiro/specs/               # Kiro spec documents (requirements, design, tasks)
```

---

## Running Tests

```bash
pip install pytest hypothesis numpy
python -m pytest tests/ -v
```

---

## License

MIT
