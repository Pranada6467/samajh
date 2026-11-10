"""A fake LLM for the extractor tests. It replays outputs keyed by schema, question and reply."""

import json
import re
from functools import cache
from pathlib import Path

from samajh.clients.errors import LlmOutputInvalid
from samajh.clients.llm import LlmResult

RECORDED = Path(__file__).parent / "recorded" / "dev_gpt-6-luna.json"
_USER = re.compile(r"Assistant's question: <<<(.*?)>>>\nCustomer's reply: <<<(.*?)>>>", re.DOTALL)

Key = tuple[str, str, str]  # schema name, bot question, customer reply


@cache
def recorded_outputs() -> dict[Key, dict]:
    calls = json.loads(RECORDED.read_text())["calls"]
    return {(c["schema"], c["question"], c["reply"]): c["output"] for c in calls}


class FakeLlm:
    """`outputs` maps a call to the JSON the model returns. `replies` overrides by reply text alone.

    A screening call with no recorded output returns no claims and no concerns. Any other call
    with no output fails the test. `sent` keeps every request, so a test can read the prompts.
    """

    def __init__(self, outputs: dict[Key, dict] | None = None) -> None:
        self.outputs = dict(outputs or {})
        self.replies: dict[tuple[str, str], dict] = {}  # (schema name, reply) -> output
        self.invalid: set[str] = set()  # replies for which the model never returns valid output
        self.sent: list[list] = []

    def say(self, schema: str, reply: str, **output) -> None:
        """Change fields of the recorded output for one reply, or set a whole new output."""
        recorded = next((v for (s, _, r), v in self.outputs.items() if (s, r) == (schema, reply)), {})
        self.replies[(schema, reply)] = recorded | output

    def complete(self, schema, messages, *, model=None, max_tokens=1024):
        self.sent.append(list(messages))
        question, reply = _USER.search(messages[1].content).groups()
        if reply in self.invalid:
            raise LlmOutputInvalid(model="fake", attempts=3, last_error="not valid JSON")
        name = schema.__name__
        output = self.replies.get((name, reply)) or self.outputs.get((name, question, reply))
        if output is None:
            if name != "ScreenReply":
                raise AssertionError(f"no output recorded for {name} / {reply!r}")
            output = {"claims": [], "concerns": []}
        return LlmResult(
            value=schema.model_validate(output), model=model or "fake", prompt_tokens=0, completion_tokens=0,
            usd=0.0, cache_hit=True, attempts=0, generation_id=None,
        )  # fmt: skip

    def prompts(self) -> str:
        return "\n".join(message.content for request in self.sent for message in request)
