"""Fresh third-party probes (verifier, iteration 2). Each script is what a person who is NOT Ramesh says
to successive bot lines. Counts bot lines after which a listener knows of a lender, a loan or an amount."""

from __future__ import annotations

import re
import sys

from p2_kit import LEAK, bot_after_first, dump, play, save

LOAN = re.compile(r"लोन|loan", re.I)
LENDER = re.compile(r"Udaharan", re.I)

# (id, lang, turns). Wife/relative scripts give the real year (1984) when asked, as a spouse would.
SCRIPTS = [
    ("wife-haanji-then-wife", "hi", ["हाँ जी", "मैं उनकी वाइफ़ बोल रही हूँ, वो बाहर गए हैं", "1984"]),
    ("wife-haan-bolo", "hi", ["हां बोलो", "हां", "उन्नीस सौ चौरासी"]),
    ("wife-ji-boliye", "hi", ["जी बोलिए", "जी", "1984"]),
    ("wife-ji-alone", "hi", ["जी", "जी", "चौरासी"]),
    ("wife-haan-all", "hi", ["हाँ", "हाँ", "हाँ", "हाँ", "हाँ", "हाँ"]),
    ("wife-ha-hello", "hi-en", ["haa hello", "haan", "1984"]),
    ("wife-ji-namaste", "hi", ["जी नमस्ते", "हाँ ठीक है", "1984"]),
    ("wife-ghar-wali", "hi", ["मैं उनकी घरवाली हूँ", "1984"]),
    ("wife-misses", "hi-en", ["main mrs ramesh bol rahi hoon", "1984"]),
    ("wife-he-is-bathing", "hi-en", ["woh bathroom mein hain abhi", "1984"]),
    ("wife-in-bathroom-dev", "hi", ["वो बाथरूम में हैं, आप होल्ड करिए", "1984"]),
    ("son-papa", "hi", ["पापा अभी सो रहे हैं", "1984"]),
    ("son-dad-not-home", "hi-en", ["dad ghar pe nahi hai, main unka beta hoon", "1984"]),
    ("son-haan-papa-ka-phone", "hi", ["हाँ, ये पापा का ही फ़ोन है", "1984"]),
    ("son-yes-his-phone", "hi-en", ["yes this is his phone", "1984"]),
    ("son-haan-unka-number", "hi", ["हाँ नंबर तो उन्हीं का है", "1984"]),
    ("daughter-haan-boliye-then-papa", "hi", ["हाँ बोलिए", "हाँ", "पापा का साल चाहिए? 1984"]),
    ("father-mera-beta", "hi", ["रमेश मेरा बेटा है, क्या काम है", "1984"]),
    ("mother-woh-kaam-pe", "hi", ["वो तो काम पे गया है, मैं उसकी माँ हूँ", "1984"]),
    ("colleague-desk", "hi-en", ["Ramesh sir apni seat pe nahi hain, main colleague bol raha hoon", "1984"]),
    ("colleague-office", "hi-en", ["office line hai ye, Ramesh ji lunch pe gaye", "1984"]),
    ("peon-sahab", "hi", ["साहब मीटिंग में हैं", "1984"]),
    ("who-is-this", "hi", ["कौन बोल रहा है?", "आप बताइए पहले, किस बारे में है?", "1984"]),
    ("who-is-this-en", "hi-en", ["who is this?", "pehle aap batao kaun ho", "1984"]),
    ("kiska-kaam", "hi", ["किससे बात करनी है? क्या काम है?", "बताइए क्या काम है", "1984"]),
    ("wrong-number", "hi", ["रॉन्ग नंबर है"]),
    ("wrong-number-en", "hi-en", ["galat number lagaya aapne"]),
    ("no-ramesh-here", "hi", ["यहाँ कोई रमेश नहीं रहता"]),
    ("haan-bolo-then-mai-uska-bhai", "hi-en", ["haan bolo", "main uska bhai hoon, bolo kya kaam hai", "1984"]),
    ("haan-then-ruko-deta-hoon", "hi", ["हाँ", "रुकिए, उनको फ़ोन देता हूँ", "1984"]),
    ("haan-ji-then-who", "hi", ["हाँ जी", "पर आप कौन?", "हाँ ठीक है", "1984"]),
    ("silence-then-noise", "hi", ["", "हम्म", "1984"]),
    ("noise-words", "hi", ["हेलो हेलो", "हाँ हाँ", "1984"]),
    ("hello-kaun", "hi-en", ["hello? kaun?", "haan", "1984"]),
    ("third-person-he", "hi-en", ["he is not available right now", "1984"]),
    ("sister-in-law", "hi", ["भाभी बोल रही हूँ, भैया बाहर हैं", "1984"]),
    ("haan-main-hi-hoon-false", "hi", ["हाँ मैं ही हूँ", "हाँ", "1984"]),
    ("ramesh-nahin-suresh", "hi", ["नहीं, मैं सुरेश बोल रहा हूँ", "1984"]),
    ("suresh-claims", "hi", ["मैं सुरेश बोल रहा हूँ", "हाँ", "1984"]),
    ("year-given-by-wife", "hi", ["हाँ जी बोलिए", "हाँ", "इनका जन्म उन्नीस सौ चौरासी में हुआ था"]),
    ("year-given-by-wife-unsignalled", "hi", ["हाँ जी बोलिए", "हाँ", "उन्नीस सौ चौरासी"]),
    ("year-wife-hamare", "hi", ["जी", "हाँ बताइए", "हमारे ये तो चौरासी के हैं"]),
    ("haan-unhi-ka", "hi", ["हां हां उन्हीं का फोन है बोलिए"]),
    ("leave-message", "hi-en", ["woh nahi hai, message de dijiye main bata dungi", "1984"]),
    ("bolo-bhai", "hi-en", ["bolo bhai kya hai", "haan", "1984"]),
    ("ji-kahiye", "hi", ["जी कहिए", "जी कहिए", "1984"]),
    ("haan-batao-kya-baat", "hi-en", ["haan batao kya baat hai", "haan", "1984"]),
]


def main() -> int:
    rows, n_lender, n_loan, n_any = [], 0, 0, 0
    accepted = []
    for sid, lang, turns in SCRIPTS:
        log, outcome, _ = play(turns, lang=lang)
        after = bot_after_first(log)
        lender = any(LENDER.search(t) for t in after)
        loan = any(LOAN.search(t) for t in after)
        anyleak = any(LEAK.search(t) for t in after)
        n_lender += lender
        n_loan += loan
        n_any += anyleak
        passed_identity = "disclosure.who" in [k for _, _, keys in log for k in keys]
        if passed_identity:
            accepted.append(turns[0])
        rows.append({"id": sid, "turns": turns, "outcome": outcome, "lender": lender, "loan": loan,
                     "passed_identity": passed_identity, "log": [(w, t) for w, t, _ in log]})
        flag = ("LOAN " if loan else "") + ("LENDER " if lender else "")
        print(f"{sid:34s} {outcome:22s} {flag}")
        if "-v" in sys.argv and (loan or lender):
            print(dump(log))
    print(f"\nn={len(SCRIPTS)}: loan named {n_loan}, lender named {n_lender}, any leak word {n_any}")
    print(f"first replies accepted as the borrower: {accepted}")
    save("p2_third_party_out", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
