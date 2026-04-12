"""
Property-based tests for agentic_office_comedy.py
Uses Hypothesis for property-based testing.
"""

import json
import sys
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure the workspace root is on the path so we can import the main script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic_office_comedy import CharacterLoader, Character, OllamaClient, PromptBuilder, DialogueTurn


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def valid_character_strategy():
    """Generate valid character dicts with all 6 required fields."""
    return st.fixed_dictionaries({
        "name": st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        "show": st.sampled_from(["English Office Comedy", "Hindi Office Comedy"]),
        "personality": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        "speaking_style": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        "catchphrases": st.lists(
            st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
            min_size=1,
            max_size=5,
        ),
        "kokoro_voice": st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    })


# ---------------------------------------------------------------------------
# Property 1: CharacterLoader loads all valid character files
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 1: CharacterLoader loads all valid character files
@settings(max_examples=100)
@given(st.lists(valid_character_strategy(), min_size=1, max_size=10))
def test_character_loader_loads_all_valid_files(characters):
    """
    **Validates: Requirements 2.1, 11.1**

    For any collection of valid character JSON files placed in the characters
    directory, CharacterLoader.load_all() shall return a list containing exactly
    one Character object per file, with all fields correctly populated.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write each character dict as a JSON file to the temp directory
        for i, char_dict in enumerate(characters):
            file_path = tmp_path / f"character_{i}.json"
            with file_path.open("w", encoding="utf-8") as fh:
                json.dump(char_dict, fh)

        # Create a CharacterLoader pointing to the temp directory
        loader = CharacterLoader(tmp_path)

        # Call load_all() — files are already written so _auto_create_samples won't be triggered
        loaded = loader.load_all()

        # Assert the returned list has exactly the same length as the input list
        assert len(loaded) == len(characters), (
            f"Expected {len(characters)} characters, got {len(loaded)}"
        )

        # Convert to comparable tuples and sort both sides to handle:
        # - non-deterministic glob ordering
        # - duplicate names across generated characters
        def to_tuple(name, show, personality, speaking_style, catchphrases, kokoro_voice):
            return (name, show, personality, speaking_style, tuple(catchphrases), kokoro_voice)

        input_tuples = sorted(
            to_tuple(d["name"], d["show"], d["personality"], d["speaking_style"],
                     d["catchphrases"], d["kokoro_voice"])
            for d in characters
        )
        loaded_tuples = sorted(
            to_tuple(c.name, c.show, c.personality, c.speaking_style,
                     c.catchphrases, c.kokoro_voice)
            for c in loaded
        )

        assert input_tuples == loaded_tuples, (
            "Loaded characters do not match input characters field-for-field"
        )


# ---------------------------------------------------------------------------
# Property 2: CharacterLoader rejects files missing any required field
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 2: CharacterLoader rejects files missing any required field
@settings(max_examples=100)
@given(
    valid_character_strategy(),
    st.sampled_from(["name", "show", "personality", "speaking_style", "catchphrases", "kokoro_voice"]),
)
def test_character_loader_rejects_missing_field(char_dict, missing_field):
    """
    **Validates: Requirements 2.3, 2.4**

    For any character dict with any single required field removed,
    CharacterLoader._load_file() shall return None rather than a Character object.
    """
    # Remove the field under test
    incomplete = dict(char_dict)
    del incomplete[missing_field]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        import json as _json
        _json.dump(incomplete, fh)
        tmp_path = Path(fh.name)

    try:
        loader = CharacterLoader(tmp_path.parent)
        result = loader._load_file(tmp_path)
        assert result is None, (
            f"Expected None when '{missing_field}' is missing, got {result!r}"
        )
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Property 3: OllamaClient embeds max_tokens in every request payload
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 3: OllamaClient embeds max_tokens in every request payload
@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=2048), st.text(min_size=1))
def test_ollama_client_embeds_max_tokens(max_tokens, prompt):
    """
    **Validates: Requirements 3.4, 10.2**

    For any max_tokens value passed to OllamaClient, every call to generate()
    shall include that exact value in the JSON payload sent to the Ollama API
    endpoint as options.num_predict.
    """
    import io
    import unittest.mock

    client = OllamaClient(
        model="test-model",
        base_url="http://localhost:11434",
        max_tokens=max_tokens,
        temperature=0.7,
        timeout=30.0,
    )

    captured_body = {}

    mock_response_data = json.dumps({"response": "test response", "done": True}).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        captured_body["data"] = request.data
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
        return mock_resp

    with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client.generate(prompt)

    assert "data" in captured_body, "urlopen was never called"
    payload = json.loads(captured_body["data"].decode("utf-8"))
    assert payload["options"]["num_predict"] == max_tokens, (
        f"Expected num_predict={max_tokens}, got {payload['options'].get('num_predict')}"
    )


# ---------------------------------------------------------------------------
# Property 4: OllamaClient returns a fallback string for any non-2xx HTTP status
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 4: OllamaClient returns a fallback string for any non-2xx HTTP status
@settings(max_examples=100)
@given(st.integers(min_value=400, max_value=599), st.text(min_size=1))
def test_ollama_client_fallback_on_non_2xx(status_code, prompt):
    """
    **Validates: Requirements 3.7**

    For any HTTP status code >= 400 returned by the Ollama server,
    OllamaClient.generate() shall return a non-empty fallback string rather
    than raising an exception.
    """
    import unittest.mock
    import urllib.error

    client = OllamaClient(
        model="test-model",
        base_url="http://localhost:11434",
        max_tokens=150,
        temperature=0.7,
        timeout=30.0,
    )

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=status_code,
            msg=f"HTTP Error {status_code}",
            hdrs=None,
            fp=None,
        )

    with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = client.generate(prompt)

    # Must return a non-empty string (not raise an exception)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert len(result) > 0, "Fallback string must be non-empty"

    # Must NOT be the actual Ollama response (it's a fallback, not real output)
    assert "response" not in result.lower() or result.startswith("["), (
        f"Result looks like a real response rather than a fallback: {result!r}"
    )


def dialogue_turn_strategy():
    """Generate dicts with 'speaker' and 'text' fields for DialogueTurn construction."""
    return st.fixed_dictionaries({
        "speaker": st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        "text": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    })


# ---------------------------------------------------------------------------
# Property 5: PromptBuilder includes all character identity and transcript context
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 5: PromptBuilder includes all character identity and transcript context
@settings(max_examples=100)
@given(valid_character_strategy(), st.lists(dialogue_turn_strategy(), min_size=0, max_size=10), st.text(min_size=1))
def test_prompt_builder_content_completeness(char_dict, turns_data, scenario):
    """
    **Validates: Requirements 4.1, 4.2**

    For any Character and any transcript window, PromptBuilder.build() shall
    return a string that contains the character's name, personality,
    speaking_style, at least one catchphrase, and the text of every
    DialogueTurn in the provided window (last 4 turns).
    """
    # 1. Build a Character from the generated dict
    character = Character(
        name=char_dict["name"],
        show=char_dict["show"],
        personality=char_dict["personality"],
        speaking_style=char_dict["speaking_style"],
        catchphrases=char_dict["catchphrases"],
        kokoro_voice=char_dict["kokoro_voice"],
    )

    # 2. Build a list of DialogueTurn objects from the turns data
    transcript = [DialogueTurn(speaker=t["speaker"], text=t["text"]) for t in turns_data]

    # 3. Create a PromptBuilder with default window size (4)
    builder = PromptBuilder()

    # 4. Call build(character, transcript, scenario)
    prompt = builder.build(character, transcript, scenario)

    # 5. Assert the prompt contains character.name
    assert character.name in prompt, (
        f"Prompt missing character name '{character.name}'"
    )

    # 6. Assert the prompt contains character.personality
    assert character.personality in prompt, (
        f"Prompt missing personality '{character.personality}'"
    )

    # 7. Assert the prompt contains character.speaking_style
    assert character.speaking_style in prompt, (
        f"Prompt missing speaking_style '{character.speaking_style}'"
    )

    # 8. Assert the prompt contains at least one of character.catchphrases
    assert any(phrase in prompt for phrase in character.catchphrases), (
        f"Prompt missing all catchphrases: {character.catchphrases}"
    )

    # 9. Assert the prompt contains the text of every turn in the window (last 4 turns)
    window = transcript[-4:]
    for turn in window:
        assert turn.text in prompt, (
            f"Prompt missing dialogue turn text '{turn.text}'"
        )


# ---------------------------------------------------------------------------
# Property 6: PromptBuilder never exceeds the configured transcript window size
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 6: PromptBuilder never exceeds the configured transcript window size
@settings(max_examples=100)
@given(
    valid_character_strategy(),
    st.integers(min_value=1, max_value=8),   # window_size
    st.integers(min_value=1, max_value=20),  # extra_turns (transcript length = window_size + extra_turns)
    st.text(min_size=1),
)
def test_prompt_builder_transcript_window_size(char_dict, window_size, extra_turns, scenario):
    """
    **Validates: Requirements 4.5**

    For any transcript of length greater than transcript_window_size,
    PromptBuilder.build() shall include at most transcript_window_size turns
    in the prompt, always taking the most recent ones.
    """
    # 1. Build a Character from the generated dict
    character = Character(
        name=char_dict["name"],
        show=char_dict["show"],
        personality=char_dict["personality"],
        speaking_style=char_dict["speaking_style"],
        catchphrases=char_dict["catchphrases"],
        kokoro_voice=char_dict["kokoro_voice"],
    )

    # 2. Create a transcript with window_size + extra_turns turns (more than the window).
    #    Use the index as part of the text to make each turn uniquely distinguishable.
    total_turns = window_size + extra_turns
    transcript = [
        DialogueTurn(speaker=f"Speaker{i}", text=f"UNIQUE_TURN_TEXT_{i}_END")
        for i in range(total_turns)
    ]

    # 3. Create a PromptBuilder with transcript_window_size=window_size
    builder = PromptBuilder(transcript_window_size=window_size)

    # 4. Call build(character, transcript, scenario)
    prompt = builder.build(character, transcript, scenario)

    # 5. Assert that the turns OUTSIDE the window (the oldest ones) are NOT in the prompt.
    #    The oldest `extra_turns` turns (indices 0 .. extra_turns-1) must be absent.
    outside_window = transcript[:extra_turns]
    for turn in outside_window:
        assert turn.text not in prompt, (
            f"Prompt should NOT contain old turn '{turn.text}' "
            f"(window_size={window_size}, total_turns={total_turns})"
        )

    # 6. Assert that the turns INSIDE the window (the most recent window_size turns) ARE in the prompt.
    inside_window = transcript[-window_size:]
    for turn in inside_window:
        assert turn.text in prompt, (
            f"Prompt should contain recent turn '{turn.text}' "
            f"(window_size={window_size}, total_turns={total_turns})"
        )


# ---------------------------------------------------------------------------
# Shared helpers for SceneOrchestrator property tests
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock
from agentic_office_comedy import (
    SceneOrchestrator,
    GenerationConfig,
    SceneResult,
)


def make_mock_ollama(responses=None):
    """Create a mock OllamaClient that returns canned responses."""
    mock = MagicMock()
    if responses:
        mock.generate.side_effect = responses
    else:
        counter = [0]
        def gen(prompt):
            counter[0] += 1
            return f"Speaker: Line {counter[0]}"
        mock.generate.side_effect = gen
    return mock


def make_character(name: str, show: str) -> Character:
    return Character(
        name=name,
        show=show,
        personality="test personality",
        speaking_style="test style",
        catchphrases=["test catchphrase"],
        kokoro_voice="af_heart",
    )


# ---------------------------------------------------------------------------
# Property 7: SceneOrchestrator only uses characters matching the selected show style
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 7: SceneOrchestrator only uses characters matching the selected show style
@settings(max_examples=50)
@given(
    st.lists(
        st.fixed_dictionaries({
            "name": st.text(min_size=1, max_size=30).filter(lambda s: s.strip()),
            "show": st.sampled_from(["English Office Comedy", "Hindi Office Comedy"]),
        }),
        min_size=2,
        max_size=8,
    ),
    st.sampled_from(["English Office Comedy", "Hindi Office Comedy"]),
    st.integers(min_value=4, max_value=8),
)
def test_scene_orchestrator_show_style_filtering(char_specs, show_style, num_exchanges):
    """
    **Validates: Requirements 5.1**

    For any mixed collection of characters spanning multiple show styles and any
    chosen show_style, every DialogueTurn in the returned SceneResult shall have
    a speaker that belongs to a character whose show field equals show_style.
    """
    # Build characters from specs, ensuring at least 2 match the chosen style
    characters = [make_character(spec["name"], spec["show"]) for spec in char_specs]

    # Count how many match the chosen style
    matching = [c for c in characters if c.show == show_style]
    if len(matching) < 2:
        # Inject two guaranteed matching characters so the scene can run
        characters.append(make_character("Alpha", show_style))
        characters.append(make_character("Beta", show_style))
        matching = [c for c in characters if c.show == show_style]

    # Deduplicate names within the matching set to avoid round-robin confusion
    seen_names = set()
    unique_matching = []
    for c in matching:
        if c.name not in seen_names:
            seen_names.add(c.name)
            unique_matching.append(c)
    if len(unique_matching) < 2:
        unique_matching = [make_character("Alpha", show_style), make_character("Beta", show_style)]

    # Rebuild full character list with unique matching chars + non-matching chars
    non_matching = [c for c in characters if c.show != show_style]
    all_characters = unique_matching + non_matching

    orchestrator = SceneOrchestrator(
        characters=all_characters,
        ollama=make_mock_ollama(),
        prompt_builder=PromptBuilder(),
        tts=None,
    )

    config = GenerationConfig(
        show_style=show_style,
        scenario="test scenario",
        num_exchanges=num_exchanges,
        tts_enabled=False,
    )

    result = orchestrator.run_scene(config)

    assert result.error is None, f"Scene returned error: {result.error}"

    # Build the set of names that belong to the chosen style
    valid_speaker_names = {c.name for c in all_characters if c.show == show_style}

    for turn in result.turns:
        assert turn.speaker in valid_speaker_names, (
            f"Turn speaker '{turn.speaker}' does not belong to show_style '{show_style}'. "
            f"Valid speakers: {valid_speaker_names}"
        )


# ---------------------------------------------------------------------------
# Property 8: SceneOrchestrator sequences characters in strict round-robin order
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 8: SceneOrchestrator sequences characters in strict round-robin order
@settings(max_examples=50)
@given(
    st.integers(min_value=2, max_value=6),   # N characters
    st.integers(min_value=2, max_value=12),  # M exchanges
)
def test_scene_orchestrator_round_robin_sequencing(n_chars, num_exchanges):
    """
    **Validates: Requirements 5.2**

    For any list of N characters (N >= 2) and any number of exchanges M, the
    speaker at position i in SceneResult.turns shall be characters[i % N].name.
    """
    show_style = "English Office Comedy"
    characters = [make_character(f"Character{i}", show_style) for i in range(n_chars)]

    # Each generate() call returns a unique line so no repetition is detected
    counter = [0]
    def unique_gen(prompt):
        counter[0] += 1
        return f"UniqueResponse{counter[0]}: line content"

    mock_ollama = MagicMock()
    mock_ollama.generate.side_effect = unique_gen

    orchestrator = SceneOrchestrator(
        characters=characters,
        ollama=mock_ollama,
        prompt_builder=PromptBuilder(),
        tts=None,
    )

    config = GenerationConfig(
        show_style=show_style,
        scenario="test scenario",
        num_exchanges=num_exchanges,
        tts_enabled=False,
    )

    result = orchestrator.run_scene(config)

    assert result.error is None, f"Scene returned error: {result.error}"
    assert len(result.turns) == num_exchanges, (
        f"Expected {num_exchanges} turns, got {len(result.turns)}"
    )

    for i, turn in enumerate(result.turns):
        expected_speaker = characters[i % n_chars].name
        assert turn.speaker == expected_speaker, (
            f"Turn {i}: expected speaker '{expected_speaker}', got '{turn.speaker}'"
        )


# ---------------------------------------------------------------------------
# Property 9: Moderator correctly identifies exact repetition
# ---------------------------------------------------------------------------

from agentic_office_comedy import SceneOrchestrator as _SO  # already imported above

# Feature: agentic-office-comedy, Property 9: Moderator correctly identifies exact repetition
@settings(max_examples=100)
@given(
    st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    st.lists(
        st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        min_size=0,
        max_size=10,
    ),
)
def test_moderator_repetition_detection(exchange_text, prior_texts):
    """
    **Validates: Requirements 5.4**

    For any exchange text that is an exact case-insensitive match of any prior
    turn's text, _is_repetition() shall return True; for any exchange text that
    does not match any prior turn, it shall return False.
    """
    transcript = [DialogueTurn(speaker=f"S{i}", text=t) for i, t in enumerate(prior_texts)]
    candidate = DialogueTurn(speaker="TestSpeaker", text=exchange_text)

    result = SceneOrchestrator._is_repetition(candidate, transcript)

    # Determine expected result: True iff exchange_text matches any prior text case-insensitively
    expected = any(t.lower() == exchange_text.lower() for t in prior_texts)

    assert result == expected, (
        f"_is_repetition returned {result} but expected {expected}. "
        f"exchange_text={exchange_text!r}, prior_texts={prior_texts!r}"
    )


# ---------------------------------------------------------------------------
# Property 10: SceneResult.as_script() contains all dialogue turns
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 10: SceneResult.as_script() contains all dialogue turns
@settings(max_examples=100)
@given(
    st.lists(
        st.fixed_dictionaries({
            "speaker": st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
            "text": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        }),
        min_size=0,
        max_size=12,
    )
)
def test_scene_result_as_script_completeness(turns_data):
    """
    **Validates: Requirements 5.5**

    For any list of DialogueTurn objects, SceneResult.as_script() shall return
    a string that contains the text of every turn in the list, in order.
    """
    turns = [DialogueTurn(speaker=t["speaker"], text=t["text"]) for t in turns_data]

    config = GenerationConfig(
        show_style="English Office Comedy",
        scenario="test",
        num_exchanges=len(turns),
        tts_enabled=False,
    )
    result = SceneResult(config=config, turns=turns)

    script = result.as_script()

    assert isinstance(script, str), "as_script() must return a string"

    # Every turn's text must appear in the script
    for i, turn in enumerate(turns):
        assert turn.text in script, (
            f"Turn {i} text {turn.text!r} not found in script"
        )

    # Verify ordering: each turn's text appears after all previous turns' texts
    # We search for each text in the portion of the script after the previous match.
    search_pos = 0
    for i, turn in enumerate(turns):
        idx = script.find(turn.text, search_pos)
        assert idx != -1, (
            f"Turn {i} text {turn.text!r} not found in script at or after position {search_pos}"
        )
        search_pos = idx + len(turn.text)


# ---------------------------------------------------------------------------
# Property 12: Scene exchange count never exceeds the configured maximum
# ---------------------------------------------------------------------------

# Feature: agentic-office-comedy, Property 12: Scene exchange count never exceeds the configured maximum
@settings(max_examples=50)
@given(
    st.integers(min_value=1, max_value=100),  # num_exchanges — including values > 12
)
def test_scene_exchange_count_cap(num_exchanges):
    """
    **Validates: Requirements 10.1**

    For any GenerationConfig with num_exchanges set to any value,
    SceneResult.turns shall contain at most 12 DialogueTurn objects.
    """
    show_style = "English Office Comedy"
    characters = [
        make_character("Alice", show_style),
        make_character("Bob", show_style),
    ]

    orchestrator = SceneOrchestrator(
        characters=characters,
        ollama=make_mock_ollama(),
        prompt_builder=PromptBuilder(),
        tts=None,
    )

    config = GenerationConfig(
        show_style=show_style,
        scenario="test scenario",
        num_exchanges=num_exchanges,
        tts_enabled=False,
    )

    result = orchestrator.run_scene(config)

    assert result.error is None, f"Scene returned error: {result.error}"
    assert len(result.turns) <= 12, (
        f"Expected at most 12 turns, got {len(result.turns)} "
        f"(num_exchanges={num_exchanges})"
    )


# ---------------------------------------------------------------------------
# Property 11: KokoroTTS produces correctly named WAV files using the character's voice
# ---------------------------------------------------------------------------

import types
import sys as _sys
import numpy as np
from unittest.mock import MagicMock, patch
from agentic_office_comedy import KokoroTTS


def _make_kokoro_mocks(captured: dict):
    """Return (mock_kpipeline_cls, mock_soundfile) that record calls."""

    def fake_pipeline_call(text, voice=None):
        captured.setdefault("calls", []).append({"text": text, "voice": voice})
        return iter([(None, None, np.zeros(100, dtype=np.float32))])

    mock_pipeline_instance = MagicMock(side_effect=fake_pipeline_call)
    mock_kpipeline_cls = MagicMock(return_value=mock_pipeline_instance)

    mock_sf = MagicMock()

    def fake_sf_write(path, data, samplerate=None):
        captured.setdefault("writes", []).append({"path": path, "samplerate": samplerate})

    mock_sf.write.side_effect = fake_sf_write

    return mock_kpipeline_cls, mock_sf


# Feature: agentic-office-comedy, Property 11: KokoroTTS produces correctly named WAV files using the character's voice
@settings(max_examples=50)
@given(
    st.text(min_size=1, max_size=30).filter(lambda s: s.strip() and " " not in s.strip()),
    st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
    st.integers(min_value=0, max_value=99),
    st.sampled_from(["English Office Comedy", "Hindi Office Comedy"]),
)
def test_kokoro_tts_file_naming_and_voice_selection(char_name, kokoro_voice, exchange_index, show_style):
    """
    **Validates: Requirements 7.1, 7.2, 7.3**

    For any DialogueTurn with a valid speaker name and exchange index, when
    KokoroTTS.synthesize() succeeds, it shall:
    (a) return a Path pointing to a file inside the specified output_folder,
    (b) name the file using the zero-padded index and character name pattern,
    (c) invoke KPipeline with the kokoro_voice value from the character definition.
    """
    import tempfile

    character = Character(
        name=char_name,
        show=show_style,
        personality="test",
        speaking_style="test",
        catchphrases=["test"],
        kokoro_voice=kokoro_voice,
    )
    turn = DialogueTurn(speaker=char_name, text=f"{char_name}: Some line.")

    captured = {}
    mock_kpipeline_cls, mock_sf = _make_kokoro_mocks(captured)

    mock_kokoro_mod = types.ModuleType("kokoro")
    mock_kokoro_mod.KPipeline = mock_kpipeline_cls

    original_kokoro = _sys.modules.get("kokoro")
    original_sf = _sys.modules.get("soundfile")
    _sys.modules["kokoro"] = mock_kokoro_mod
    _sys.modules["soundfile"] = mock_sf

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_folder = Path(tmpdir)

            with patch.object(KokoroTTS, "__init__", return_value=None):
                tts = KokoroTTS.__new__(KokoroTTS)
                result = tts.synthesize(turn, output_folder, exchange_index, character, show_style)

            # (a) Must return a Path
            assert isinstance(result, Path), (
                f"Expected Path, got {type(result)}"
            )

            # (b) Path must be inside output_folder with correct naming pattern
            expected_name = f"{exchange_index:02d}_{char_name.replace(' ', '_')}.wav"
            assert result == output_folder / expected_name, (
                f"Expected {output_folder / expected_name}, got {result}"
            )

            # (c) KPipeline must have been called with the character's kokoro_voice
            calls = captured.get("calls", [])
            assert len(calls) == 1, f"Expected 1 KPipeline call, got {len(calls)}"
            assert calls[0]["voice"] == kokoro_voice, (
                f"Expected voice '{kokoro_voice}', got '{calls[0]['voice']}'"
            )

            # soundfile.write must have been called with samplerate=24000
            writes = captured.get("writes", [])
            assert len(writes) == 1, f"Expected 1 soundfile.write call, got {len(writes)}"
            assert writes[0]["samplerate"] == 24000, (
                f"Expected samplerate=24000, got {writes[0]['samplerate']}"
            )
    finally:
        if original_kokoro is None:
            _sys.modules.pop("kokoro", None)
        else:
            _sys.modules["kokoro"] = original_kokoro
        if original_sf is None:
            _sys.modules.pop("soundfile", None)
        else:
            _sys.modules["soundfile"] = original_sf
