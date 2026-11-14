"""Run the post-call chain (samajh.pipeline.run_text) on 20 consent cases of a bank-B run, recording the tier and what
the extraction made of the consent answers.  chain.py RUN-B.jsonl OUT.jsonl"""
import json, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)
import samajh
from samajh.pipeline import default_llm, run_text
from samajh.types import Transcript
sys.path.insert(0, str(Path(__file__).parent))
from run import record_for
B = {r["id"]: r for r in (json.loads(x) for x in (Path(__file__).parents[1] / "banks/B-half-answers.jsonl").read_text().splitlines())}
ids = [i for i, g in B.items() if g["slot"] == "consent" and g["subkind"] in ("how_only", "what_only")] + \
      [i for i, g in B.items() if g["slot"] == "consent" and g["subkind"] == "both"][:6]
res = {r["id"]: r for r in (json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines())}
llm = default_llm()
out = []
for i in ids:
    t = Transcript.model_validate(res[i]["transcript"])
    run = run_text(t, record_for("Ramesh"), llm)
    p = run.extraction.raw.products[0]
    cr = run.result
    out.append({"id": i, "subkind": B[i]["subkind"], "tier": cr.tier.value,
                "consent_given": json.loads(p.consent_given.model_dump_json()),
                "consent_method": json.loads(p.consent_method.model_dump_json()),
                "gaps": [json.loads(g.model_dump_json()) for g in cr.products[0].gaps],
                "flags": [f.rule_id.value + ":" + f.reason.value for f in cr.products[0].flags]})
    print(i, B[i]["subkind"], cr.tier.value, p.consent_given.status, p.consent_method.status, getattr(p.consent_method, "value", None))
Path(sys.argv[2]).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
print("samajh", samajh.__file__, "spent", getattr(getattr(llm, "_llm", llm), "spent_usd", None))
