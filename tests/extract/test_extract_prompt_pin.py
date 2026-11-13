"""The exact text of every request the extractor sends, pinned by sha256.

The retraction guards rest on model readings: a one-line change to the change-check prompt (the
`ChangeReply` docstring is sent as the schema's description) once flipped a withdrawn premium to a
false `clear` (`references/reviews/iter2/verify-P3a-r3.md`, addendum). So any change to a prompt,
an example, a wire model's fields or docstrings, or how a reply is numbered fails here first.
"""

import hashlib
import json

import pytest

from samajh.clients.llm import strict_json_schema
from samajh.extract._prompt import change_messages, messages, screen_messages
from samajh.extract._wire import SCHEMA, ChangeReply, ScreenReply
from samajh.types import Language

QUESTION = "वह क्या है: बीमा, एफ़डी, या कुछ और?"
REPLIES = ("बीमा है नहीं पता नहीं क्या है", "डिपॉज़िट है, अरे नहीं, बीमा है।", "insurance hai nahi pata nahi")

RERUN = (
    "the prompt changed: rerun the retraction probes (references/reviews/iter2/probes/p3a_r3_llm*.py, "
    "p3a_r3_carry2.py) and update this hash"
)


def _digest(body: object) -> str:
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _requests(build) -> list:
    return [
        [m.model_dump() for m in build(kind, language, reply)]
        for kind in SCHEMA
        for language in Language
        for reply in REPLIES
    ]


RENDERED = {
    "answer requests": lambda: _requests(lambda k, lang, r: messages(k, lang, QUESTION, r)),
    "change-check requests": lambda: _requests(lambda k, lang, r: change_messages(k, lang, QUESTION, r)),
    "screening requests": lambda: [
        [m.model_dump() for m in screen_messages(language, QUESTION, reply)]
        for language in Language
        for reply in REPLIES
    ],
    "wire schemas": lambda: {
        schema.__name__: strict_json_schema(schema) for schema in (*SCHEMA.values(), ScreenReply, ChangeReply)
    },
    "change-check schema": lambda: strict_json_schema(ChangeReply),
}

# P5 fix round (2026-11-13): answer requests and wire schemas re-pinned on purpose (premium `free`,
# payment `not_charged`, consent: a phone yes is `recorded_call` unless not recorded, a denial line and `money_back` in the money-back probe). The
# change-check requests, the screening requests and the change-check schema did not change.
PINNED = {
    "answer requests": "e1da9b415e31406aad594ef1e96765a180803c0f836292c77c59faf22318154a",
    "change-check requests": "77c186ac318d97149d1f03708df00ade3f0722597e3f31fec61c56799e7a0fa9",
    "screening requests": "3397cbec185617549019027a5ae9ff3d6aaa955a5d69238d60e7467a759802ff",
    "wire schemas": "12dde0abf56818a80b62dc463cd13c9c6376a5fad1eeaf40bdbbee9d071da6ac",
    "change-check schema": "6b2ffc35b07d80063ec00de2a452b9e2315b45e50f649aaf6ed79ad2d04f2f12",
}


@pytest.mark.parametrize("name", PINNED)
def test_the_prompt_text_is_pinned(name):
    assert _digest(RENDERED[name]()) == PINNED[name], f"{name}: {RERUN}"
