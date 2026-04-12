# Architecture Document — Agentic Workplace Scene Simulator

## Overview

The application is a **single Python script** (`agentic_office_comedy.py`) that orchestrates multiple LLM-backed agents to generate workplace scenes. The design philosophy is **simplicity over abstraction**: no agent frameworks, no vector databases, no streaming HTTP — just a hand-rolled HTTP client, dataclasses, and a Gradio UI.

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Gradio UI (create_app)                     │
│  Show Style · Scene Mode · Scenario · Exchanges · TTS · Cast Panel  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ user triggers generation
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SceneOrchestrator                             │
│  _init_scene_state()   → SceneState (hidden director brain)         │
│  _pick_character()     → round-robin or debate order                │
│  _should_do_confessional() → every 3rd turn in Comedy/Drama         │
│  run_scene_streaming() → yields SceneResult after each exchange     │
│  _update_scene_state() → tension ramp, last_shift tracking          │
│  _post_process()       → strip markdown, enforce speaker prefix     │
│  _enforce_speaker_prefix() → guarantee "Name: line" format          │
└──────┬──────────────┬──────────────────────────────────────────────┘
       │              │
       ▼              ▼
┌────────────┐  ┌─────────────────────────────────────────────────────┐
│PromptBuilder│  │              OllamaClient                           │
│            │  │  generate_chat(system, user) → LM Studio            │
│build_chat()│  │  _generate_openai() → /v1/chat/completions          │
│build_      │  │  _generate_ollama() → /api/generate                 │
│confessional│  │  is_available()     → /v1/models or /               │
│mode_       │  └─────────────────────────────────────────────────────┘
│instruction │
│mode_rules  │  ┌─────────────────────────────────────────────────────┐
└────────────┘  │              KokoroTTS (optional)                   │
       ▲        │  synthesize(turn, folder, idx, char, style)         │
       │        │  → KPipeline → numpy concat → soundfile.write       │
