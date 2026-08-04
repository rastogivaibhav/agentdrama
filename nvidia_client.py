"""
NVIDIA API Client Wrapper
==========================

Provides OpenAI-compatible interface for NVIDIA DeepSeek API with streaming
support and reasoning/thinking token handling.

Uses only Python stdlib — no external HTTP libraries required.
"""

import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class NvidiaClient:
    """HTTP wrapper for NVIDIA DeepSeek API (OpenAI-compatible /v1/chat/completions).

    Supports streaming responses with reasoning tokens and structured thinking output.
    Uses only urllib — no external HTTP libraries required.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-ai/deepseek-v4-flash",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        max_tokens: int = 150,
        temperature: float = 0.7,
        timeout: float = 30.0,
        enable_reasoning: bool = False,
        reasoning_effort: str = "medium",  # "low", "medium", "high"
    ) -> None:
        """
        Initialize NVIDIA DeepSeek client.

        Args:
            api_key: NVIDIA API key (must be provided via environment variable)
            model: Model name (default: deepseek-v4-flash)
            base_url: API endpoint
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)
            timeout: Request timeout in seconds
            enable_reasoning: Whether to enable chain-of-thought reasoning
            reasoning_effort: Reasoning level ("low", "medium", "high") - only used if enable_reasoning=True
        """
        if not api_key or not api_key.strip():
            raise ValueError("NVIDIA_API_KEY must be provided and non-empty")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.enable_reasoning = enable_reasoning
        self.reasoning_effort = reasoning_effort

    def generate(self, prompt: str) -> str:
        """Send a prompt and return generated text (single-string interface).

        For non-streaming, collects full reasoning + content response.
        """
        return self._generate_openai_nonstreaming(prompt)

    def generate_chat(self, system: str, user: str) -> str:
        """Send system + user message pair via chat completions API.

        Args:
            system: System prompt
            user: User message

        Returns:
            Generated text response (reasoning stripped if present)
        """
        return self._generate_openai_nonstreaming(user, system=system)

    def generate_chat_streaming(self, system: str, user: str):
        """Generator — yields reasoning and content chunks as they arrive.

        Each yield is a dict with optional keys:
            - 'reasoning': reasoning token chunk
            - 'content': content token chunk
            - 'error': error message (on failure)
        """
        yield from self._generate_openai_streaming(user, system=system)

    # ── Non-streaming implementation ──────────────────────────────────────────

    def _generate_openai_nonstreaming(self, prompt: str, system: str | None = None) -> str:
        """POST to /v1/chat/completions (non-streaming).

        Collects the full response and extracts content + reasoning.
        """
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

        # Add reasoning parameters if enabled
        if self.enable_reasoning:
            payload["extra_body"] = {
                "chat_template_kwargs": {
                    "thinking": True,
                    "reasoning_effort": self.reasoning_effort,
                }
            }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            logger.error("NVIDIA API returned HTTP %d", exc.code)
            return f"[generation failed: HTTP {exc.code}]"
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
                logger.error("NVIDIA API request timed out after %.1fs", self.timeout)
                return "[generation timed out]"
            logger.error("NVIDIA API connection error: %s", exc)
            return "[connection error: NVIDIA API unavailable]"
        except socket.timeout:
            logger.error("NVIDIA API request timed out (socket)")
            return "[generation timed out]"
        except OSError as exc:
            logger.error("NVIDIA API I/O error: %s", exc)
            return "[connection error: NVIDIA API unavailable]"

        try:
            data = json.loads(raw)
            # Extract content, skip reasoning in non-streaming mode
            return data["choices"][0]["message"]["content"].strip()
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.error("Failed to parse NVIDIA API response: %s", exc)
            return "[generation failed: invalid response]"

    # ── Streaming implementation ──────────────────────────────────────────────

    def _generate_openai_streaming(self, prompt: str, system: str | None = None):
        """Generator — stream chunks from /v1/chat/completions.

        Yields dicts with 'reasoning' and/or 'content' keys for each chunk.
        """
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
            "stream": True,
        }

        # Add reasoning parameters if enabled
        if self.enable_reasoning:
            payload["extra_body"] = {
                "chat_template_kwargs": {
                    "thinking": True,
                    "reasoning_effort": self.reasoning_effort,
                }
            }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                for line in response:
                    line = line.decode("utf-8").strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break

                    try:
                        chunk_data = json.loads(line)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})

                        # Extract reasoning
                        reasoning = delta.get("reasoning") or delta.get("reasoning_content")
                        if reasoning:
                            yield {"reasoning": reasoning}

                        # Extract content
                        content = delta.get("content")
                        if content:
                            yield {"content": content}

                    except json.JSONDecodeError:
                        logger.debug("Skipped malformed chunk: %s", line)
                        continue

        except urllib.error.HTTPError as exc:
            logger.error("NVIDIA API returned HTTP %d", exc.code)
            yield {"error": f"HTTP {exc.code}"}
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
                logger.error("NVIDIA API request timed out after %.1fs", self.timeout)
                yield {"error": "Request timed out"}
            else:
                logger.error("NVIDIA API connection error: %s", exc)
                yield {"error": "Connection failed"}
        except socket.timeout:
            logger.error("NVIDIA API request timed out (socket)")
            yield {"error": "Request timed out"}
        except OSError as exc:
            logger.error("NVIDIA API I/O error: %s", exc)
            yield {"error": "I/O error"}

    def is_available(self) -> bool:
        """Check if NVIDIA API is reachable and auth works.

        Makes a simple HEAD request to the API endpoint.
        Returns True on success, False on any exception — never raises.
        """
        url = f"{self.base_url}/v1/models"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                _ = response.read()
            logger.debug("NVIDIA API reachable at %s", self.base_url)
            return True
        except Exception as exc:
            logger.warning("NVIDIA API not reachable at %s: %s", self.base_url, exc)
            return False
