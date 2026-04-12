"""
Agentic Office Comedy
=====================

A fully offline, multi-agent comedy scene generator powered by local LLM inference
(Ollama) and optional local TTS synthesis (Kokoro). Two comedy worlds are supported:
English office cringe comedy and Hindi bureaucratic satire.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Minimal dependencies (install via pip):
    pip install gradio soundfile kokoro

Optional (for TTS):
    pip install kokoro soundfile

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OLLAMA SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Install Ollama from https://ollama.com
2. Start the Ollama server:
       ollama serve
3. Pull the required model (runs on 4 GB VRAM):
       ollama pull qwen2.5:4b
   Alternatively:
       ollama pull gemma3:4b

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KOKORO TTS SETUP (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Kokoro provides fully local, high-quality TTS synthesis.

1. Install Kokoro and soundfile:
       pip install kokoro soundfile
2. On first run, Kokoro will download voice model weights automatically.
3. If Kokoro is not installed, the TTS checkbox in the UI will be disabled and
   the app will run in text-only mode.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUNNING THE APP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    python agentic_office_comedy.py

Then open http://localhost:7860 in your browser.
"""

import json
import logging
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging — all diagnostic output goes through the standard logging module;
# bare print() statements are not used anywhere in this script.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory setup — created at module load time so every component can assume
# these paths exist.  exist_ok=True makes repeated imports / restarts safe.
# ---------------------------------------------------------------------------
CHARACTERS_DIR = Path("characters")
OUTPUTS_DIR = Path("outputs")

CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

logger.info("Directories ready: %s, %s", CHARACTERS_DIR, OUTPUTS_DIR)

# ---------------------------------------------------------------------------
# Scene mode constants and config
# ---------------------------------------------------------------------------

COMEDY_MODE = "Comedy"
DRAMA_MODE  = "Drama"
DEBATE_MODE = "Debate"
SCENE_MODES = [COMEDY_MODE, DRAMA_MODE, DEBATE_MODE]

ENGLISH_STYLE = "English Office Comedy"
HINDI_STYLE   = "Hindi Office Comedy"

MODE_CONFIG = {
    COMEDY_MODE: {
        "goal": "produce short entertaining in-character lines with light escalation",
        "line_style": "compact, witty, awkward, playable",
        "escalation": "misunderstanding, absurdity, cringe, deadpan reactions",
        "allow_confessional": True,
        "use_moderator": False,
    },
    DRAMA_MODE: {
        "goal": "produce emotionally grounded workplace tension with realistic conflict",
        "line_style": "serious, tense, concise, natural",
        "escalation": "pressure, accusation, fear, status conflict, ethical tension",
        "allow_confessional": True,
        "use_moderator": False,
    },
    DEBATE_MODE: {
        "goal": "produce short structured arguments and rebuttals on a topic",
        "line_style": "clear, sharp, concise, role-consistent",
        "escalation": "argument depth, rebuttal strength, challenge, clarification",
        "allow_confessional": False,
        "use_moderator": True,
    },
}

DRAMA_FALLBACKS_EN = [
    "This is no longer a misunderstanding. It's becoming a decision about trust.",
    "You keep calling it process, but it feels personal.",
    "I did the work. I just wasn't the one in the room.",
    "No one says the truth directly here, and that's the problem.",
]
DRAMA_FALLBACKS_HI = [
    "Aap log procedure bolte hain, par nuksaan aadmi ka hota hai.",
    "Galti system ki ho, zimmedari neeche wale par aa jaati hai.",
    "Mujhe niyam se problem nahi, niyat se hai.",
    "Insaan ruk gaya hai, file aage badh rahi hai.",
]
DEBATE_FALLBACKS_EN = [
    "Efficiency matters, but so does trust. You cannot optimise one by destroying the other.",
    "That sounds principled, but in practice it shifts the burden downward.",
    "The real question is not whether it works in theory, but who pays the price when it fails.",
    "A policy is only fair if ordinary people can survive it.",
]
DEBATE_FALLBACKS_HI = [
    "Sawal sirf niyam ka nahi hai, asar ka bhi hai.",
    "Theory mein baat sahi lagti hai, ground par log phas jaate hain.",
    "Jo policy aam aadmi jhel na sake, usse safal kaise kahenge?",
    "Practical mushkil ko ignore karke debate poori nahi hoti.",
]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SceneState:
    """Hidden director brain — tracks mode, tension, and debate roles."""
    mode: str
    topic_or_scenario: str
    tension: float
    objective: str
    conflict: str
    last_shift: str
    turn_index: int = 0
    debate_roles: Optional[dict] = None   # {character_name: role_description}
    debate_order: Optional[list] = None   # ordered list of character names


@dataclass
class Character:
    """A comedy archetype loaded from a JSON file in characters/."""
    name: str
    show: str                  # "English Office Comedy" | "Hindi Office Comedy"
    personality: str
    speaking_style: str
    catchphrases: list[str]
    kokoro_voice: str


@dataclass
class DialogueTurn:
    """A single spoken line within a scene."""
    speaker: str               # character name
    text: str                  # full line including "Speaker: ..." prefix
    audio_path: Path | None = None


@dataclass
class GenerationConfig:
    """All parameters that control a single scene generation run."""
    show_style: str
    scenario: str
    num_exchanges: int         # 4–12
    tts_enabled: bool
    scene_mode: str = COMEDY_MODE
    model: str = "nvidia/nemotron-3-nano-4b"
    max_tokens: int = 150
    temperature: float = 0.7
    transcript_window: int = 4
    timeout: float = 30.0


@dataclass
class SceneResult:
    """The complete output of a scene generation run."""
    config: GenerationConfig
    turns: list[DialogueTurn] = field(default_factory=list)
    output_folder: Path | None = None
    error: str | None = None

    def as_script(self) -> str:
        """Return the full scene as a newline-joined script string."""
        return "\n".join(turn.text for turn in self.turns)

    def audio_paths(self) -> list[Path]:
        """Return only the turns that have an associated WAV file."""
        return [t.audio_path for t in self.turns if t.audio_path is not None]


