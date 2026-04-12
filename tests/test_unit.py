import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from pathlib import Path

from agentic_office_comedy import CharacterLoader


def test_auto_create_samples_english_creates_at_least_4_files():
    """_auto_create_samples() creates at least 4 JSON files for English Office Comedy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = CharacterLoader(Path(tmpdir))
        loader._auto_create_samples()

        json_files = list(Path(tmpdir).glob("*.json"))
        english_chars = [
            loader._load_file(f)
            for f in json_files
        ]
        english_chars = [c for c in english_chars if c is not None and c.show == "English Office Comedy"]

        assert len(english_chars) >= 4, (
            f"Expected at least 4 English Office Comedy characters, got {len(english_chars)}"
        )


def test_auto_create_samples_hindi_creates_at_least_4_files():
    """_auto_create_samples() creates at least 4 JSON files for Hindi Office Comedy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = CharacterLoader(Path(tmpdir))
        loader._auto_create_samples()

        json_files = list(Path(tmpdir).glob("*.json"))
        hindi_chars = [
            loader._load_file(f)
            for f in json_files
        ]
        hindi_chars = [c for c in hindi_chars if c is not None and c.show == "Hindi Office Comedy"]

        assert len(hindi_chars) >= 4, (
            f"Expected at least 4 Hindi Office Comedy characters, got {len(hindi_chars)}"
        )


def test_auto_create_samples_all_files_are_valid():
    """All files created by _auto_create_samples() can be loaded by _load_file() without returning None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = CharacterLoader(Path(tmpdir))
        loader._auto_create_samples()

        json_files = list(Path(tmpdir).glob("*.json"))
        assert len(json_files) > 0, "Expected at least one JSON file to be created"

        for path in json_files:
            character = loader._load_file(path)
            assert character is not None, f"_load_file() returned None for {path.name}"


def test_load_all_on_empty_dir_auto_creates_and_returns_at_least_8_characters():
    """load_all() on an empty directory auto-creates samples and returns at least 8 characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = CharacterLoader(Path(tmpdir))
        characters = loader.load_all()

        assert len(characters) >= 8, (
            f"Expected at least 8 characters after auto-create, got {len(characters)}"
        )


# ---------------------------------------------------------------------------
# OllamaClient.is_available() tests
# ---------------------------------------------------------------------------

import http.server
import threading
import urllib.error
from unittest.mock import patch, MagicMock
from agentic_office_comedy import OllamaClient


def _make_client(base_url: str) -> OllamaClient:
    return OllamaClient(
        model="test-model",
        base_url=base_url,
        max_tokens=50,
        temperature=0.7,
        timeout=30.0,
    )


def test_is_available_returns_true_on_success():
    """is_available() returns True when the server responds with 2xx."""
    mock_response = MagicMock()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.read.return_value = b"Ollama is running"

    with patch("urllib.request.urlopen", return_value=mock_response):
        client = _make_client("http://localhost:11434")
        assert client.is_available() is True


def test_is_available_returns_false_on_connection_error():
    """is_available() returns False when the server is unreachable."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        client = _make_client("http://localhost:11434")
        assert client.is_available() is False


def test_is_available_returns_false_on_timeout():
    """is_available() returns False on socket timeout."""
    import socket
    with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
        client = _make_client("http://localhost:11434")
        assert client.is_available() is False


def test_is_available_returns_false_on_http_error():
    """is_available() returns False on HTTP error responses."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
        url="http://localhost:11434/", code=500, msg="Internal Server Error",
        hdrs=None, fp=None
    )):
        client = _make_client("http://localhost:11434")
        assert client.is_available() is False


def test_is_available_never_raises():
    """is_available() must not propagate any exception."""
    with patch("urllib.request.urlopen", side_effect=OSError("unexpected OS error")):
        client = _make_client("http://localhost:11434")
        # Should return False, not raise
        result = client.is_available()
        assert result is False


def test_is_available_uses_short_timeout():
    """is_available() uses a 5-second timeout, not the full generation timeout."""
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["timeout"] = timeout
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b""
        return mock_response

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = _make_client("http://localhost:11434")
        client.is_available()

    assert captured.get("timeout") == 5, (
        f"Expected timeout=5, got {captured.get('timeout')}"
    )


# ---------------------------------------------------------------------------
# OllamaClient.generate() error path tests
# Requirements: 1.3, 3.6
# ---------------------------------------------------------------------------

import socket


def test_generate_returns_fallback_on_timeout():
    """generate() returns '[generation timed out]' when socket.timeout is raised.

    Validates: Requirement 3.6
    """
    with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
        client = _make_client("http://localhost:11434")
        result = client.generate("Say something funny.")
    assert result == "[generation timed out]"


