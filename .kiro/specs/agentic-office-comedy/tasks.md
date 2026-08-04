# Implementation Plan: Agentic Office Comedy

## Overview

Implement `agentic_office_comedy.py` as a single Python script with all components wired together: data models, character loading, Ollama HTTP client, prompt building, scene orchestration, optional Kokoro TTS, and a Gradio web UI. The implementation follows the design document exactly, using dataclasses, `pathlib.Path`, `urllib.request`, and Python's `logging` module throughout.

## Tasks

- [x] 1. Project scaffolding and data models
  - Create `agentic_office_comedy.py` with the header comment block (installation instructions, dependency list, Ollama setup, Kokoro setup)
  - Set up `logging` configuration at module level
  - Create the `characters/` and `outputs/` directories (via `pathlib.Path.mkdir(exist_ok=True)`)
  - Implement all four dataclasses: `Character`, `DialogueTurn`, `GenerationConfig`, `SceneResult` with `as_script()` and `audio_paths()` methods
  - Add type hints to all dataclass fields and methods
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 2. CharacterLoader implementation
  - [x] 2.1 Implement `CharacterLoader.__init__` and `load_all()`
    - Scan `characters_dir` for `*.json` files, call `_load_file` on each, skip invalid with a warning, return valid list
    - Call `_auto_create_samples()` when no JSON files are found
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 2.2 Implement `CharacterLoader._load_file()`
    - Validate all six required fields; return `None` and log a warning if any are missing
    - Return a populated `Character` dataclass on success
    - _Requirements: 2.3, 2.4_

  - [x] 2.3 Write property test for CharacterLoader valid file loading
    - **Property 1: CharacterLoader loads all valid character files**
    - **Validates: Requirements 2.1, 11.1**

  - [x] 2.4 Write property test for CharacterLoader missing-field rejection
    - **Property 2: CharacterLoader rejects files missing any required field**
    - **Validates: Requirements 2.3, 2.4**

  - [x] 2.5 Implement `CharacterLoader._auto_create_samples()`
    - Write four English Office Comedy character JSON files (manager, deadpan colleague, intense colleague, receptionist archetypes)
    - Write four Hindi Office Comedy character JSON files (petitioner, corrupt official, clerk, supervisor archetypes)
    - _Requirements: 2.5, 2.6_

  - [x] 2.6 Write unit tests for `_auto_create_samples()`
    - Verify files are created for both show styles when `characters/` is empty
    - _Requirements: 2.5, 2.6_

- [x] 3. OllamaClient implementation
  - [x] 3.1 Implement `OllamaClient.__init__` and `generate()`
    - Use `urllib.request` to POST to `/api/generate` with `stream=False`
    - Parse JSON response and return the `response` field
    - Include `max_tokens` (as `num_predict`) and `temperature` in every request payload
    - Return fallback string on timeout or non-2xx status; log errors
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 3.2 Implement `OllamaClient.is_available()`
    - Send a lightweight GET to `/` and return `True` on success, `False` on any exception
    - _Requirements: 1.3_

  - [x] 3.3 Write property test for OllamaClient max_tokens embedding
    - **Property 3: OllamaClient embeds max_tokens in every request payload**
    - **Validates: Requirements 3.4, 10.2**

  - [x] 3.4 Write property test for OllamaClient non-2xx fallback
    - **Property 4: OllamaClient returns a fallback string for any non-2xx HTTP status**
    - **Validates: Requirements 3.7**

  - [x] 3.5 Write unit tests for OllamaClient error paths
    - Test timeout returns fallback string (Requirement 3.6)
    - Test connection error returns fallback string (Requirement 1.3)
    - _Requirements: 1.3, 3.6_

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. PromptBuilder implementation
  - [x] 5.1 Implement `PromptBuilder.__init__` and `build()`
    - Select last `transcript_window_size` turns from the transcript
    - Format the prompt with character identity block, scene context block, and instruction block
    - Include `name`, `personality`, `speaking_style`, one catchphrase, scenario, and transcript window
    - Instruct the model to respond with one short line prefixed by the character's name
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 5.2 Write property test for PromptBuilder content completeness
    - **Property 5: PromptBuilder includes all character identity and transcript context**
    - **Validates: Requirements 4.1, 4.2**

  - [x] 5.3 Write property test for PromptBuilder transcript window size
    - **Property 6: PromptBuilder never exceeds the configured transcript window size**
    - **Validates: Requirements 4.5**