# ---------------------------------------------------------------------------
# CharacterLoader
# ---------------------------------------------------------------------------

class CharacterLoader:
    """Discovers and validates character definitions from the characters/ directory."""

    def __init__(self, characters_dir: Path) -> None:
        self.characters_dir = characters_dir

    def load_all(self) -> list[Character]:
        """Scan characters_dir for *.json files and return valid Character objects.

        If no JSON files are found, _auto_create_samples() is called first so
        the app always has at least the bundled sample characters available.
        """
        json_files = list(self.characters_dir.glob("*.json"))

        # Auto-create sample files on first run (empty characters/ directory).
        if not json_files:
            logger.info("No character JSON files found; auto-creating samples.")
            self._auto_create_samples()
            json_files = list(self.characters_dir.glob("*.json"))

        characters: list[Character] = []
        for path in json_files:
            character = self._load_file(path)
            if character is None:
                logger.warning("Skipping invalid character file: %s", path)
            else:
                characters.append(character)

        logger.info("Loaded %d character(s) from %s", len(characters), self.characters_dir)
        return characters

    def _auto_create_samples(self) -> None:
        """Write eight sample character JSON files — four per show style.

        English Office Comedy: manager, deadpan colleague, intense colleague, receptionist.
        Hindi Office Comedy: petitioner, corrupt official, clerk, supervisor.
        """
        import json

        samples = [
            # ── English Office Comedy ──────────────────────────────────────────
            {
                "name": "Gareth Pinnock",
                "show": "English Office Comedy",
                "personality": "Cringe overconfident manager who desperately wants to be liked by everyone in the office",
                "speaking_style": "Rambling, self-aggrandizing, prone to awkward pauses, misquotes famous people, and pivots every sentence back to himself",
                "catchphrases": [
                    "That's what she said",
                    "I am the world's best boss — I have a mug that says so",
                    "Would I rather be feared or loved? Easy. Both.",
                ],
                "kokoro_voice": "af_heart",
            },
            {
                "name": "Tim Blankenship",
                "show": "English Office Comedy",
                "personality": "Dry, sardonic colleague who expends the absolute minimum effort and finds everything mildly absurd",
                "speaking_style": "Deadpan, clipped sentences, long pauses, occasional glance at an invisible camera, never raises his voice",
                "catchphrases": [
                    "Sure.",
                    "That tracks.",
                    "I've seen worse. Not many, but some.",
                ],
                "kokoro_voice": "am_michael",
            },
            {
                "name": "Dwight Bramble",
                "show": "English Office Comedy",
                "personality": "Literal, self-important, intensely earnest colleague who treats every office task as a military operation",
                "speaking_style": "Clipped declarative sentences, cites obscure regulations, corrects everyone, never uses contractions",
                "catchphrases": [
                    "False.",
                    "Identity theft is not a joke, Jim.",
                    "I have been trained in seventeen forms of office combat.",
                ],
                "kokoro_voice": "af_bella",
            },
            {
                "name": "Parveen Osei",
                "show": "English Office Comedy",
                "personality": "Observant, quietly amused receptionist who has seen everything and judges nothing — out loud",
                "speaking_style": "Measured, polite, with a perfectly timed dry aside; never volunteers more than necessary",
                "catchphrases": [
                    "I'll let him know you called.",
                    "Noted.",
                    "That's… one way to handle it.",
                ],
                "kokoro_voice": "af_nicole",
            },
            # ── Hindi Office Comedy ───────────────────────────────────────────
            {
                "name": "Ramesh Prasad Verma",
                "show": "Hindi Office Comedy",
                "personality": "Frustrated common man who has been trying to get a simple form stamped for six months and is running out of patience",
                "speaking_style": "Exasperated, increasingly loud, mixes Hindi idioms with bureaucratic jargon he has reluctantly learned",
                "catchphrases": [
                    "Yaar, sirf ek stamp chahiye!",
                    "Main teen mahine se aa raha hoon!",
                    "Kya yahan koi kaam bhi hota hai?",
                ],
                "kokoro_voice": "hf_alpha",
            },
            {
                "name": "Shri Brijmohan Lal Sharma",
                "show": "Hindi Office Comedy",
                "personality": "Slippery, evasive corrupt official who always finds a new reason to delay, redirect, or lose paperwork",
                "speaking_style": "Oily, over-formal, peppered with vague references to 'procedure' and 'higher authorities', never gives a direct answer",
                "catchphrases": [
                    "Yeh toh upar se aana chahiye.",
                    "File abhi process mein hai.",
                    "Aap kal aana, sahib.",
                ],
                "kokoro_voice": "hm_omega",
            },
            {
                "name": "Babu Laxmikant Tiwari",
                "show": "Hindi Office Comedy",
                "personality": "Bureaucratic, form-obsessed clerk who recites rules from memory and treats every deviation as a personal affront",
                "speaking_style": "Monotone, recites regulation numbers, insists on triplicate copies, deeply offended by informality",
                "catchphrases": [
                    "Form 27-B nahi bhara?",
                    "Niyam ke anusaar…",
                    "Bina rubber stamp ke kuch nahi hoga.",
                ],
                "kokoro_voice": "hf_alpha",
            },
            {
                "name": "Adhikari Mahavir Singh Chauhan",
                "show": "Hindi Office Comedy",
                "personality": "Pompous, dismissive supervisor who is never available, always in a meeting, and takes credit for everything",
                "speaking_style": "Booming, self-important, drops English management buzzwords into Hindi sentences, ends every statement with a rhetorical question",
                "catchphrases": [
                    "Main meeting mein hoon.",
                    "Yeh mera department nahi sambhalta toh kaun sambhalta?",
                    "Synergy, Ramesh ji. Synergy.",
                ],
                "kokoro_voice": "hm_omega",
            },
        ]

        for character in samples:
            # Derive a safe filename from the character's name.
            filename = character["name"].lower().replace(" ", "_") + ".json"
            path = self.characters_dir / filename
            with path.open("w", encoding="utf-8") as fh:
                json.dump(character, fh, indent=2, ensure_ascii=False)

        logger.info(
            "Created %d sample character files in %s",
            len(samples),
            self.characters_dir,
        )

    def _load_file(self, path: Path) -> "Character | None":
        """Parse and validate a single character JSON file.

        Returns a Character on success, or None if any required field is missing
        or the file cannot be parsed as valid JSON.
        """
        import json

        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in character file %s: %s", path, exc)
            return None

        required_fields = ("name", "show", "personality", "speaking_style", "catchphrases", "kokoro_voice")
        for field_name in required_fields:
            if field_name not in data:
                logger.warning("Character file %s is missing required field '%s'", path, field_name)
                return None

        if not isinstance(data["catchphrases"], list) or len(data["catchphrases"]) == 0:
            logger.warning("Character file %s: 'catchphrases' must be a non-empty list", path)
            return None

        return Character(
            name=data["name"],
            show=data["show"],
            personality=data["personality"],
            speaking_style=data["speaking_style"],
            catchphrases=data["catchphrases"],
            kokoro_voice=data["kokoro_voice"],
        )

    def save_character(self, char: "Character") -> None:
        """Write a Character back to its JSON file (create or overwrite)."""
        import json as _json
        filename = char.name.lower().replace(" ", "_") + ".json"
        path = self.characters_dir / filename
        data = {
            "name": char.name,
            "show": char.show,
            "personality": char.personality,
            "speaking_style": char.speaking_style,
            "catchphrases": char.catchphrases,
            "kokoro_voice": char.kokoro_voice,
        }
        with path.open("w", encoding="utf-8") as fh:
            _json.dump(data, fh, indent=2, ensure_ascii=False)
        logger.info("Saved character: %s", path)

    def delete_character(self, name: str) -> bool:
        """Delete the JSON file for the named character. Returns True if deleted."""
        filename = name.lower().replace(" ", "_") + ".json"
        path = self.characters_dir / filename
        if path.exists():
            path.unlink()
            logger.info("Deleted character file: %s", path)
            return True
        return False


        """Parse and validate a single character JSON file.

        Returns a Character on success, or None if any required field is missing
        or the file cannot be parsed as valid JSON.
        """
        import json

        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in character file %s: %s", path, exc)
            return None

        required_fields = ("name", "show", "personality", "speaking_style", "catchphrases", "kokoro_voice")
        for field_name in required_fields:
            if field_name not in data:
                logger.warning("Character file %s is missing required field '%s'", path, field_name)
                return None

        # catchphrases must be a non-empty list
        if not isinstance(data["catchphrases"], list) or len(data["catchphrases"]) == 0:
            logger.warning("Character file %s: 'catchphrases' must be a non-empty list", path)
            return None

        return Character(
            name=data["name"],
            show=data["show"],
            personality=data["personality"],
            speaking_style=data["speaking_style"],
            catchphrases=data["catchphrases"],
            kokoro_voice=data["kokoro_voice"],
        )


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------

