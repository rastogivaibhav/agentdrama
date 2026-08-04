# Requirements Document

## Introduction

Agentic Office Comedy is a fully offline, multi-agent comedy simulation application. Local AI agents role-play characters inspired by two comedy archetypes: English office cringe comedy (The Office US/UK style) and Hindi bureaucratic satire (Office Office style). Given a user-provided scenario, the system generates short improvised comedy scenes, optionally synthesizes each line into speech using a local TTS engine, and exposes all functionality through a Gradio web UI. The application runs entirely on local hardware after initial model downloads, targeting machines with 4 GB VRAM and 32 GB RAM.

---

## Glossary

- **App**: The Agentic Office Comedy application as a whole.
- **Scene**: A generated sequence of dialogue exchanges between characters for a given scenario.
- **Exchange**: A single spoken line by one character within a Scene.
- **Character**: A comedy archetype defined by a JSON file containing personality, speaking style, catchphrases, and voice assignment.
- **Character_Loader**: The component responsible for reading Character JSON files from the `characters/` directory and auto-creating sample files on first run.
- **Agent**: The component that constructs prompts and calls the LLM_Client to generate a single Exchange in-character.
- **Orchestrator**: The component that sequences Agents, maintains the running transcript, and enforces scene coherence rules.
- **LLM_Client**: The custom HTTP-based wrapper around the local Ollama API used for text generation.
- **TTS_Engine**: The local Kokoro TTS wrapper that synthesizes an Exchange into a WAV audio file.
- **UI**: The Gradio-based web interface through which users interact with the App.
- **Show_Style**: The user-selected comedy world — either "English Office Comedy" or "Hindi Office Comedy".
- **Transcript**: The lightweight rolling context window of prior Exchanges used to maintain scene continuity.
- **Output_Folder**: A scene-specific directory under `outputs/scene_<timestamp>/` where generated audio files are saved.
- **Moderator**: A lightweight rule layer within the Orchestrator that checks for repetition and incoherence before each Exchange is accepted.
- **Ollama**: The local LLM inference server used by the LLM_Client.
- **Kokoro**: The local TTS library (KPipeline) used by the TTS_Engine.

---

## Requirements

### Requirement 1: Offline-First Operation

**User Story:** As a user, I want the App to run fully offline after initial model downloads, so that I have no dependency on internet connectivity during use.

#### Acceptance Criteria

1. THE App SHALL perform all LLM inference through the local Ollama server without making external network calls during scene generation.
2. THE App SHALL perform all TTS synthesis through the local Kokoro library without making external network calls during audio generation.
3. WHEN Ollama is unavailable at generation time, THE LLM_Client SHALL return a graceful error message and THE Orchestrator SHALL surface that error to the UI without crashing.
4. WHEN Kokoro is not installed, THE TTS_Engine SHALL log a warning and THE UI SHALL disable the TTS checkbox with an explanatory status message.

---

### Requirement 2: Character System

**User Story:** As a developer, I want characters defined as JSON files in a `characters/` folder, so that the character set is easily extensible without modifying application code.

#### Acceptance Criteria

1. THE Character_Loader SHALL read Character definitions from JSON files located in the `characters/` directory.
2. WHEN the `characters/` directory does not exist or contains no JSON files on startup, THE Character_Loader SHALL auto-create sample Character JSON files for both the English Office Comedy set and the Hindi Office Comedy set.
3. THE Character_Loader SHALL require each Character JSON file to contain the fields: `name`, `show`, `personality`, `speaking_style`, `catchphrases`, and `kokoro_voice`.
4. IF a Character JSON file is missing any required field, THEN THE Character_Loader SHALL log a warning and skip that Character.
5. THE App SHALL include at least four sample Characters for the English Office Comedy set: a cringe overconfident manager archetype, a dry deadpan colleague archetype, an intense literal self-important colleague archetype, and an observant restrained receptionist archetype.
6. THE App SHALL include at least four sample Characters for the Hindi Office Comedy set: a frustrated common-man petitioner archetype, a slippery evasive corrupt official archetype, a bureaucratic rule-reciting clerk archetype, and a pompous dismissive supervisor archetype.

