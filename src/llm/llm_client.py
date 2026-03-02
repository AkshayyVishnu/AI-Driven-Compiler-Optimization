"""
LLM Client for AI-Driven Compiler Optimization System

Connects to Qwen 2.5 Coder 7B via Ollama's HTTP API.
Falls back to a stub response when Ollama is not running, so the rest
of the system can always be tested/used offline.
"""

import json
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ── Ollama configuration ────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL   = "qwen2.5-coder:7b"


def _try_import_requests():
    try:
        import requests  # type: ignore
        return requests
    except ImportError:
        return None


class LLMClient:
    """
    Client for Qwen 2.5 Coder 7B via Ollama.

    Usage
    -----
    client = LLMClient()
    response = client.generate("Explain this code: ...")
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: int = 360,
        max_retries: int = 2,
    ):
        self.model      = model
        self.base_url   = base_url.rstrip("/")
        self.timeout    = timeout
        self.max_retries = max_retries
        self._requests  = _try_import_requests()
        self._available = self._check_ollama()

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a completion.

        Returns the raw text response.  On any failure the stub is returned so
        callers always receive a parseable string.
        """
        if not self._available:
            logger.warning("Ollama not available – returning stub response")
            return self._stub_response(prompt)

        payload: Dict[str, Any] = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        for attempt in range(1, self.max_retries + 2):
            try:
                resp = self._requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except Exception as exc:
                logger.warning(f"LLM attempt {attempt} failed: {exc}")
                if attempt <= self.max_retries:
                    time.sleep(1)

        logger.error("All LLM attempts failed – returning stub response")
        return self._stub_response(prompt)

    def is_available(self) -> bool:
        """Return True if Ollama is reachable."""
        return self._available

    def health_check(self) -> Dict[str, Any]:
        """Return a dict describing connectivity status."""
        available = self._check_ollama()
        self._available = available
        return {
            "available":  available,
            "model":      self.model,
            "base_url":   self.base_url,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _check_ollama(self) -> bool:
        if self._requests is None:
            logger.warning("'requests' not installed – Ollama unavailable")
            return False
        try:
            resp = self._requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    # ── Stub (offline / fallback) ─────────────────────────────────────────────

    def _stub_response(self, prompt: str) -> str:
        """
        Return a minimal well-formed CoT JSON string so that upstream parsers
        always receive valid input even when the LLM is offline.
        """
        hint = ""
        p = prompt.lower()
        if "analyz" in p or "detect" in p:
            hint = "Rule-based analysis completed (LLM offline stub)."
        elif "optim" in p or "fix" in p or "transform" in p:
            hint = "Optimization suggestions generated (LLM offline stub)."
        elif "verif" in p:
            hint = "Verification reasoning completed (LLM offline stub)."
        else:
            hint = "Task processed (LLM offline stub)."

        stub = {
            "reasoning_steps": [
                "Step 1: Parsed the input code.",
                "Step 2: Applied rule-based heuristics.",
                "Step 3: " + hint,
            ],
            "findings": [],
            "conclusion": hint,
            "confidence": 0.5,
        }
        return "```json\n" + json.dumps(stub, indent=2) + "\n```"