class OllamaClient:
    """HTTP wrapper supporting both Ollama (/api/generate) and OpenAI-compatible
    servers such as LM Studio (/v1/chat/completions).

    Set backend="lmstudio" (or any OpenAI-compatible server) to use the chat
    completions API.  backend="ollama" uses the native Ollama generate API.
    Uses only Python stdlib — no external HTTP libraries required.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
        backend: str = "lmstudio",  # "ollama" | "lmstudio"
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.backend = backend

    def generate(self, prompt: str) -> str:
        """Send a prompt and return the generated text (single-string interface)."""
        if self.backend == "ollama":
            return self._generate_ollama(prompt)
        return self._generate_openai(prompt)

    def generate_chat(self, system: str, user: str) -> str:
        """Send a system+user message pair (chat completions interface).

        Falls back to concatenating both into a single prompt for Ollama.
        """
        if self.backend == "ollama":
            return self._generate_ollama(f"{system}\n\n{user}")
        return self._generate_openai(user, system=system)

    def _generate_openai(self, prompt: str, system: str | None = None) -> str:
        """POST to /v1/chat/completions (LM Studio / OpenAI-compatible)."""
        url = f"{self.base_url}/v1/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            logger.error("LM Studio returned HTTP %d for model '%s'", exc.code, self.model)
            return f"[generation failed: HTTP {exc.code}]"
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
                logger.error("LM Studio request timed out after %.1fs", self.timeout)
                return "[generation timed out]"
            logger.error("LM Studio connection error: %s", exc)
            return "[connection error: LM Studio unavailable]"
        except socket.timeout:
            logger.error("LM Studio request timed out (socket)")
            return "[generation timed out]"
        except OSError as exc:
            logger.error("LM Studio I/O error: %s", exc)
            return "[connection error: LM Studio unavailable]"

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error("Failed to parse LM Studio response: %s", exc)
            return "[generation failed: invalid response]"

    def _generate_ollama(self, prompt: str) -> str:
        """POST to /api/generate (native Ollama API)."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            logger.error("Ollama returned HTTP %d for model '%s'", exc.code, self.model)
            return f"[generation failed: HTTP {exc.code}]"
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
                logger.error("Ollama request timed out after %.1fs", self.timeout)
                return "[generation timed out]"
            logger.error("Ollama connection error: %s", exc)
            return "[connection error: Ollama unavailable]"
        except socket.timeout:
            logger.error("Ollama request timed out (socket)")
            return "[generation timed out]"
        except OSError as exc:
            logger.error("Ollama I/O error: %s", exc)
            return "[connection error: Ollama unavailable]"

        try:
            data = json.loads(raw)
            return data["response"].strip()
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to parse Ollama response: %s", exc)
            return "[generation failed: invalid response]"

    def is_available(self) -> bool:
        """Check whether the LLM server is reachable.

        For LM Studio hits /v1/models; for Ollama hits /.
        Returns True on success, False on any exception — never raises.
        """
        url = f"{self.base_url}/v1/models" if self.backend != "ollama" else f"{self.base_url}/"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                _ = response.read()
            logger.debug("LLM server reachable at %s", self.base_url)
            return True
        except Exception as exc:
            logger.warning("LLM server not reachable at %s: %s", self.base_url, exc)
            return False


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class PromptBuilder:
    """Mode-aware prompt builder for Comedy, Drama, and Debate scenes."""

    def __init__(self, transcript_window_size: int = 4) -> None:
        self.transcript_window_size = transcript_window_size

    def build(self, character, transcript, scenario,
              scene_mode=None, scene_state=None, debate_role=None):
        """Single-string fallback (Ollama backend)."""
        system, user = self.build_chat(character, transcript, scenario,
                                       scene_mode or COMEDY_MODE, scene_state, debate_role)
        return f"{system}\n\n{user}"

    def build_chat(self, character, transcript, scenario,
                   scene_mode=COMEDY_MODE, scene_state=None, debate_role=None):
        """Return (system_prompt, user_prompt) for chat completions API."""
        window = transcript[-self.transcript_window_size:]
        transcript_text = (
            "\n".join(f"{t.speaker}: {t.text}" for t in window) if window else "[scene starts]"
        )
        catchphrase_hint = character.catchphrases[0] if character.catchphrases else ""

        state_block = ""
        if scene_state:
            state_block = (
                f"Hidden scene state:\n"
                f"- mode: {scene_state.mode}\n"
                f"- conflict: {scene_state.conflict}\n"
                f"- objective: {scene_state.objective}\n"
                f"- tension: {scene_state.tension:.2f}\n"
                f"- last shift: {scene_state.last_shift}\n"
            )

        debate_block = ""
        if debate_role:
            debate_block = f"Your debate role: {debate_role}\nTopic: {scenario}\n"

        system = (
            f"You are {character.name}, a character in a workplace scene.\n"
            f"Personality: {character.personality}\n"
            f"Speaking style: {character.speaking_style}\n"
            f"Catchphrase flavour: \"{catchphrase_hint}\"\n\n"
            f"{self.mode_instruction(scene_mode, character.show)}\n"
            f"{self.mode_rules(scene_mode)}"
        )

        user = f"{state_block}{debate_block}Scenario: {scenario}\n\nRecent dialogue:\n{transcript_text}\n\n"
        if window:
            user += f"{window[-1].speaker} just said: \"{window[-1].text}\"\n"
        user += f"Now respond as {character.name}."

        return system, user

    def build_confessional(self, character, transcript, scene_mode):
        """Confessional aside — character speaks privately to the camera."""
        window = transcript[-4:]
        transcript_text = (
            "\n".join(f"{t.speaker}: {t.text}" for t in window) if window else "[scene starts]"
        )
        system = (
            f"You are writing one short confessional line spoken privately to a documentary camera.\n"
            f"Character: {character.name}\n"
            f"Personality: {character.personality}\n"
            f"Mode: {scene_mode}\nTone: honest, concise, revealing.\n\n"
            f"RULES: one short line only. No narration. No stage directions. "
            f"Reveal what the character really thinks."
        )
        user = f"Recent scene:\n{transcript_text}\n\nSpeak your confessional as {character.name}."
        return system, user

    @staticmethod
    def mode_instruction(scene_mode, show_style):
        if scene_mode == COMEDY_MODE:
            if show_style == ENGLISH_STYLE:
                return ("Mode: Comedy. Tone: awkward office mockumentary, cringe management energy, "
                        "dry reactions, restrained absurdity.")
            return ("Mode: Comedy. Tone: Hindi bureaucratic satire, Hinglish frustration, "
                    "red tape absurdity, petty procedural nonsense.")
        if scene_mode == DRAMA_MODE:
            if show_style == ENGLISH_STYLE:
                return ("Mode: Drama. Tone: realistic workplace tension, emotional pressure, "
                        "career stakes, natural serious dialogue.")
            return ("Mode: Drama. Tone: institutional pressure, bureaucracy, helplessness, dignity, "
                    "suppressed anger, natural serious Hinglish or Hindi.")
        if show_style == ENGLISH_STYLE:
            return ("Mode: Debate. Tone: structured workplace argument, clear viewpoints, "
                    "direct rebuttals, professional but sharp.")
        return ("Mode: Debate. Tone: structured bahas on a public or workplace issue, "
                "direct arguments, practical friction, clear rebuttals in natural Hinglish or Hindi.")

    @staticmethod
    def mode_rules(scene_mode):
        if scene_mode == COMEDY_MODE:
            return ("RULES: output ONE short in-character line only. No narration. No bullet points. "
                    "Do not explain the joke. Add mild escalation or reaction. "
                    "Max 20 words. Start with your character name and a colon.")
        if scene_mode == DRAMA_MODE:
            return ("RULES: output ONE short emotionally grounded line only. No narration. "
                    "Respond to pressure or vulnerability. Increase tension slightly. "
                    "Stay realistic. Max 20 words. Start with your character name and a colon.")
        return ("RULES: output ONE short argument, rebuttal, or clarification only. "
                "No narration. Address the topic directly. Defend your stance. "
                "Max 20 words. Start with your character name and a colon.")