- [x] 6. SceneOrchestrator implementation
  - [x] 6.1 Implement `SceneOrchestrator.__init__` and `_get_characters_for_style()`
    - Filter characters list by `show_style` field
    - _Requirements: 5.1_

  - [x] 6.2 Implement `SceneOrchestrator.run_scene()` — core loop
    - Filter characters, return error `SceneResult` if fewer than 2 match
    - Create `output_folder` when TTS is enabled; disable TTS on filesystem error
    - Run round-robin loop for `num_exchanges` turns: build prompt → generate → parse response
    - Append accepted `DialogueTurn` to transcript
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 8.1, 8.2, 8.3_

  - [x] 6.3 Implement `_is_repetition()` Moderator helper
    - Case-insensitive exact match of new exchange text against all prior turn texts
    - Retry up to 2 additional times on repetition detection
    - _Requirements: 5.4_

  - [x] 6.4 Write property test for show-style character filtering
    - **Property 7: SceneOrchestrator only uses characters matching the selected show style**
    - **Validates: Requirements 5.1**

  - [x] 6.5 Write property test for round-robin sequencing
    - **Property 8: SceneOrchestrator sequences characters in strict round-robin order**
    - **Validates: Requirements 5.2**

  - [x] 6.6 Write property test for Moderator repetition detection
    - **Property 9: Moderator correctly identifies exact repetition**
    - **Validates: Requirements 5.4**

  - [x] 6.7 Write property test for SceneResult.as_script() completeness
    - **Property 10: SceneResult.as_script() contains all dialogue turns**
    - **Validates: Requirements 5.5**

  - [x] 6.8 Write property test for exchange count cap
    - **Property 12: Scene exchange count never exceeds the configured maximum**
    - **Validates: Requirements 10.1**

  - [x] 6.9 Write unit tests for SceneOrchestrator error paths
    - Test TTS disabled produces no audio files (Requirement 7.5)
    - Test filesystem error disables TTS gracefully (Requirement 8.3)
    - _Requirements: 7.5, 8.3_

- [x] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. KokoroTTS implementation
  - [x] 8.1 Implement `KokoroTTS.__init__`
    - Import `KPipeline` inside `__init__`; raise `ImportError` if not installed
    - _Requirements: 1.4, 7.1_

  - [x] 8.2 Implement `KokoroTTS.synthesize()`
    - Extract spoken text by stripping the `"Speaker: "` prefix
    - Infer `lang_code` from `show_style` (`"en-us"` or `"hi"` with fallback warning)
    - Call `KPipeline` with the character's `kokoro_voice`, collect audio chunks, concatenate
    - Write WAV to `output_folder / f"{i:02d}_{character.name.replace(' ', '_')}.wav"` via `soundfile.write()`
    - Return `Path` on success; log error and return `None` on exception
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7_

  - [x] 8.3 Write property test for KokoroTTS file naming and voice selection
    - **Property 11: KokoroTTS produces correctly named WAV files using the character's voice**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 8.4 Write unit test for KokoroTTS exception handling
    - Test that `synthesize()` returns `None` on Kokoro exception without halting the scene
    - _Requirements: 7.6_

- [x] 9. Gradio UI implementation
  - [x] 9.1 Implement the `create_app()` factory function
    - Build `gr.Blocks` layout with: `gr.Radio` for Show_Style, `gr.Textbox` for scenario, `gr.Slider` for exchange count (4–12, default 6), `gr.Checkbox` for TTS (disabled when `tts_available=False`), `gr.Button` to generate
    - Add read-only `gr.Textbox` for script output, `gr.Audio` for last audio, `gr.File` for full audio list, `gr.Textbox` for status/errors
    - Add `gr.Examples` with at least six default scenarios
    - Wire the generate button to a handler that calls `SceneOrchestrator.run_scene()` and populates all outputs
    - Surface Ollama unavailability and TTS status in the status area on load
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_

- [x] 10. Integration wiring and main entry point
  - [x] 10.1 Wire all components together at module level
    - Instantiate `CharacterLoader` and call `load_all()` at startup
    - Attempt `KokoroTTS()` construction in try/except; set `tts_available` flag
    - Check `OllamaClient.is_available()` at startup; log warning if unreachable
    - Instantiate `PromptBuilder`, `OllamaClient`, and `SceneOrchestrator` with loaded characters
    - Pass `tts_available` to `create_app()`
    - _Requirements: 1.3, 1.4, 9.8_

  - [x] 10.2 Implement `if __name__ == "__main__":` entry point
    - Call `create_app().launch()` to start the Gradio server
    - _Requirements: 9.1_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use **Hypothesis** with `@given` decorators; each is tagged with its property number from the design document
- Unit tests cover error paths and startup behavior not covered by property tests
- All property tests should be placed in `tests/test_properties.py`; unit tests in `tests/test_unit.py`
- The single script `agentic_office_comedy.py` must contain no stubs or placeholder functions (Requirement 9.8)
