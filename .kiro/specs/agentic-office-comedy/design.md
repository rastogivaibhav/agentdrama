# Design Document: Agentic Office Comedy

## Overview

Agentic Office Comedy is a single-file Python application that orchestrates multiple LLM-backed agents to improvise comedy scenes in two distinct styles: English office cringe comedy and Hindi bureaucratic satire. The system is fully offline after initial model downloads, using Ollama for local LLM inference and optionally Kokoro for local TTS synthesis. A Gradio web UI provides the user-facing interface.

The core design philosophy is **simplicity over abstraction**: everything lives in one Python script, no agent frameworks are used, and all orchestration logic is hand-rolled. This makes the codebase easy to audit, deploy, and extend.

### Key Design Decisions

- **Single-file architecture**: Reduces deployment friction and makes the codebase self-contained. The tradeoff is that the file will be long, but inline comments and clear section headers mitigate readability concerns.
- **Custom HTTP client over agent frameworks**: Preserves full IP ownership of orchestration logic and avoids heavy dependencies that would conflict with the offline-first constraint.
- **Round-robin sequencing**: Simple, predictable, and fair to all characters. Avoids the complexity of dynamic speaker selection while still producing natural-feeling scenes.
- **Rolling transcript window**: Keeps prompt length bounded regardless of scene length, which is critical for VRAM-constrained hardware.
- **Dataclasses for structured data**: Provides type safety and IDE support without the overhead of Pydantic or other validation libraries.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Gradio UI                            │
│  (Show_Style selector, scenario input, sliders, outputs)    │
└──────────────────────────┬──────────────────────────────────┘
                           │ user triggers generation
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SceneOrchestrator                         │
│  - selects characters by show style                         │
│  - round-robin sequencing                                   │
│  - transcript management                                    │
│  - Moderator repetition checks                              │
│  - calls PromptBuilder → OllamaClient per exchange          │
│  - calls KokoroTTS per exchange (if enabled)                │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────────┐
│PromptBuilder│ │OllamaClient│ │   KokoroTTS    │
│            │ │            │ │  (optional)    │
│ builds     │ │ HTTP POST  │ │ KPipeline +    │
│ in-character│ │ /api/generate│ │ soundfile     │
│ prompts    │ │            │ │                │
└────────────┘ └────────────┘ └────────────────┘
       ▲
┌────────────┐
│Character   │
│  Loader    │
│ reads JSON │
│ characters/│
└────────────┘
```

### Data Flow

1. On startup, `CharacterLoader` reads all JSON files from `characters/`, auto-creating samples if none exist.
2. User fills in the Gradio UI (show style, scenario, exchange count, TTS toggle) and clicks Generate.
3. The UI calls `SceneOrchestrator.run_scene(config)`.
4. The orchestrator filters characters by `show_style`, then iterates round-robin for `num_exchanges` turns:
   a. `PromptBuilder.build(character, transcript_window, scenario)` → prompt string
   b. `OllamaClient.generate(prompt)` → raw text
   c. `Moderator.check(exchange, transcript)` → accept or retry (up to 2 retries)
   d. Append accepted exchange to transcript
   e. If TTS enabled: `KokoroTTS.synthesize(exchange, output_folder)` → WAV path
5. Orchestrator assembles `SceneResult` and returns it to the UI.
6. UI renders the script text, audio player (last file), and file list.

---

## Components and Interfaces

### CharacterLoader

Responsible for discovering and validating character definitions.

```python
class CharacterLoader:
    def __init__(self, characters_dir: Path) -> None: ...
    def load_all(self) -> list[Character]: ...
    def _auto_create_samples(self) -> None: ...
    def _load_file(self, path: Path) -> Character | None: ...
```

- `load_all()` scans `characters_dir` for `*.json` files, calls `_load_file` on each, skips invalid files with a warning, and returns the valid list.
- `_auto_create_samples()` is called when no JSON files are found; it writes the eight sample character files.
- `_load_file()` validates required fields (`name`, `show`, `personality`, `speaking_style`, `catchphrases`, `kokoro_voice`) and returns `None` on missing fields.

### OllamaClient

Thin HTTP wrapper around the Ollama `/api/generate` endpoint.

```python
class OllamaClient:
    def __init__(self, model: str, base_url: str, max_tokens: int,
                 temperature: float, timeout: float) -> None: ...
    def generate(self, prompt: str) -> str: ...
    def is_available(self) -> bool: ...
