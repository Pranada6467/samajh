"""Short follow-up sequences (verifier-written after the main run, to explain what it showed).
uv run python references/reviews/iter2/probes/p2_r2_extras.py  -> p2_r2_extras.jsonl (never overwritten)"""
import json, sys, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from p2_r2_run import Call, make, save_rows, save_latency

H = "हाँ जी, मैं ही बोल रहा हूँ"
SEQS = [
    ("year_dont_remember_twice", "hi", [H, "हाँ", "याद नहीं", "याद नहीं"]),
    ("year_wrong_then_dont_remember", "hi", [H, "हाँ", "1985", "याद नहीं"]),
    ("year_two_guesses_one_turn_then_right", "hi-en", ["haan main hi bol raha hoon", "haan", "1980 ya 1981", "1984"]),
    ("year_three_in_one_turn", "hi-en", ["haan main hi bol raha hoon", "haan", "1982, 1983 ya 1984"]),
    ("year_who_loop", "hi", [H, "हाँ", "कौन बोल रहा है?", "कौन बोल रहा है?", "कौन बोल रहा है?", "कौन बोल रहा है?"]),
    ("year_loose_then_tight", "hi-en", ["haan main hi bol raha hoon", "haan", "mera 1984 hai", "1984"]),
    ("year_loose_twice", "hi-en", ["haan main hi bol raha hoon", "haan", "mera 1984 hai", "mera 1984 hai na"]),
    ("year_spouse_after_claim", "hi", [H, "हाँ", "रुको पत्नी से पूछता हूँ... वो कह रही है 1984"]),
    ("callback_but_now", "hi", [H, "अभी बिज़ी था, अब बोलो", "अभी बोलिए, अभी फ़्री हूँ"]),
    ("callback_but_now_en", "hi-en", ["haan ji, main hi bol raha hoon", "time to nahi hai zyada par chalo pucho", "abhi pucho na"]),
    ("real_phone_then_ji_boliye", "hi", ["हाँ, रमेश जी से हो रही है।", "हाँ जी, बोलिए"]),
    ("real_phone_then_main_hi", "hi", ["हाँ, रमेश जी से हो रही है।", "हाँ, मैं ही बोल रहा हूँ"]),
    ("real_phone_then_name_again", "hi", ["हाँ, रमेश जी से हो रही है।", "हाँ जी, रमेश ही बोल रहा है"]),
    ("purpose_twice_then_ack", "hi", ["हाँ जी", "किस बारे में है?", "किस बारे में है?", "हाँ"]),
]


def main(arm):
    interp, rec = make(arm)
    rows = []
    for name, lang, turns in SEQS:
        call = Call("ramesh", lang, interp, rec, f"x-{name}")
        for t in turns:
            if call.end:
                break
            call.say(t)
        rows.append({"id": name, "arm": arm, "outcome": call.outcome, "log": call.log})
        print(f"--- {arm} {name}: {call.outcome}")
        for e in call.log:
            print("   ", e["who"], e.get("keys", ""), e["text"][:110])
    time.sleep(3.0)
    save_rows(f"p2_r2_extras_{arm}", rows)
    save_latency(f"extras_{arm}", rec, interp)


if __name__ == "__main__":
    for arm in sys.argv[1:] or ["rules", "live", "failing"]:
        main(arm)