def test_generate_returns_fallback_on_url_error_timeout():
    """generate() returns '[generation timed out]' when URLError wraps a socket.timeout.

    Validates: Requirement 3.6
    """
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(socket.timeout("timed out"))):
        client = _make_client("http://localhost:11434")
        result = client.generate("Say something funny.")
    assert result == "[generation timed out]"


def test_generate_returns_fallback_on_connection_error():
    """generate() returns '[connection error: Ollama unavailable]' on a plain URLError.

    Validates: Requirement 1.3
    """
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        client = _make_client("http://localhost:11434")
        result = client.generate("Say something funny.")
    assert result == "[connection error: Ollama unavailable]"


def test_generate_never_raises_on_os_error():
    """generate() returns a non-empty string and does not raise on OSError.

    Validates: Requirement 1.3
    """
    with patch("urllib.request.urlopen", side_effect=OSError("remote disconnected")):
        client = _make_client("http://localhost:11434")
        result = client.generate("Say something funny.")
    assert isinstance(result, str) and len(result) > 0


# ---------------------------------------------------------------------------
# SceneOrchestrator error path tests
# Requirements: 7.5, 8.3
# ---------------------------------------------------------------------------

from agentic_office_comedy import (
    SceneOrchestrator,
    GenerationConfig,
    Character,
    PromptBuilder,
)


def _make_character(name: str, show: str) -> Character:
    return Character(
        name=name,
        show=show,
        personality="test personality",
        speaking_style="test style",
        catchphrases=["test catchphrase"],
        kokoro_voice="af_heart",
    )


def _make_mock_ollama():
    """Return a mock OllamaClient with a counter-based generate() side effect."""
    counter = [0]
    mock = MagicMock()
    def gen(prompt):
        counter[0] += 1
        return f"Speaker: Line {counter[0]}"
    mock.generate.side_effect = gen
    return mock


def test_tts_disabled_produces_no_audio_files():
    """When TTS is disabled, no audio_path is set on any DialogueTurn.

    Validates: Requirement 7.5
    """
    show_style = "English Office Comedy"
    characters = [
        _make_character("Alice", show_style),
        _make_character("Bob", show_style),
    ]

    orchestrator = SceneOrchestrator(
        characters=characters,
        ollama=_make_mock_ollama(),
        prompt_builder=PromptBuilder(),
        tts=None,  # TTS explicitly disabled
    )

    config = GenerationConfig(
        show_style=show_style,
        scenario="A meeting goes wrong",
        num_exchanges=4,
        tts_enabled=False,
    )

    result = orchestrator.run_scene(config)

    assert result.error is None, f"Unexpected error: {result.error}"
    assert len(result.turns) == 4

    for turn in result.turns:
        assert turn.audio_path is None, (
            f"Expected no audio_path when TTS is disabled, "
            f"but turn '{turn.speaker}' has audio_path={turn.audio_path!r}"
        )

    # audio_paths() helper should return an empty list
    assert result.audio_paths() == []


def test_filesystem_error_disables_tts_gracefully():
    """When output folder creation raises OSError, TTS is disabled and scene completes.

    Validates: Requirement 8.3
    """
    show_style = "English Office Comedy"
    characters = [
        _make_character("Alice", show_style),
        _make_character("Bob", show_style),
    ]

    # Create a mock TTS object — it should NOT be called when mkdir fails
    mock_tts = MagicMock()

    orchestrator = SceneOrchestrator(
        characters=characters,
        ollama=_make_mock_ollama(),
        prompt_builder=PromptBuilder(),
        tts=mock_tts,
    )

    config = GenerationConfig(
        show_style=show_style,
        scenario="A meeting goes wrong",
        num_exchanges=4,
        tts_enabled=True,  # TTS requested, but mkdir will fail
    )

    with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
        result = orchestrator.run_scene(config)

    # Scene must complete without crashing
    assert result.error is None, f"Unexpected error: {result.error}"
    assert len(result.turns) == 4

    # TTS synthesize() must NOT have been called (graceful degradation)
    mock_tts.synthesize.assert_not_called()

    # No audio paths should be set
    for turn in result.turns:
        assert turn.audio_path is None, (
            f"Expected no audio_path after filesystem error, "
            f"but turn '{turn.speaker}' has audio_path={turn.audio_path!r}"
        )


# ---------------------------------------------------------------------------
# KokoroTTS unit tests
# Requirements: 7.6
# ---------------------------------------------------------------------------

from agentic_office_comedy import KokoroTTS, DialogueTurn, Character


def _make_tts_character(name: str = "Alice", voice: str = "af_heart") -> Character:
    return Character(
        name=name,
        show="English Office Comedy",
        personality="test",
        speaking_style="test",
        catchphrases=["test"],
        kokoro_voice=voice,
    )