```

- `generate()` sends a POST to `/api/generate` with `stream=False`, parses the JSON response, and returns the `response` field. On timeout or non-2xx status, logs the error and returns a descriptive fallback string.
- `is_available()` sends a lightweight GET to `/` to check server reachability; used at startup to set UI state.
- Uses Python's `urllib.request` (stdlib) to avoid adding an HTTP dependency.

### PromptBuilder

Constructs the in-character prompt for a single exchange.

```python
class PromptBuilder:
    def __init__(self, transcript_window_size: int = 4) -> None: ...
    def build(self, character: Character, transcript: list[DialogueTurn],
              scenario: str) -> str: ...
```

- Selects the last `transcript_window_size` turns from the transcript.
- Formats a compact system-style prompt (no chain-of-thought instructions) that includes character name, personality summary, speaking style, one catchphrase, the scenario, and the transcript window.
- Instructs the model to respond with a single short line prefixed by the character's name.

**Prompt template (illustrative):**

```
You are {name}, a character in an office comedy.
Personality: {personality}
Speaking style: {speaking_style}
Catchphrase: {catchphrases[0]}

Scenario: {scenario}

Recent dialogue:
{transcript_window}

Respond with ONE short line as {name}. Start with "{name}:".
```

### SceneOrchestrator

Coordinates the full scene generation loop.

```python
class SceneOrchestrator:
    def __init__(self, characters: list[Character], ollama: OllamaClient,
                 prompt_builder: PromptBuilder, tts: KokoroTTS | None) -> None: ...
    def run_scene(self, config: GenerationConfig) -> SceneResult: ...
    def _get_characters_for_style(self, show_style: str) -> list[Character]: ...
```

- `run_scene()` filters characters, creates the output folder (if TTS enabled), runs the round-robin loop, and returns a `SceneResult`.
- The Moderator logic lives inline in `run_scene()` as a private helper `_is_repetition(exchange, transcript)` — a simple exact-match check against prior exchange texts.

### KokoroTTS

Optional TTS wrapper; gracefully absent when Kokoro is not installed.

```python
class KokoroTTS:
    def __init__(self) -> None: ...  # raises ImportError if kokoro not installed
    def synthesize(self, turn: DialogueTurn, output_folder: Path) -> Path | None: ...
```

- `synthesize()` calls `KPipeline` with the character's `kokoro_voice`, writes the result via `soundfile.write()`, and returns the WAV path. On exception, logs and returns `None`.
- The application wraps `KokoroTTS()` construction in a try/except at startup; if it fails, `tts` is set to `None` and the UI checkbox is disabled.

### Gradio UI

Single `gr.Blocks` layout wired to `SceneOrchestrator.run_scene`.

Key components:
- `gr.Radio` for Show_Style
- `gr.Textbox` for scenario (with default value)
- `gr.Slider` for exchange count (4–12, default 6)
- `gr.Checkbox` for TTS enable
- `gr.Button` to trigger generation
- `gr.Textbox(interactive=False)` for script output
- `gr.Audio` for last generated audio
- `gr.File` or `gr.Gallery` for full audio file list
- `gr.Textbox(interactive=False)` for status/error messages
- `gr.Examples` with at least six default scenarios

---

## Data Models

All structured data is represented as Python dataclasses.

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Character:
    name: str
    show: str                    # "English Office Comedy" | "Hindi Office Comedy"
    personality: str
    speaking_style: str
    catchphrases: list[str]
    kokoro_voice: str

@dataclass
class DialogueTurn:
    speaker: str                 # character name
    text: str                    # full line including "Speaker: ..." prefix
    audio_path: Path | None = None

@dataclass
class GenerationConfig:
    show_style: str
    scenario: str
    num_exchanges: int           # 4–12
    tts_enabled: bool
    model: str = "qwen2.5:4b"
    max_tokens: int = 150
    temperature: float = 0.7
    transcript_window: int = 4
    timeout: float = 30.0

@dataclass
class SceneResult:
    config: GenerationConfig
    turns: list[DialogueTurn] = field(default_factory=list)
    output_folder: Path | None = None
    error: str | None = None

    def as_script(self) -> str:
        """Return the full scene as a formatted script string."""
        return "\n".join(turn.text for turn in self.turns)

    def audio_paths(self) -> list[Path]:
        return [t.audio_path for t in self.turns if t.audio_path is not None]
```

### Character JSON Schema

Each file in `characters/` must conform to:

