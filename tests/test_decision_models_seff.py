# coding: utf-8
"""``SeffModel``: Jev's wire schema on Seff's own host, free and text-only.

The contract is Jev's (same body, same reply). The connectivity test runs the real ``JevDecisionsClient``
over an ``httpx.MockTransport``, so the configured URL, the Bearer header and the JSON round-trip are
exercised without a network. A live test runs only when ``SEFF_API_URL`` and ``SEFF_API_KEY`` are set.
"""

from __future__ import annotations

import json
import os
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import httpx
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError

from decision_model_contract import OBSERVATION, PICK, DecisionModelContract
from s1a.decision_models import DecisionModel, Json, Observation, ScriptedTransport, SeffModel
from s1a.decision_models import seff

SEFF_ENV = {
    "SEFF_API_KEY": "seff-key",
    "SEFF_API_URL": "https://seff.test/v1/decisions",
    "SEFF_MODEL": "seff-test",
    "SEFF_TIMEOUT_S": "",
}
REPLY = {
    "model": "seff-test",
    "answers": {"pick": {"choice": "stand", "probabilities": {"hit": 0.1, "stand": 0.9}, "confidence": 0.9}},
    "usage": {"input_tokens": 42, "output_tokens": 7},
}


class TestSeffContract(DecisionModelContract, IsolatedAsyncioTestCase):
    def make(self) -> DecisionModel:
        return SeffModel(ScriptedTransport())

    def make_scripted(self, answers: list[dict[str, Json]]) -> DecisionModel:
        return SeffModel(ScriptedTransport(answers=answers))


class TestSeffFlags(TestCase):
    def test_seff_is_free_and_text_only(self) -> None:
        self.assertIs(SeffModel.bills_input_tokens, False)
        self.assertIs(SeffModel.supports_images, False)
        self.assertEqual(SeffModel.name, "seff")


class TestSimpleDecision(IsolatedAsyncioTestCase):
    async def test_a_simple_choice_is_the_decision_the_service_gave(self) -> None:
        model = SeffModel(ScriptedTransport(choose="stand"))
        answer = await model.choose(
            Observation({"player_total": 18, "dealer_upcard": 9}),
            {"hit": "take a card", "stand": "keep the hand"},
            rules="stand on 17 or more",
        )
        self.assertEqual(answer.key, "stand")
        self.assertAlmostEqual(answer.probabilities["stand"], 1.0)


class TestConnectivity(IsolatedAsyncioTestCase):
    async def test_the_real_client_posts_to_the_configured_endpoint_and_reads_a_decision(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=REPLY)

        with patch.dict(os.environ, SEFF_ENV):
            model = SeffModel.from_env(transport=httpx.MockTransport(handler))
        try:
            decision = await model.decide_many(OBSERVATION, {"pick": PICK})
        finally:
            await model.close()

        self.assertEqual(len(seen), 1)
        request = seen[0]
        self.assertEqual(str(request.url), "https://seff.test/v1/decisions")
        self.assertEqual(request.headers["Authorization"], "Bearer seff-key")
        body = json.loads(request.content)
        self.assertEqual(body["model"], "seff-test")
        self.assertEqual(body["state"], OBSERVATION.state)
        self.assertIn("pick", body["questions"])
        self.assertEqual(decision.choice("pick").key, "stand")
        self.assertEqual(decision.usage.input_tokens, 42)


class TestFromEnv(TestCase):
    def test_the_env_names_the_endpoint_key_and_model(self) -> None:
        with patch.dict(os.environ, SEFF_ENV):
            model = SeffModel.from_env()
        self.assertEqual(model.model, "seff-test")
        self.assertEqual(model._transport.url, "https://seff.test/v1/decisions")
        self.assertEqual(model._transport._client.headers["Authorization"], "Bearer seff-key")

    def test_the_model_defaults_when_unset(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_MODEL": ""}):
            self.assertEqual(SeffModel.from_env().model, seff.DEFAULT_SEFF_MODEL)

    def test_whitespace_around_the_key_is_stripped(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_API_KEY": "  seff-key  "}):
            model = SeffModel.from_env()
        self.assertEqual(model._transport._client.headers["Authorization"], "Bearer seff-key")

    def test_a_missing_key_is_a_config_error_naming_it(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_API_KEY": ""}):
            with self.assertRaises(BaseError) as caught:
                SeffModel.from_env()
        self.assertEqual(caught.exception.status, StatusCode.MODEL_SERVICE_CONFIG_ERROR)
        self.assertIn("SEFF_API_KEY", str(caught.exception))

    def test_a_missing_url_is_a_config_error_naming_it(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_API_URL": ""}):
            with self.assertRaises(BaseError) as caught:
                SeffModel.from_env()
        self.assertEqual(caught.exception.status, StatusCode.MODEL_SERVICE_CONFIG_ERROR)
        self.assertIn("SEFF_API_URL", str(caught.exception))

    def test_the_timeout_defaults_to_the_shared_decision_timeout(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_TIMEOUT_S": "", "S1A_DECISION_TIMEOUT_S": ""}):
            self.assertEqual(SeffModel.from_env()._transport._timeout_s, 5.0)

    def test_the_timeout_variable_sets_the_deadline(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_TIMEOUT_S": "30"}):
            self.assertEqual(SeffModel.from_env()._transport._timeout_s, 30.0)

    def test_an_explicit_deadline_wins(self) -> None:
        with patch.dict(os.environ, {**SEFF_ENV, "SEFF_TIMEOUT_S": "30"}):
            self.assertEqual(SeffModel.from_env(timeout_s=2.0)._transport._timeout_s, 2.0)

    def test_a_bad_timeout_is_a_config_error_naming_it(self) -> None:
        for raw in ("abc", "0", "-3", "nan", "inf", "1e9999"):
            with self.subTest(raw=raw), patch.dict(os.environ, {**SEFF_ENV, "SEFF_TIMEOUT_S": raw}):
                with self.assertRaises(BaseError) as caught:
                    SeffModel.from_env()
                self.assertEqual(caught.exception.status, StatusCode.MODEL_SERVICE_CONFIG_ERROR)
                self.assertIn("SEFF_TIMEOUT_S", str(caught.exception))


class TestLiveSeff(IsolatedAsyncioTestCase):
    async def test_a_live_simple_decision_reaches_the_endpoint(self) -> None:
        if os.getenv("S1A_LIVE_SEFF") != "1":
            self.skipTest("set S1A_LIVE_SEFF=1 (with SEFF_API_URL and SEFF_API_KEY) for the live Seff smoke")
        from s1a import config

        config.load_env()
        model = SeffModel.from_env()
        try:
            answer = await model.choose(
                Observation({"player_total": 18, "dealer_upcard": 9}),
                {"hit": "take a card", "stand": "keep the hand"},
                rules="stand on 17 or more",
            )
        finally:
            await model.close()
        self.assertIn(answer.key, ("hit", "stand"))
        self.assertAlmostEqual(sum(answer.probabilities.values()), 1.0, delta=0.02)
