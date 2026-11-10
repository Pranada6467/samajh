from __future__ import annotations

import secrets
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from samajh.clients.llm import LlmClient, Message


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_kind: Literal["insurance", "fixed_deposit", "not_stated"]
    nonce: str


@pytest.mark.live
def test_live_call_validates_then_hits_the_cache() -> None:
    nonce = secrets.token_hex(8)
    messages = [
        Message(role="system", content="Fill the schema from the user's text. Copy the nonce exactly."),
        Message(role="user", content=f"nonce {nonce}. हाँ, loan के साथ insurance भी दिया गया था।"),
    ]
    client = LlmClient.from_env(usd_cap=0.05)

    first = client.complete(Reply, messages, max_tokens=100)
    assert first.value.product_kind == "insurance" and first.value.nonce == nonce
    assert first.cache_hit is False and first.attempts >= 1 and first.usd >= 0
    assert first.prompt_tokens > 0 and first.completion_tokens > 0
    assert client.spent_usd == pytest.approx(first.usd)

    second = client.complete(Reply, messages, max_tokens=100)
    assert second.cache_hit is True and second.usd == 0.0 and second.value == first.value
    assert client.spent_usd == pytest.approx(first.usd)