```json
{
  "name": "Michael Scott",
  "show": "English Office Comedy",
  "personality": "Cringe overconfident manager who desperately wants to be liked",
  "speaking_style": "Rambling, self-aggrandizing, prone to awkward pauses and misquotes",
  "catchphrases": ["That's what she said", "I am the world's best boss"],
  "kokoro_voice": "af_heart"
}
```

Required fields: `name`, `show`, `personality`, `speaking_style`, `catchphrases` (non-empty list), `kokoro_voice`.

---

## Prompt Design Strategy

### Goals

- Keep prompts short to minimize VRAM usage and latency on 4 GB VRAM hardware.
- Produce single-line, in-character responses without chain-of-thought reasoning.
- Maintain scene continuity through a bounded transcript window.

### Prompt Structure

Each prompt has three logical sections:

1. **Character identity block** (~3 lines): name, personality, speaking style, one catchphrase. This is the same for every exchange by the same character and could be cached in future.
2. **Scene context block** (~2 lines): the user's scenario and the rolling transcript window (last N turns, default 4).
3. **Instruction block** (~2 lines): a direct instruction to produce one short line prefixed with the character's name. No reasoning steps, no alternatives.

### Transcript Window

The window is a slice of the last `transcript_window` `DialogueTurn` objects, formatted as:

```
Michael Scott: That's what she said.
Dwight Schrute: False. Bears eat beets.
Jim Halpert: (stares at camera)
Pam Beesly: I just work here.
```

Limiting to 4 turns keeps the prompt under ~200 tokens for typical exchanges, well within the context budget for `qwen2.5:4b`.

### Output Parsing

The model is instructed to prefix its response with `"{name}:"`. The application strips leading/trailing whitespace and takes the first non-empty line of the response. If the response does not start with the expected prefix, the raw first line is used as-is (graceful degradation).

---

## Scene Orchestration Flow

```
run_scene(config)
│
├── filter characters by config.show_style
├── if len(characters) < 2: return SceneResult(error="Not enough characters")
├── create output_folder (if tts_enabled)
├── transcript = []
│
└── for i in range(config.num_exchanges):
    │
    ├── character = characters[i % len(characters)]   # round-robin
    ├── prompt = prompt_builder.build(character, transcript[-window:], scenario)
    │
    ├── attempts = 0
    ├── while attempts < 3:
    │   ├── raw = ollama.generate(prompt)
    │   ├── exchange = DialogueTurn(speaker=character.name, text=parse(raw))
    │   ├── if not _is_repetition(exchange, transcript): break
    │   └── attempts += 1
    │
    ├── transcript.append(exchange)
    │
    └── if tts_enabled and tts is not None:
        └── exchange.audio_path = tts.synthesize(exchange, output_folder)
│
└── return SceneResult(config, turns=transcript, output_folder=output_folder)
```

### Moderator Logic

`_is_repetition(exchange, transcript)` performs a case-insensitive exact match of the new exchange's text against all prior exchange texts. This is intentionally simple — the goal is to catch verbatim LLM repetition loops, not semantic similarity. A more sophisticated check (e.g., edit distance) is left as a future extensibility hook.

---

## TTS Integration Approach

### Availability Detection

At application startup:

```python
try:
    tts_engine = KokoroTTS()
    tts_available = True
except ImportError:
    tts_engine = None
    tts_available = False
    logging.warning("Kokoro not installed; TTS disabled.")
```

The Gradio checkbox is set to `interactive=tts_available` and its value to `False` when unavailable.

### Synthesis Pipeline

For each `DialogueTurn` when TTS is enabled:

1. Extract the spoken text (strip the `"Speaker: "` prefix for cleaner synthesis).
2. Call `KPipeline(lang_code=...)(text, voice=character.kokoro_voice)`.
3. Collect audio chunks and concatenate.
4. Write to `output_folder / f"{i:02d}_{character.name}.wav"` using `soundfile.write()`.
5. Store the path in `DialogueTurn.audio_path`.

### Voice Assignment

Each character JSON specifies a `kokoro_voice` string (e.g., `"af_heart"`, `"am_michael"`). The TTS engine passes this directly to `KPipeline`. Voice selection is entirely data-driven — adding a new character with a new voice requires no code changes.

### Language Code Selection

Kokoro requires a `lang_code` parameter. The application infers this from `show_style`:
- `"English Office Comedy"` → `lang_code = "en-us"`
- `"Hindi Office Comedy"` → `lang_code = "hi"` (if supported by the installed Kokoro version; falls back to `"en-us"` with a warning)