# ---------------------------------------------------------------------------
# KokoroTTS
# ---------------------------------------------------------------------------

class KokoroTTS:
    """Optional TTS wrapper around Kokoro's KPipeline."""

    def __init__(self) -> None:
        try:
            from kokoro import KPipeline  # noqa: F401
        except ImportError as exc:
            raise ImportError("Kokoro not installed. Run: pip install kokoro soundfile") from exc

    def synthesize(self, turn, output_folder, exchange_index, character, show_style):
        lang_code_map = {ENGLISH_STYLE: "en-us", HINDI_STYLE: "hi"}
        lang_code = lang_code_map.get(show_style, "en-us")
        if show_style not in lang_code_map:
            logger.warning("Unknown show_style '%s'; falling back to en-us", show_style)
        prefix = f"{turn.speaker}: "
        spoken_text = turn.text[len(prefix):] if turn.text.startswith(prefix) else turn.text
        wav_path = output_folder / f"{exchange_index:02d}_{character.name.replace(' ', '_')}.wav"
        try:
            import numpy as np
            import soundfile as sf
            from kokoro import KPipeline
            pipeline = KPipeline(lang_code=lang_code)
            chunks = [chunk for _, _, chunk in pipeline(spoken_text, voice=character.kokoro_voice)]
            sf.write(str(wav_path), np.concatenate(chunks), samplerate=24000)
            logger.info("TTS wrote %s", wav_path)
            return wav_path
        except Exception as exc:
            logger.error("KokoroTTS synthesis failed for exchange %d (%s): %s",
                         exchange_index, character.name, exc)
            return None


