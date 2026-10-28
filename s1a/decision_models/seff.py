# coding: utf-8
"""Seff: Jev's wire schema on Seff's own host. Free (unbilled) and text-only, like ``laya-served``."""

from __future__ import annotations

import math
import os

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error

from s1a.decision_models.jev import JevModel
from s1a.decision_models.wire import JevDecisionsClient, decisions_timeout_from_env

DEFAULT_SEFF_MODEL = "seff-1.0"


def _required(name: str, what: str) -> str:
    """``name`` from the environment, stripped; a config error naming it when empty.

    ``JevDecisionsClient`` guards only the key (and its message says "Jev"), and it accepts an empty URL,
    which would fail later inside the request. Both are checked here so the error names the Seff variable.
    """
    value = (os.getenv(name) or "").strip()
    if not value:
        raise build_error(
            StatusCode.MODEL_SERVICE_CONFIG_ERROR,
            error_msg=f"no Seff {what}: set {name} in .env or the environment",
        )
    return value


def seff_timeout_from_env() -> float:
    """One decision's deadline: ``SEFF_TIMEOUT_S`` when set, else the shared ``S1A_DECISION_TIMEOUT_S``/5 s."""
    raw = (os.getenv("SEFF_TIMEOUT_S") or "").strip()
    if not raw:
        return decisions_timeout_from_env()
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    # float() also reads nan, inf and 1e9999 (inf): nan passes `<= 0` and poisons the deadline, inf removes it
    if not math.isfinite(value) or value <= 0:
        raise build_error(
            StatusCode.MODEL_SERVICE_CONFIG_ERROR,
            error_msg=f"SEFF_TIMEOUT_S must be a finite, positive number of seconds, not {raw!r}",
        )
    return value


class SeffModel(JevModel):
    """Seff's decisions endpoint: Jev's wire body and reply on another host, free and text-only."""

    name = "seff"
    bills_input_tokens = False  # free, like laya-served: the caller's own server, not Jev's pricing
    supports_images = False

    @classmethod
    def from_env(cls, *, timeout_s: float | None = None) -> "SeffModel":
        """Seff from ``SEFF_API_KEY`` / ``SEFF_API_URL`` / ``SEFF_MODEL``.

        The deadline is ``timeout_s`` when given, else ``SEFF_TIMEOUT_S``, else ``S1A_DECISION_TIMEOUT_S``/5 s.
        """
        api_key = _required("SEFF_API_KEY", "key")
        url = _required("SEFF_API_URL", "endpoint")
        model = (os.getenv("SEFF_MODEL") or "").strip() or DEFAULT_SEFF_MODEL
        deadline = timeout_s if timeout_s is not None else seff_timeout_from_env()
        return cls(JevDecisionsClient(api_key=api_key, url=url, model=model, timeout_s=deadline))