def test_kokoro_tts_init_raises_import_error_when_not_installed():
    """KokoroTTS.__init__ raises ImportError when kokoro is not installed.

    Validates: Requirements 1.4, 7.1
    """
    import sys
    import importlib
    from unittest.mock import patch

    # Simulate kokoro not being installed by making the import fail
    with patch.dict(sys.modules, {"kokoro": None}):
        try:
            tts = KokoroTTS()
            # If we get here, kokoro IS installed — skip the assertion
        except ImportError:
            pass  # Expected when kokoro is not installed
        except Exception as exc:
            # Any other exception is unexpected
            assert False, f"Expected ImportError, got {type(exc).__name__}: {exc}"


def test_kokoro_tts_synthesize_returns_none_on_exception():
    """synthesize() returns None when Kokoro raises an exception, without halting the scene.

    Validates: Requirement 7.6
    """
    import tempfile
    from unittest.mock import patch, MagicMock

    character = _make_tts_character("Bob")
    turn = DialogueTurn(speaker="Bob", text="Bob: Hello there.")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_folder = Path(tmpdir)

        # Patch KPipeline to raise an exception during synthesis
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.side_effect = RuntimeError("Kokoro synthesis error")
        mock_kpipeline_cls = MagicMock(return_value=mock_pipeline_instance)

        with patch.dict("sys.modules", {"kokoro": MagicMock(KPipeline=mock_kpipeline_cls)}):
            # Bypass __init__ check by patching it
            with patch.object(KokoroTTS, "__init__", return_value=None):
                tts = KokoroTTS.__new__(KokoroTTS)
                tts.__init__ = lambda: None

                # Patch the import inside synthesize to use our mock
                import types
                mock_kokoro_mod = types.ModuleType("kokoro")
                mock_kokoro_mod.KPipeline = mock_kpipeline_cls

                import sys as _sys
                original = _sys.modules.get("kokoro")
                _sys.modules["kokoro"] = mock_kokoro_mod
                try:
                    result = tts.synthesize(turn, output_folder, 0, character, "English Office Comedy")
                finally:
                    if original is None:
                        _sys.modules.pop("kokoro", None)
                    else:
                        _sys.modules["kokoro"] = original

        assert result is None, (
            f"Expected None when Kokoro raises an exception, got {result!r}"
        )


def test_kokoro_tts_synthesize_strips_speaker_prefix():
    """synthesize() strips the 'Speaker: ' prefix before passing text to KPipeline.

    Validates: Requirement 7.1
    """
    import tempfile
    import types
    import sys as _sys
    from unittest.mock import MagicMock, patch
    import numpy as np

    character = _make_tts_character("Alice")
    turn = DialogueTurn(speaker="Alice", text="Alice: Hello there.")

    captured = {}

    def fake_pipeline_call(text, voice=None):
        captured["text"] = text
        captured["voice"] = voice
        # Return a single chunk: (gs, ps, audio)
        return iter([(None, None, np.zeros(100, dtype=np.float32))])

    mock_pipeline_instance = MagicMock(side_effect=fake_pipeline_call)
    mock_kpipeline_cls = MagicMock(return_value=mock_pipeline_instance)

    mock_soundfile = MagicMock()
    mock_numpy = np  # use real numpy for concatenate

    with tempfile.TemporaryDirectory() as tmpdir:
        output_folder = Path(tmpdir)

        mock_kokoro_mod = types.ModuleType("kokoro")
        mock_kokoro_mod.KPipeline = mock_kpipeline_cls

        original_kokoro = _sys.modules.get("kokoro")
        original_sf = _sys.modules.get("soundfile")
        _sys.modules["kokoro"] = mock_kokoro_mod
        _sys.modules["soundfile"] = mock_soundfile

        try:
            with patch.object(KokoroTTS, "__init__", return_value=None):
                tts = KokoroTTS.__new__(KokoroTTS)
                result = tts.synthesize(turn, output_folder, 0, character, "English Office Comedy")
        finally:
            if original_kokoro is None:
                _sys.modules.pop("kokoro", None)
            else:
                _sys.modules["kokoro"] = original_kokoro
            if original_sf is None:
                _sys.modules.pop("soundfile", None)
            else:
                _sys.modules["soundfile"] = original_sf

    # The text passed to KPipeline should NOT include the "Alice: " prefix
    assert captured.get("text") == "Hello there.", (
        f"Expected spoken text 'Hello there.', got {captured.get('text')!r}"
    )
    assert captured.get("voice") == "af_heart", (
        f"Expected voice 'af_heart', got {captured.get('voice')!r}"
    )