---

## Error Handling Strategy

| Failure Scenario | Component | Handling |
|---|---|---|
| Ollama server unreachable at startup | OllamaClient.is_available() | Log warning; UI shows status message; generation button remains enabled (user may start Ollama later) |
| Ollama request timeout | OllamaClient.generate() | Log error; return fallback string `"[generation timed out]"` |
| Ollama non-2xx response | OllamaClient.generate() | Log error with status code; return fallback string |
| Kokoro not installed | KokoroTTS.__init__() | Catch ImportError; set tts=None; disable UI checkbox |
| Kokoro synthesis exception | KokoroTTS.synthesize() | Log error; return None; scene continues without audio for that turn |
| Output folder creation failure | SceneOrchestrator.run_scene() | Log error; set tts_enabled=False for this scene; continue with text-only output |
| Character JSON missing fields | CharacterLoader._load_file() | Log warning with field name; skip character; continue loading others |
| No characters for selected style | SceneOrchestrator.run_scene() | Return SceneResult(error="No characters found for style X") |
| Fewer than 2 characters | SceneOrchestrator.run_scene() | Return SceneResult(error="Need at least 2 characters for a scene") |

All errors surface to the user via the Gradio status text area. The application never raises unhandled exceptions to the Gradio layer.

---

## File Output Structure

```
outputs/
└── scene_20241215_143022/
    ├── 00_Michael_Scott.wav
    ├── 01_Dwight_Schrute.wav
    ├── 02_Jim_Halpert.wav
    ├── 03_Pam_Beesly.wav
    ├── 04_Michael_Scott.wav
    └── 05_Dwight_Schrute.wav
```

- Folder name: `scene_YYYYMMDD_HHMMSS` (sortable, human-readable)
- File names: zero-padded exchange index + character name (spaces replaced with underscores)
- Only WAV files are written; no transcript or metadata files in this version (extensibility hook: serialize `SceneResult` to JSON here)

---

## Extensibility Hooks

The design explicitly leaves the following extension points:

1. **New show styles**: Add character JSON files with a new `show` value and update the `gr.Radio` choices list. No other code changes required.
2. **Persistent scene memory**: Extend `SceneResult.turns` to persist between calls, or serialize/deserialize `SceneResult` to JSON in the output folder.
3. **Semantic repetition detection**: Replace `_is_repetition()` with an edit-distance or embedding-based check without changing the orchestration loop.
4. **Streaming output**: Replace `OllamaClient.generate()` with a streaming variant and update the Gradio output to use `gr.Textbox` streaming — the orchestrator loop structure does not need to change.
5. **Additional TTS engines**: Swap `KokoroTTS` for another engine by implementing the same `synthesize(turn, output_folder) -> Path | None` interface.
6. **Scene saving/loading**: Serialize `SceneResult` (all fields are JSON-serializable with a custom encoder for `Path`) to `output_folder/scene.json`.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Property-based testing is applicable here because the core logic components (CharacterLoader, PromptBuilder, SceneOrchestrator, OllamaClient, KokoroTTS) are functions with clear input/output behavior that vary meaningfully with input. The PBT library used is **Hypothesis** (Python).

### Property 1: CharacterLoader loads all valid character files

*For any* collection of valid character JSON files placed in the characters directory, `CharacterLoader.load_all()` shall return a list containing exactly one `Character` object per file, with all fields correctly populated.

**Validates: Requirements 2.1, 11.1**

---

### Property 2: CharacterLoader rejects files missing any required field

*For any* character dict with any single required field (`name`, `show`, `personality`, `speaking_style`, `catchphrases`, `kokoro_voice`) removed, `CharacterLoader._load_file()` shall return `None` rather than a `Character` object.

**Validates: Requirements 2.3, 2.4**

---

### Property 3: OllamaClient embeds max_tokens in every request payload

*For any* `max_tokens` value passed to `OllamaClient`, every call to `generate()` shall include that exact value in the JSON payload sent to the Ollama API endpoint.

**Validates: Requirements 3.4, 10.2**

---

### Property 4: OllamaClient returns a fallback string for any non-2xx HTTP status

*For any* HTTP status code ≥ 400 returned by the Ollama server, `OllamaClient.generate()` shall return a non-empty fallback string rather than raising an exception.

**Validates: Requirements 3.7**

---

### Property 5: PromptBuilder includes all character identity and transcript context