┌────────────┐  └─────────────────────────────────────────────────────┘
│CharacterLoader│
│load_all()  │
│save_char() │
│delete_char()│
│characters/ │
└────────────┘
```

---

## Data Flow

1. **Startup**: `CharacterLoader` reads `characters/*.json`, auto-creates 8 samples if empty. `OllamaClient.is_available()` checks the LLM server. `KokoroTTS()` construction is attempted; failure sets `tts_available=False`.

2. **User submits**: UI calls `generate_scene(show_style, scene_mode, scenario, num_exchanges, tts_enabled, active_names)`.

3. **Scene init**: `SceneOrchestrator._init_scene_state()` creates a `SceneState` with mode-specific conflict, objective, and starting tension. For Debate mode, `_assign_debate_roles()` deterministically assigns moderator/pro/con/pragmatic roles.

4. **Turn loop** (streaming generator):
   - `_pick_character()` — round-robin for Comedy/Drama; debate order with moderator every 4th turn for Debate
   - `_should_do_confessional()` — true every 3rd turn in Comedy/Drama (never in Debate)
   - `PromptBuilder.build_chat()` or `build_confessional()` — constructs system+user prompt pair with hidden scene state injected
   - `OllamaClient.generate_chat()` — POST to `/v1/chat/completions`, returns first non-empty line
   - `_post_process()` + `_enforce_speaker_prefix()` — clean output, guarantee `"Name: line"` format
   - Repetition check with up to 2 retries
   - `_update_scene_state()` — increment tension, record last shift
   - `yield SceneResult(turns=transcript_so_far)` — UI updates live

5. **UI renders**: Each yielded `SceneResult` appends to the script textbox. The cast panel shows 🟢/⚫ roster. Pause/stop flags are checked between exchanges.

---

## Key Design Decisions

### Single-file architecture
Reduces deployment friction. The tradeoff is a long file (~1400 lines), mitigated by clear section headers and inline comments.

### Custom HTTP client over agent frameworks
`OllamaClient` uses only `urllib.request` (stdlib). This preserves full IP ownership of orchestration logic and avoids heavy dependencies that conflict with the offline-first constraint.

### System/user prompt split
The chat completions API (`/v1/chat/completions`) accepts separate system and user messages. Putting character identity and hard rules in the system message and scene context in the user message gives smaller models a much clearer role boundary, dramatically improving in-character consistency.

### Hidden scene state
`SceneState` is injected into every prompt as a hidden context block. The model never "sees" it as instructions — it reads as background context. This guides escalation without requiring the model to track state itself.

### Round-robin sequencing
Simple, predictable, fair. Avoids the complexity of dynamic speaker selection while producing natural-feeling scenes. Debate mode overrides this with a deterministic role-based order.

### Rolling transcript window
Prompt length is bounded to the last N turns (default 4) regardless of scene length. Critical for VRAM-constrained hardware.

### Streaming generator
`run_scene_streaming()` yields after each exchange. The Gradio UI polls this generator and updates the script textbox live. Pause/stop are implemented as shared flags checked between yields — a simple but effective approach for a sequential single-threaded generator.

---

## Scene Mode Engine

### SceneState (director brain)

```python
@dataclass
class SceneState:
    mode: str               # Comedy | Drama | Debate
    topic_or_scenario: str
    tension: float          # 0.0–1.0, ramps each turn
    objective: str          # what the scene is trying to achieve
    conflict: str           # the underlying dramatic tension
    last_shift: str         # last 100 chars of previous line
    turn_index: int
    debate_roles: dict      # {name: role_description} — Debate only
    debate_order: list      # ordered speaker list — Debate only
```

### Tension ramp

| Mode | Starting tension | Per-turn increment | Max |
|------|:---:|:---:|:---:|
| Comedy | 0.25 | +0.07 | 1.0 |
| Drama | 0.40 | +0.10 | 1.0 |
| Debate | 0.40 | +0.06 | 1.0 |

### Confessional logic

In Comedy and Drama, every 3rd turn (turn_index % 3 == 2, after the first turn) triggers a confessional aside. The character speaks directly to a documentary camera, revealing their inner thoughts. Output is labelled `"Name (confessional)"`.

### Debate role assignment

For Debate mode, characters are assigned roles deterministically based on their position in the filtered character list:

| Position | English role | Hindi role |
|----------|-------------|-----------|
| 0 | Moderator (fair, visionary) | Moderator (procedural) |
| 1 | Strongly in favour | Strongly in favour |
| 2 | Strongly against | Strongly against |
| 3 | Pragmatic middle ground | Pragmatic (lived frustration) |

Every 4th turn (after the first) is forced back to the moderator for framing/summary.

---

## Prompt Architecture

Each exchange uses a **system + user** message pair:

**System message** (character identity + mode rules):
```
You are {name}, a character in a workplace scene.
Personality: {personality}
Speaking style: {speaking_style}
Catchphrase flavour: "{catchphrase}"

Mode: {Comedy|Drama|Debate}. Tone: {mode-specific tone description}
RULES: output ONE short {mode-specific rule}. Max 20 words. Start with your character name and a colon.
```

**User message** (scene context + cue):
```
Hidden scene state:
- mode: Drama
- conflict: workplace tension is exposing insecurity or unfairness
- objective: escalate realistic emotional stakes
- tension: 0.60
- last shift: "You keep calling it process, but it feels personal."

Scenario: A manager takes credit for a team member's work.

Recent dialogue:
Gareth Pinnock: I just want to say — this was a team effort.
Tim Blankenship: Sure.

Tim Blankenship just said: "Sure."
Now respond as Dwight Bramble.
```

**Confessional system message** strips the mode rules and replaces them with:
```
Tone: honest, concise, revealing.
RULES: one short line only. No narration. No stage directions. Reveal what the character really thinks.
```

---

## Output Post-Processing

After each LLM response:

1. **Extract first non-empty line** — ignore multi-line responses
2. **Strip markdown** — remove `**`, `##`, `*` prefixes
3. **Strip debate openers** — remove "I believe", "In my opinion", "Frankly" (Debate mode)
4. **Enforce speaker prefix** — if line doesn't start with `"Name:"`, prepend it; if it starts with a different character's name, strip and re-prefix

This ensures the script output is always clean `"Name: line"` format regardless of model behaviour.

---

## LLM Backend Abstraction

`OllamaClient` supports two backends via the `backend` parameter:

| Backend | Endpoint | Payload format | Response field |
|---------|----------|---------------|----------------|
| `lmstudio` | `/v1/chat/completions` | `{messages: [{role, content}]}` | `choices[0].message.content` |
| `ollama` | `/api/generate` | `{prompt, options: {num_predict, temperature}}` | `response` |

`generate_chat(system, user)` routes to the appropriate backend. For Ollama, system and user are concatenated into a single prompt string.

---

## Character File Schema

```json
{
  "name": "string (required)",
  "show": "English Office Comedy | Hindi Office Comedy (required)",
  "personality": "string (required)",
  "speaking_style": "string (required)",
  "catchphrases": ["string", "..."] (non-empty list, required),
  "kokoro_voice": "string (required, e.g. af_heart, am_michael)"
}
```

Files are stored as `characters/{name_lowercase_underscored}.json`. The `CharacterLoader` validates all six fields on load and skips invalid files with a warning.

---

## TTS Pipeline

When TTS is enabled and Kokoro is installed:

1. Strip `"Name: "` prefix from `turn.text` to get clean spoken text
2. Map `show_style` → `lang_code` (`en-us` or `hi`)
3. Call `KPipeline(lang_code)(text, voice=character.kokoro_voice)`
4. Collect `(graphemes, phonemes, audio_array)` tuples, concatenate audio arrays
5. Write WAV to `outputs/scene_YYYYMMDD_HHMMSS/{idx:02d}_{name}.wav` via `soundfile.write(..., samplerate=24000)`
6. On any exception: log error, return `None`, scene continues without audio for that turn

---

## Correctness Properties (Property-Based Tests)

The test suite uses [Hypothesis](https://hypothesis.readthedocs.io/) to verify 12 correctness properties:

| # | Property | Validates |
|---|----------|-----------|
| 1 | CharacterLoader loads all valid files | Req 2.1, 11.1 |
| 2 | CharacterLoader rejects missing fields | Req 2.3, 2.4 |
| 3 | OllamaClient embeds max_tokens in every payload | Req 3.4, 10.2 |
| 4 | OllamaClient returns fallback on non-2xx status | Req 3.7 |
| 5 | PromptBuilder includes all character identity fields | Req 4.1, 4.2 |
| 6 | PromptBuilder never exceeds transcript window size | Req 4.5 |
| 7 | SceneOrchestrator only uses characters matching show style | Req 5.1 |
| 8 | SceneOrchestrator sequences characters in round-robin order | Req 5.2 |
| 9 | Moderator correctly identifies exact repetition | Req 5.4 |
| 10 | SceneResult.as_script() contains all dialogue turns | Req 5.5 |
| 11 | KokoroTTS produces correctly named WAV files | Req 7.1–7.3 |
| 12 | Scene exchange count never exceeds 12 | Req 10.1 |

---

## Extension Points

| What to extend | How |
|----------------|-----|
| New show style | Add character JSON files with a new `show` value; update `gr.Radio` choices |
| New scene mode | Add entry to `MODE_CONFIG`; add `mode_instruction` and `mode_rules` branches |
| Streaming TTS | Replace `KokoroTTS.synthesize()` with a streaming variant; orchestrator loop unchanged |
| Persistent scene memory | Serialize `SceneResult` to `outputs/scene_*/scene.json` |
| Semantic repetition detection | Replace `_is_repetition()` with edit-distance or embedding check |
| Different LLM backend | Add a new branch in `OllamaClient.generate_chat()` |