---

### Requirement 3: LLM Client

**User Story:** As a developer, I want a custom Ollama HTTP client, so that the App has full IP ownership of its orchestration logic without depending on external agent frameworks.

#### Acceptance Criteria

1. THE LLM_Client SHALL communicate with the Ollama API exclusively via standard HTTP requests using Python's built-in or lightweight HTTP libraries.
2. THE LLM_Client SHALL NOT use CrewAI, LangGraph, AutoGen, PydanticAI, or any external agent orchestration framework.
3. THE LLM_Client SHALL accept a configurable model name, defaulting to `qwen2.5:4b` or `gemma3:4b` as specified in application configuration.
4. THE LLM_Client SHALL cap generated output at a configurable maximum token count to limit VRAM usage and latency.
5. THE LLM_Client SHALL use a low but non-zero temperature setting for generation to balance creativity and coherence.
6. WHEN an Ollama API request exceeds a configurable timeout threshold, THE LLM_Client SHALL raise a timeout error and return a fallback error string to the caller.
7. IF the Ollama server returns a non-success HTTP status, THEN THE LLM_Client SHALL log the error details and return a descriptive fallback string.
8. THE LLM_Client SHALL perform all generation sequentially with no parallel requests.

---

### Requirement 4: Agent and Prompt Design

**User Story:** As a developer, I want each Agent to generate short, in-character lines using optimized prompts, so that generation is fast on low-end hardware.

#### Acceptance Criteria

1. THE Agent SHALL construct a prompt that includes the Character's name, personality, speaking style, and a sample catchphrase.
2. THE Agent SHALL include the current Transcript window in the prompt to maintain scene continuity.
3. THE Agent SHALL instruct the LLM_Client to produce a single short Exchange line prefixed with the Character's name.
4. THE Agent SHALL NOT use chain-of-thought style prompting or multi-step reasoning instructions.
5. THE Agent SHALL keep prompt length short by limiting the Transcript window to a configurable number of recent Exchanges, defaulting to the last 4 Exchanges.

---

### Requirement 5: Scene Orchestration

**User Story:** As a user, I want the system to automatically sequence characters and manage scene flow, so that I receive a coherent comedy scene without manual intervention.

#### Acceptance Criteria

1. WHEN a user submits a scenario, THE Orchestrator SHALL select all Characters matching the chosen Show_Style.
2. THE Orchestrator SHALL sequence selected Characters in a round-robin order for each Exchange until the configured number of Exchanges is reached.
3. THE Orchestrator SHALL maintain a running Transcript of all accepted Exchanges and pass the most recent window to each Agent.
4. THE Moderator SHALL check each generated Exchange for exact repetition of a prior Exchange and, WHEN repetition is detected, THE Orchestrator SHALL request a regeneration from the same Agent up to two additional times before accepting the output regardless.
5. WHEN all Exchanges are generated, THE Orchestrator SHALL return the complete Scene as a formatted script string with speaker names prefixed to each line.

---

### Requirement 6: User Interface

**User Story:** As a user, I want a simple Gradio web UI, so that I can generate comedy scenes without using the command line.

#### Acceptance Criteria

1. THE UI SHALL provide a radio button group for selecting Show_Style with options "English Office Comedy" and "Hindi Office Comedy".
2. THE UI SHALL provide a text input for the user to enter a scenario, pre-populated with a default example scenario.
3. THE UI SHALL provide a slider for selecting the number of Exchanges, with a minimum of 4, a maximum of 12, and a default of 6.
4. THE UI SHALL provide a checkbox to enable or disable TTS synthesis, defaulting to disabled.
5. THE UI SHALL provide a button to trigger scene generation.
6. THE UI SHALL display the generated script in a read-only text area or code block after generation completes.
7. WHEN TTS is enabled and audio files are generated, THE UI SHALL display an audio player for the most recently generated Exchange audio file.
8. WHEN TTS is enabled and audio files are generated, THE UI SHALL display a file list or gallery of all audio files in the Output_Folder for the current Scene.
9. THE UI SHALL display a status or error message area that surfaces setup issues, Ollama unavailability, or TTS failures to the user.
10. THE UI SHALL include a set of at least six default scenario examples selectable by the user.