*For any* `Character` and any transcript window, `PromptBuilder.build()` shall return a string that contains the character's `name`, `personality`, `speaking_style`, at least one element of `catchphrases`, and the text of every `DialogueTurn` in the provided window.

**Validates: Requirements 4.1, 4.2**

---

### Property 6: PromptBuilder never exceeds the configured transcript window size

*For any* transcript of length greater than `transcript_window_size`, `PromptBuilder.build()` shall include at most `transcript_window_size` turns in the prompt, always taking the most recent ones.

**Validates: Requirements 4.5**

---

### Property 7: SceneOrchestrator only uses characters matching the selected show style

*For any* mixed collection of characters spanning multiple show styles and any chosen `show_style`, every `DialogueTurn` in the returned `SceneResult` shall have a `speaker` that belongs to a character whose `show` field equals `show_style`.

**Validates: Requirements 5.1**

---

### Property 8: SceneOrchestrator sequences characters in strict round-robin order

*For any* list of N characters (N ≥ 2) and any number of exchanges M, the speaker at position i in `SceneResult.turns` shall be `characters[i % N].name`.

**Validates: Requirements 5.2**

---

### Property 9: Moderator correctly identifies exact repetition

*For any* exchange text that is an exact case-insensitive match of any prior turn's text in the transcript, `_is_repetition()` shall return `True`; for any exchange text that does not match any prior turn, it shall return `False`.

**Validates: Requirements 5.4**

---

### Property 10: SceneResult.as_script() contains all dialogue turns

*For any* list of `DialogueTurn` objects, `SceneResult.as_script()` shall return a string that contains the `text` of every turn in the list, in order.

**Validates: Requirements 5.5**

---

### Property 11: KokoroTTS produces correctly named WAV files using the character's voice

*For any* `DialogueTurn` with a valid `speaker` name and exchange index, when `KokoroTTS.synthesize()` succeeds, it shall: (a) return a `Path` pointing to an existing WAV file, (b) place that file inside the specified `output_folder`, (c) name the file using the zero-padded index and character name pattern, and (d) invoke `KPipeline` with the `kokoro_voice` value from the corresponding character definition.

**Validates: Requirements 7.1, 7.2, 7.3**

---

### Property 12: Scene exchange count never exceeds the configured maximum

*For any* `GenerationConfig` with `num_exchanges` set to any value, `SceneResult.turns` shall contain at most 12 `DialogueTurn` objects.

**Validates: Requirements 10.1**

---

## Error Handling Strategy (Extended)

See the Error Handling table in the Components section above. The key principle is **fail-soft**: every component degrades gracefully rather than propagating exceptions to the Gradio layer. The UI status area is the single surface for all error communication.

---

## Testing Strategy

### Dual Testing Approach

Both unit/example tests and property-based tests are used:

- **Unit/example tests**: Verify specific scenarios, error paths, and startup behavior (Ollama unavailable, Kokoro not installed, empty characters directory, filesystem errors).
- **Property-based tests**: Verify universal correctness properties across randomized inputs using **Hypothesis**.

### Property-Based Testing Configuration

- Library: `hypothesis` (Python)
- Minimum iterations: 100 per property (Hypothesis default `max_examples=100`)
- Each property test is tagged with a comment referencing the design property:
  ```python
  # Feature: agentic-office-comedy, Property 1: CharacterLoader loads all valid character files
  @given(st.lists(valid_character_strategy(), min_size=1, max_size=10))
  def test_character_loader_loads_all_valid_files(characters): ...
  ```

### Unit Test Focus Areas

- `CharacterLoader._auto_create_samples()` creates files for both show styles (Requirements 2.5, 2.6)
- `OllamaClient.generate()` returns fallback on timeout (Requirement 3.6)
- `OllamaClient.generate()` returns fallback on connection error (Requirement 1.3)
- `SceneOrchestrator.run_scene()` with TTS disabled produces no audio files (Requirement 7.5)
- `SceneOrchestrator.run_scene()` with filesystem error disables TTS gracefully (Requirement 8.3)
- `KokoroTTS.synthesize()` returns `None` on Kokoro exception without halting scene (Requirement 7.6)
- Output folder naming matches `outputs/scene_YYYYMMDD_HHMMSS` pattern (Requirement 8.1)

### What Is Not Property-Tested

- UI component layout (Gradio Blocks structure) — manual/smoke verification
- Offline network constraint — architectural enforcement, not runtime testable
- Code quality requirements (type hints, logging, single-file) — static analysis / linting
- Sequential execution constraints — architectural enforcement
