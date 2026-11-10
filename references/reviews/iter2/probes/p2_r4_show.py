import json, sys
from pathlib import Path
H = Path(__file__).parent
for arm in ("live", "failing"):
    print("=====", arm)
    for l in (H / f"p2_r4_out_{arm}.jsonl").read_text().splitlines():
        r = json.loads(l); g = r["group"]
        if g == "g1":
            print(g, r["id"], r["kind"], "route=", (r.get("route") or "NONE")[:20], "| end", r.get("end"), "| pos", r.get("pos_after"),
                  "| keys", r.get("keys_after"), "| named", r.get("named_after"), "| deg", r.get("degraded"))
        elif g == "g2":
            print(g, r["id"], r["kind"], r["stage"], "| at", r.get("at"), "| now", r.get("end_now"), "| next", r.get("next_keys"),
                  "| namedBefore", r.get("named_before_pass"), "| passOn", r.get("who_passed_on_follow"), "| namedAfter", r.get("named_after_follow"),
                  "| final", r.get("final_end") or r.get("final_pos"), "| deg", r.get("degraded"))
        elif g == "g3":
            print(g, r["id"], r["kind"], r["text"], "|", r.get("result"), "| keys", r.get("keys_after"), "| named", r.get("named_after"), "| deg", r.get("degraded"))
        else:
            print(g, r["id"], r["kind"], r["stage"], "reached", r.get("reached"), "| end", r.get("end"), "| pos", r.get("pos_after"), "| sc", r.get("speaker_confirmed"),
                  "| keys", r.get("keys_after"), "| named", r.get("named_after"), "| deg", r.get("degraded"))
