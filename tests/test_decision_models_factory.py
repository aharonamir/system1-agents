# coding: utf-8
"""Model name to decision_model, from the environment: ``build_model`` is the door every front uses."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError

from s1a.decision_models import (
    DECISION_MODEL_NAMES,
    JevModel,
    LayaModel,
    RandomModel,
    RuleModel,
    SeffModel,
    build_model,
)
from s1a.decision_models.cua_four_b import CuaFourBModel

KEYS = {"TYPESAFE_API_KEY": "k", "TYPESAFE_API_URL": "", "TYPESAFE_MODEL": "", "OPENROUTER_API_KEY": ""}
SEFF_KEYS = {"SEFF_API_KEY": "k", "SEFF_API_URL": "https://seff.test/v1/decisions", "SEFF_MODEL": ""}


class TestBuildModel(TestCase):
    def test_cua_four_b_is_explicit_and_unknown_variants_fail(self) -> None:
        with patch.dict(os.environ, {"CUA_S1_VARIANT": "4b"}), patch.object(CuaFourBModel, "from_env") as build:
            self.assertIs(build_model("cua"), build.return_value)
        with patch.dict(os.environ, {"CUA_S1_VARIANT": "typo"}), self.assertRaises(ValueError):
            build_model("cua")

    def test_every_name_builds_its_class(self) -> None:
        with patch.dict(os.environ, KEYS):
            self.assertIsInstance(build_model("jev"), JevModel)
        fake_laya = SimpleNamespace(
            load=lambda *a, **k: SimpleNamespace(cfg={}, system_one=lambda state, questions: {})
        )
        with patch.dict(sys.modules, {"laya": fake_laya}), patch.dict(os.environ, {"LAYA_SUBFOLDER": ""}):
            self.assertIsInstance(build_model("laya"), LayaModel)
        self.assertIsInstance(build_model("random", seed=3), RandomModel)
        rule = build_model("rule", rule=("always-inc", lambda state, options: "inc"))
        self.assertIsInstance(rule, RuleModel)
        self.assertEqual(rule.name, "always-inc")
        self.assertEqual(
            DECISION_MODEL_NAMES, ("jev", "seff", "clm", "laya", "laya-served", "cua", "omnijev", "random", "rule")
        )

    def test_the_errors(self) -> None:
        with self.assertRaises(RuntimeError):
            build_model("rule")
        with self.assertRaises(ValueError):
            build_model("llm")
        for model_name, module in (("laya", "laya"), ("cua", "cua_s1.nano")):
            with patch.dict(sys.modules, {module: None}):
                with self.assertRaises(BaseError) as caught:
                    build_model(model_name)
            self.assertEqual(caught.exception.status, StatusCode.MODEL_SERVICE_CONFIG_ERROR)
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            with self.assertRaises(BaseError):
                build_model("jev")

    def test_the_seed_and_the_rule_reach_their_models(self) -> None:
        self.assertEqual(build_model("random", seed=1).name, "random")
        self.assertEqual(build_model("rule", rule=("r", lambda s, o: "a")).name, "r")

    def test_seff_builds_from_its_own_env(self) -> None:
        with patch.dict(os.environ, SEFF_KEYS):
            decision_model = build_model("seff")
        self.assertIsInstance(decision_model, SeffModel)
        self.assertEqual((decision_model.name, decision_model.model), ("seff", "seff-1.0"))

    def test_seff_without_its_key_is_a_config_error_naming_it(self) -> None:
        with patch.dict(os.environ, {**SEFF_KEYS, "SEFF_API_KEY": ""}):
            with self.assertRaises(BaseError) as caught:
                build_model("seff")
        self.assertEqual(caught.exception.status, StatusCode.MODEL_SERVICE_CONFIG_ERROR)
        self.assertIn("SEFF_API_KEY", str(caught.exception))