---

### Requirement 7: TTS Synthesis

**User Story:** As a user, I want each character's line optionally synthesized to speech using a distinct voice, so that the scene is more immersive and entertaining.

#### Acceptance Criteria

1. WHEN TTS is enabled, THE TTS_Engine SHALL synthesize each Exchange into a WAV audio file using the Kokoro KPipeline library.
2. THE TTS_Engine SHALL use the `kokoro_voice` field from the Character's JSON definition to select the voice for that Character's Exchange.
3. THE TTS_Engine SHALL save each WAV file into the Output_Folder for the current Scene, named to reflect the Exchange sequence number and Character name.
4. THE TTS_Engine SHALL use the `soundfile` library to write WAV files to disk.
5. WHEN TTS is disabled, THE TTS_Engine SHALL NOT be invoked and no audio files SHALL be created.
6. IF Kokoro synthesis raises an exception for a given Exchange, THEN THE TTS_Engine SHALL log the error and continue processing remaining Exchanges without halting the scene.
7. THE TTS_Engine SHALL perform synthesis synchronously and sequentially, one Exchange at a time.

---

### Requirement 8: Output File Handling

**User Story:** As a user, I want generated audio files organized in a timestamped folder, so that I can easily find and replay scenes.

#### Acceptance Criteria

1. THE App SHALL create a scene-specific Output_Folder at path `outputs/scene_<timestamp>/` before writing any audio files, where `<timestamp>` is an ISO-format or sortable datetime string.
2. THE App SHALL use `pathlib.Path` for all file and directory path operations.
3. WHEN an Output_Folder cannot be created due to a filesystem error, THE App SHALL log the error and disable TTS for that Scene without crashing.

---

### Requirement 9: Application Structure and Code Quality

**User Story:** As a developer, I want the entire application in a single well-structured Python script, so that it is easy to deploy, audit, and extend.

#### Acceptance Criteria

1. THE App SHALL be implemented as a single Python script using Python 3.10 or later syntax.
2. THE App SHALL use dataclasses to represent structured data such as Character definitions and Scene results.
3. THE App SHALL use type hints on all function signatures.
4. THE App SHALL use `pathlib.Path` for all path operations rather than string concatenation.
5. THE App SHALL include a header comment block containing: installation instructions, the minimal dependency list, instructions for running Ollama and pulling the required model, and instructions for installing Kokoro and soundfile.
6. THE App SHALL include inline comments explaining key design decisions, particularly around prompt construction, transcript windowing, and TTS fallback behavior.
7. THE App SHALL use Python's standard `logging` module for all diagnostic output rather than bare `print` statements.
8. THE App SHALL contain no pseudocode, placeholder functions, or unimplemented stubs.

---

### Requirement 10: Performance Constraints

**User Story:** As a user on low-end hardware, I want the App to stay within 4 GB VRAM and complete scene generation in a reasonable time, so that the experience is usable on my machine.

#### Acceptance Criteria

1. THE App SHALL limit the number of Exchanges per Scene to a maximum of 12.
2. THE LLM_Client SHALL cap max tokens per generation call at a configurable value sized to keep individual inference calls fast on a 4 GB VRAM GPU.
3. THE App SHALL NOT use a vector database, embedding model, or heavy memory system.
4. THE App SHALL NOT perform parallel LLM generation calls.
5. THE App SHALL NOT load more than one LLM model simultaneously.

---

### Requirement 11: Extensibility

**User Story:** As a developer, I want the architecture to support future enhancements without major refactoring, so that the App can grow over time.

#### Acceptance Criteria

1. THE Character_Loader SHALL support loading additional Character JSON files placed in the `characters/` directory without requiring code changes.
2. THE Orchestrator SHALL be designed so that persistent memory between Scenes can be added by extending the Transcript data structure.
3. THE App SHALL be structured so that additional Show_Style comedy worlds can be added by creating new Character JSON files and updating the Show_Style selection list.
4. THE App SHALL be structured so that scene saving and loading can be added by serializing and deserializing the Scene result dataclass.