# ---------------------------------------------------------------------------

class SceneOrchestrator:
    """V2 multi-mode scene orchestrator: Comedy, Drama, Debate."""

    def __init__(self, characters, ollama, prompt_builder, tts=None):
        self.characters = characters
        self.ollama = ollama
        self.prompt_builder = prompt_builder
        self.tts = tts

    # ── public streaming interface ────────────────────────────────────────────

    def run_scene_streaming(self, config, active_names=None):
        """Generator — yields a partial SceneResult after each exchange."""
        all_chars = self._get_characters_for_style(config.show_style)
        characters = [c for c in all_chars if c.name in active_names] if active_names else all_chars

        if len(characters) < 2:
            yield SceneResult(config=config, error="Need at least 2 characters for a scene")
            return

        tts_enabled = config.tts_enabled
        output_folder = None
        if tts_enabled:
            output_folder = OUTPUTS_DIR / f"scene_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                output_folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.error("Failed to create output folder %s: %s", output_folder, exc)
                tts_enabled = False
                output_folder = None

        scene_mode = config.scene_mode
        state = self._init_scene_state(scene_mode, config.scenario, config.show_style, characters)
        transcript = []
        num_exchanges = min(config.num_exchanges, 12)

        for idx in range(num_exchanges):
            character = self._pick_character(idx, characters, scene_mode, state)
            is_confessional = self._should_do_confessional(scene_mode, idx)

            try:
                if is_confessional:
                    sys_p, usr_p = self.prompt_builder.build_confessional(
                        character, transcript, scene_mode)
                    speaker_label = f"{character.name} (confessional)"
                else:
                    debate_role = (state.debate_roles or {}).get(character.name) if scene_mode == DEBATE_MODE else None
                    sys_p, usr_p = self.prompt_builder.build_chat(
                        character, transcript[-config.transcript_window:],
                        config.scenario, scene_mode, state, debate_role)
                    speaker_label = character.name

                raw = self.ollama.generate_chat(sys_p, usr_p)
                line = self._post_process(raw, config.show_style, scene_mode)
                line = self._enforce_speaker_prefix(line, character.name)

                # Repetition retry
                attempts = 0
                while attempts < 2 and self._is_repetition(DialogueTurn(speaker_label, line), transcript):
                    raw = self.ollama.generate_chat(sys_p, usr_p)
                    line = self._post_process(raw, config.show_style, scene_mode)
                    line = self._enforce_speaker_prefix(line, character.name)
                    attempts += 1

            except Exception as exc:
                logger.error("Generation error at exchange %d: %s", idx, exc)
                line = self._fallback_line(character, config.show_style, scene_mode, idx)
                line = self._enforce_speaker_prefix(line, character.name)
                speaker_label = character.name

            turn = DialogueTurn(speaker=speaker_label, text=line)
            transcript.append(turn)
            self._update_scene_state(state, line, scene_mode)

            if tts_enabled and self.tts is not None:
                turn.audio_path = self.tts.synthesize(turn, output_folder, idx, character, config.show_style)

            yield SceneResult(config=config, turns=list(transcript), output_folder=output_folder)

    def run_scene(self, config, active_names=None):
        """Non-streaming version — returns final SceneResult."""
        result = None
        for result in self.run_scene_streaming(config, active_names):
            pass
        return result or SceneResult(config=config, error="No exchanges generated")

    # ── scene state ───────────────────────────────────────────────────────────

    def _init_scene_state(self, scene_mode, text, show_style, characters):
        if scene_mode == COMEDY_MODE:
            if show_style == ENGLISH_STYLE:
                conflict = "an awkward office situation is spiraling"
                objective = "increase discomfort or dry reaction without losing coherence"
            else:
                conflict = "bureaucratic absurdity is blocking something simple"
                objective = "increase procedural nonsense or frustration"
        elif scene_mode == DRAMA_MODE:
            if show_style == ENGLISH_STYLE:
                conflict = "workplace tension is exposing insecurity or unfairness"
                objective = "escalate realistic emotional stakes"
            else:
                conflict = "bureaucratic or institutional pressure is hurting someone"
                objective = "escalate moral, practical, or emotional pressure"
        else:
            conflict = "participants disagree on a workplace or public issue"
            objective = "surface contrasting viewpoints clearly and sharply"

        state = SceneState(
            mode=scene_mode,
            topic_or_scenario=text.strip(),
            tension=0.25 if scene_mode == COMEDY_MODE else 0.4,
            objective=objective,
            conflict=conflict,
            last_shift="scene begins",
        )

        if scene_mode == DEBATE_MODE:
            roles, order = self._assign_debate_roles(show_style, characters, text)
            state.debate_roles = roles
            state.debate_order = order

        return state

    def _assign_debate_roles(self, show_style, characters, topic):
        usable = characters[:4]
        if show_style == ENGLISH_STYLE:
            role_templates = [
                "moderator trying to sound fair and visionary",
                "strongly in favor of the topic",
                "strongly against the topic",
                "pragmatic middle-ground perspective",
            ]
        else:
            role_templates = [
                "moderator maintaining order and sounding procedural",
                "strongly in favor of the topic",
                "strongly against the topic",
                "pragmatic practical perspective shaped by lived frustration",
            ]
        roles = {}
        order = []
        for idx, char in enumerate(usable):
            roles[char.name] = role_templates[min(idx, len(role_templates) - 1)]
            order.append(char.name)
        return roles, order

    def _update_scene_state(self, state, line, scene_mode):
        state.turn_index += 1
        state.last_shift = line[:100]
        if scene_mode == COMEDY_MODE:
            state.tension = min(1.0, state.tension + 0.07)
        elif scene_mode == DRAMA_MODE:
            state.tension = min(1.0, state.tension + 0.10)
        else:
            state.tension = min(1.0, state.tension + 0.06)

    # ── character selection ───────────────────────────────────────────────────

    def _pick_character(self, idx, characters, scene_mode, state):
        if scene_mode == DEBATE_MODE and state.debate_order:
            # Every 4th turn (after the first) goes back to the moderator
            if idx > 0 and idx % 4 == 3:
                speaker_name = state.debate_order[0]
            else:
                speaker_name = state.debate_order[idx % len(state.debate_order)]
            match = [c for c in characters if c.name == speaker_name]
            return match[0] if match else characters[idx % len(characters)]
        return characters[idx % len(characters)]

    def _get_characters_for_style(self, show_style):
        return [c for c in self.characters if c.show == show_style]

    # ── confessional logic ────────────────────────────────────────────────────

    @staticmethod
    def _should_do_confessional(scene_mode, turn_index):
        if scene_mode == DEBATE_MODE:
            return False
        return turn_index > 0 and turn_index % 3 == 2

    # ── post-processing ───────────────────────────────────────────────────────

    @staticmethod
    def _post_process(raw, show_style, scene_mode):
        """Extract the first non-empty line and clean it up."""
        line = next((l.strip() for l in raw.splitlines() if l.strip()), raw.strip())
        if scene_mode == DEBATE_MODE:
            line = re.sub(r"^(I believe|In my opinion|Frankly|To be honest),?\s*", "", line, flags=re.I)
        # Strip markdown artifacts
        line = re.sub(r"^[*#]+\s*", "", line).strip()
        return line

    @staticmethod
    def _enforce_speaker_prefix(line, character_name):
        """Ensure line starts with 'Name: '. Fixes hallucinated or missing prefixes."""
        if line.lower().startswith(character_name.lower() + ":"):
            return line
        # Strip any wrong "OtherName:" prefix the model may have added
        if re.match(r"^[A-Za-z ]{1,40}:", line):
            line = re.sub(r"^[A-Za-z ]{1,40}:\s*", "", line).strip()
        return f"{character_name}: {line}"

    @staticmethod
    def _is_repetition(exchange, transcript):
        new_text = exchange.text.lower()
        return any(t.text.lower() == new_text for t in transcript)

    # ── fallbacks ─────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_line(character, show_style, scene_mode, turn_index):
        import random
        if scene_mode == DRAMA_MODE:
            pool = DRAMA_FALLBACKS_EN if show_style == ENGLISH_STYLE else DRAMA_FALLBACKS_HI
        elif scene_mode == DEBATE_MODE:
            pool = DEBATE_FALLBACKS_EN if show_style == ENGLISH_STYLE else DEBATE_FALLBACKS_HI
        else:
            pool = [
                f"{character.name}: That's what she said.",
                f"{character.name}: I have a mug that says I'm the best boss.",
                f"{character.name}: Noted.",
                f"{character.name}: Yaar, sirf ek stamp chahiye!",
            ]
        line = random.choice(pool)
        if not line.startswith(character.name):
            line = f"{character.name}: {line}"
        return line



# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

# Mode-aware scenario examples: [show_style, scene_mode, scenario_text]
SCENARIO_EXAMPLES = [
    [ENGLISH_STYLE, COMEDY_MODE, "The office holds a meeting that could have been an email."],
    [ENGLISH_STYLE, COMEDY_MODE, "The regional boss starts a disastrous diversity workshop."],
    [ENGLISH_STYLE, DRAMA_MODE,  "A manager takes credit for a team member's work during an executive review."],
    [ENGLISH_STYLE, DRAMA_MODE,  "Rumours of layoffs spread and nobody knows who will be blamed."],
    [ENGLISH_STYLE, DEBATE_MODE, "Should remote work remain permanent for most office roles?"],
    [ENGLISH_STYLE, DEBATE_MODE, "Are performance reviews useful or mostly political?"],
    [HINDI_STYLE,   COMEDY_MODE, "A babu sends one form across five desks for no reason."],
    [HINDI_STYLE,   COMEDY_MODE, "The electricity goes out during an important inspection."],
    [HINDI_STYLE,   DRAMA_MODE,  "A pension file has been delayed for months and the family is under pressure."],
    [HINDI_STYLE,   DRAMA_MODE,  "An honest officer clashes with staff who prefer the old way of doing things."],
    [HINDI_STYLE,   DEBATE_MODE, "Kya sarkari daftar mein har process ko poori tarah digital kar dena chahiye?"],
    [HINDI_STYLE,   DEBATE_MODE, "Kya promotion seniority se honi chahiye ya merit se?"],
]


def create_app(
    orchestrator: SceneOrchestrator,
    loader: "CharacterLoader",
    ollama_available: bool,
    tts_available: bool,
):
    """Build and return the Gradio Blocks application with live streaming and character panel."""
    import gradio as gr
    import threading

    # ── shared mutable state ──────────────────────────────────────────────────
    _scene_state = {
        "running": False,
        "paused": False,
        "stop": False,
        "active_names": None,   # None = all characters for the style
    }

    def _initial_status() -> str:
        if not ollama_available:
            msg = "⚠️ LM Studio is not running. Start LM Studio, load a model, and enable the local server."
            if not tts_available:
                msg += " TTS disabled (Kokoro not installed)."
            return msg
        status = "✅ Ready. LM Studio server is running."
        if not tts_available:
            status += " TTS disabled (Kokoro not installed)."
        return status

    def _chars_for_style(show_style: str) -> list[Character]:
        return [c for c in orchestrator.characters if c.show == show_style]

    def _roster_html(show_style: str, active_names: list[str] | None) -> str:
        chars = _chars_for_style(show_style)
        if not chars:
            return "<p><em>No characters loaded for this style.</em></p>"
        rows = []
        for c in chars:
            active = active_names is None or c.name in active_names
            badge = "🟢" if active else "⚫"
            rows.append(f"<li>{badge} <strong>{c.name}</strong></li>")
        return "<ul style='margin:0;padding-left:1.2em'>" + "".join(rows) + "</ul>"

    # ── character panel helpers ───────────────────────────────────────────────

    def load_char_for_edit(name: str, show_style: str):
        chars = {c.name: c for c in _chars_for_style(show_style)}
        if name not in chars:
            return "", "", "", "", ""
        c = chars[name]
        return (
            c.name,
            c.personality,
            c.speaking_style,
            "\n".join(c.catchphrases),
            c.kokoro_voice,
        )

    def save_char(name, personality, speaking_style, catchphrases_text, kokoro_voice, show_style):
        if not name.strip():
            return "❌ Name cannot be empty.", gr.update()
        catchphrases = [l.strip() for l in catchphrases_text.splitlines() if l.strip()]
        if not catchphrases:
            return "❌ At least one catchphrase required.", gr.update()
        char = Character(
            name=name.strip(),
            show=show_style,
            personality=personality.strip(),
            speaking_style=speaking_style.strip(),
            catchphrases=catchphrases,
            kokoro_voice=kokoro_voice.strip() or "af_heart",
        )
        loader.save_character(char)
        # Reload orchestrator's character list
        orchestrator.characters = loader.load_all()
        new_choices = [c.name for c in _chars_for_style(show_style)]
        return f"✅ Saved {char.name}", gr.update(choices=new_choices)

    def delete_char(name, show_style):
        if not name:
            return "❌ Select a character first.", gr.update()
        loader.delete_character(name)
        orchestrator.characters = loader.load_all()
        new_choices = [c.name for c in _chars_for_style(show_style)]
        return f"🗑️ Deleted {name}", gr.update(choices=new_choices, value=None)

    def toggle_active(name, active_names_state, show_style):
        """Add or remove a character from the active roster."""
        if active_names_state is None:
            active_names_state = [c.name for c in _chars_for_style(show_style)]
        if name in active_names_state:
            active_names_state = [n for n in active_names_state if n != name]
        else:
            active_names_state = active_names_state + [name]
        _scene_state["active_names"] = active_names_state
        return active_names_state, _roster_html(show_style, active_names_state)

    def reset_roster(show_style):
        _scene_state["active_names"] = None
        return None, _roster_html(show_style, None)

    # ── scene generation ──────────────────────────────────────────────────────

    def generate_scene(show_style, scene_mode, scenario, num_exchanges, tts_enabled, active_names_state):
        _scene_state["running"] = True
        _scene_state["paused"] = False
        _scene_state["stop"] = False

        config = GenerationConfig(
            show_style=show_style,
            scenario=scenario,
            num_exchanges=int(num_exchanges),
            tts_enabled=tts_enabled,
            scene_mode=scene_mode,
        )

        active = active_names_state if active_names_state else None
        script_so_far = ""
        partial = None

        for partial in orchestrator.run_scene_streaming(config, active_names=active):
            if _scene_state["stop"]:
                break
            while _scene_state["paused"] and not _scene_state["stop"]:
                import time; time.sleep(0.3)
            if partial.error:
                yield partial.error, _roster_html(show_style, active), f"❌ {partial.error}"
                return
            script_so_far = partial.as_script()
            status = f"🎭 [{scene_mode}] Exchange {len(partial.turns)}/{int(num_exchanges)}…"
            yield script_so_far, _roster_html(show_style, active), status

        _scene_state["running"] = False
        n = len(partial.turns) if partial else 0
        yield script_so_far, _roster_html(show_style, active), f"✅ Done — {n} exchanges."

    def pause_scene():
        if _scene_state["running"]:
            _scene_state["paused"] = not _scene_state["paused"]
            return "▶️ Resume" if _scene_state["paused"] else "⏸ Pause"
        return "⏸ Pause"

    def stop_scene():
        _scene_state["stop"] = True
        _scene_state["running"] = False
        return "⏸ Pause"

    def refresh_char_list(show_style):
        return gr.update(choices=[c.name for c in _chars_for_style(show_style)])

    # ── UI layout ─────────────────────────────────────────────────────────────

    with gr.Blocks(title="Agentic Office Comedy") as app:
        gr.Markdown("# 🎭 Agentic Office Comedy")

        active_names_state = gr.State(None)  # None = all characters active

        with gr.Row():
            # ── LEFT: scene controls ──────────────────────────────────────────
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### Scene Setup")
                show_style = gr.Radio(
                    choices=[ENGLISH_STYLE, HINDI_STYLE],
                    value=ENGLISH_STYLE,
                    label="Show Style",
                )
                scene_mode = gr.Radio(
                    choices=SCENE_MODES,
                    value=COMEDY_MODE,
                    label="Scene Mode",
                )
                scenario = gr.Textbox(
                    value=SCENARIO_EXAMPLES[0][2],
                    label="Scenario / Topic",
                    lines=2,
                )
                num_exchanges = gr.Slider(minimum=4, maximum=12, value=6, step=1, label="Exchanges")
                tts_checkbox = gr.Checkbox(value=False, label="Enable TTS", interactive=tts_available)

                with gr.Row():
                    generate_btn = gr.Button("▶ Generate", variant="primary")
                    pause_btn = gr.Button("⏸ Pause")
                    stop_btn = gr.Button("⏹ Stop", variant="stop")

                gr.Examples(
                    examples=[[r[0], r[1], r[2]] for r in SCENARIO_EXAMPLES],
                    inputs=[show_style, scene_mode, scenario],
                    label="Example Scenarios",
                )

            # ── MIDDLE: live script output ────────────────────────────────────
            with gr.Column(scale=2):
                gr.Markdown("### Live Scene")
                script_output = gr.Textbox(
                    label="Script",
                    interactive=False,
                    lines=24,
                    max_lines=40,
                )
                status_box = gr.Textbox(
                    label="Status",
                    interactive=False,
                    value=_initial_status(),
                )

            # ── RIGHT: character panel ────────────────────────────────────────
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### 🧑‍🤝‍🧑 Cast")

                roster_html = gr.HTML(
                    value=_roster_html("English Office Comedy", None),
                    label="Active Characters",
                )

                char_selector = gr.Dropdown(
                    choices=[c.name for c in _chars_for_style("English Office Comedy")],
                    label="Select character to edit / toggle",
                    interactive=True,
                )

                with gr.Row():
                    toggle_btn = gr.Button("🔄 Toggle Active")
                    reset_btn = gr.Button("↺ Reset Roster")

                with gr.Accordion("✏️ Edit / Add Character", open=False):
                    edit_name = gr.Textbox(label="Name")
                    edit_personality = gr.Textbox(label="Personality", lines=2)
                    edit_style = gr.Textbox(label="Speaking Style", lines=2)
                    edit_catchphrases = gr.Textbox(
                        label="Catchphrases (one per line)", lines=3,
                        placeholder="That's what she said\nI am the world's best boss"
                    )
                    edit_voice = gr.Textbox(label="Kokoro Voice", value="af_heart")
                    with gr.Row():
                        save_btn = gr.Button("💾 Save", variant="primary")
                        delete_btn = gr.Button("🗑️ Delete", variant="stop")
                    char_msg = gr.Textbox(label="", interactive=False, lines=1)

        # ── event wiring ──────────────────────────────────────────────────────

        # Show style change → refresh char list and roster
        show_style.change(
            fn=lambda s: (
                gr.update(choices=[c.name for c in _chars_for_style(s)]),
                _roster_html(s, None),
                None,
            ),
            inputs=[show_style],
            outputs=[char_selector, roster_html, active_names_state],
        )

        # Select character → populate edit fields
        char_selector.change(
            fn=load_char_for_edit,
            inputs=[char_selector, show_style],
            outputs=[edit_name, edit_personality, edit_style, edit_catchphrases, edit_voice],
        )

        # Toggle active
        toggle_btn.click(
            fn=toggle_active,
            inputs=[char_selector, active_names_state, show_style],
            outputs=[active_names_state, roster_html],
        )

        # Reset roster
        reset_btn.click(
            fn=reset_roster,
            inputs=[show_style],
            outputs=[active_names_state, roster_html],
        )

        # Save character
        save_btn.click(
            fn=save_char,
            inputs=[edit_name, edit_personality, edit_style, edit_catchphrases, edit_voice, show_style],
            outputs=[char_msg, char_selector],
        ).then(
            fn=lambda s: _roster_html(s, None),
            inputs=[show_style],
            outputs=[roster_html],
        )

        # Delete character
        delete_btn.click(
            fn=delete_char,
            inputs=[char_selector, show_style],
            outputs=[char_msg, char_selector],
        ).then(
            fn=lambda s: _roster_html(s, None),
            inputs=[show_style],
            outputs=[roster_html],
        )

        # Pause / stop
        pause_btn.click(fn=pause_scene, outputs=[pause_btn])
        stop_btn.click(fn=stop_scene, outputs=[pause_btn])

        # Generate — streaming
        generate_btn.click(
            fn=generate_scene,
            inputs=[show_style, scene_mode, scenario, num_exchanges, tts_checkbox, active_names_state],
            outputs=[script_output, roster_html, status_box],
        )

    return app


# ---------------------------------------------------------------------------
# Application wiring and entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Load characters
    _loader = CharacterLoader(CHARACTERS_DIR)
    _characters = _loader.load_all()

    # 2. Try to initialize KokoroTTS
    _tts: KokoroTTS | None = None
    _tts_available = False
    try:
        _tts = KokoroTTS()
        _tts_available = True
        logger.info("KokoroTTS initialized successfully.")
    except ImportError:
        logger.warning("Kokoro not installed; TTS disabled.")

    # 3. Initialize OllamaClient and check availability
    _ollama = OllamaClient(
        model="nvidia/nemotron-3-nano-4b",
        base_url="http://localhost:1234",
        max_tokens=150,
        temperature=0.7,
        timeout=60.0,
        backend="lmstudio",
    )
    _ollama_available = _ollama.is_available()
    if not _ollama_available:
        logger.warning("LM Studio server is not reachable. Start LM Studio and enable the local server.")

    # 4. Initialize PromptBuilder and SceneOrchestrator
    _prompt_builder = PromptBuilder(transcript_window_size=4)
    _orchestrator = SceneOrchestrator(
        characters=_characters,
        ollama=_ollama,
        prompt_builder=_prompt_builder,
        tts=_tts,
    )

    # 5. Create and launch the Gradio app
    app = create_app(
        orchestrator=_orchestrator,
        loader=_loader,
        ollama_available=_ollama_available,
        tts_available=_tts_available,
    )
    app.launch()
