"""Case scaffolds for banks A, B and C: who the speaker is and what they do. The replies are written by outside models
(gen/write.py); gold is set by the checker from the scaffold and then reviewed against the written replies."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "gen" / "scaffolds"
LENDER = "Udaharan Bank"
rng = random.Random(4404)

# (record first name in Latin, Devanagari spoken form, a variant spelling the person might use, region tag)
NAMES = [
    ("Ramesh", "रमेश", "Rames", "north"), ("Sunita", "सुनीता", "Sunitha", "north"), ("Rajesh", "राजेश", "Rajesh", "north"),
    ("Pooja", "पूजा", "Puja", "north"), ("Anil", "अनिल", "Aneel", "north"), ("Neha", "नेहा", "Neha", "north"),
    ("Vikram", "विक्रम", "Vikrum", "north"), ("Manoj", "मनोज", "Manoj", "north"), ("Rekha", "रेखा", "Rekha", "north"),
    ("Deepak", "दीपक", "Dipak", "north"), ("Mahender", "महेंद्र", "Mahendra", "north"), ("Pinky", "पिंकी", "Pinki", "north"),
    ("Shiva", "शिवा", "Shiv", "north"), ("Gurpreet", "गुरप्रीत", "Gurprit", "sikh"), ("Harjeet", "हरजीत", "Harjit", "sikh"),
    ("Surinder", "सुरिंदर", "Surender", "sikh"), ("Manpreet", "मनप्रीत", "Manprit", "sikh"),
    ("Jaswinder", "जसविंदर", "Jasvinder", "sikh"), ("Imran", "इमरान", "Imraan", "muslim"),
    ("Farhana", "फ़रहाना", "Farhaana", "muslim"), ("Mohammed", "मोहम्मद", "Mohd", "muslim"),
    ("Shabnam", "शबनम", "Shabnum", "muslim"), ("Zubair", "ज़ुबैर", "Jubair", "muslim"), ("Ayesha", "आयशा", "Aisha", "muslim"),
    ("Salim", "सलीम", "Saleem", "muslim"), ("Joseph", "जोसेफ़", "Josef", "christian"), ("Mary", "मैरी", "Meri", "christian"),
    ("Thomas", "थॉमस", "Tomas", "christian"), ("Lizy", "लिज़ी", "Lizzie", "christian"),
    ("Anthony", "एंथनी", "Antony", "christian"), ("Philomena", "फिलोमिना", "Filomena", "christian"),
    ("Kavitha", "कविता", "Kavita", "south"), ("Geetha", "गीता", "Gita", "south"), ("Sujatha", "सुजाता", "Sujata", "south"),
    ("Lalitha", "ललिता", "Lalita", "south"), ("Preethi", "प्रीति", "Priti", "south"), ("Radhika", "राधिका", "Radhica", "south"),
    ("Sudhakar", "सुधाकर", "Sudakar", "south"), ("Venkatesh", "वेंकटेश", "Venkatesh", "south"),
    ("Murugan", "मुरुगन", "Murugun", "south"), ("Senthil", "सेंथिल", "Sentil", "south"), ("Lakshmi", "लक्ष्मी", "Laxmi", "south"),
    ("Srinivas", "श्रीनिवास", "Shrinivas", "south"), ("Padmavathi", "पद्मावती", "Padmavati", "south"),
    ("Nandhini", "नंदिनी", "Nandini", "south"), ("Aravindh", "अरविंद", "Arvind", "south"),
    ("Prabhakar", "प्रभाकर", "Prabhakar", "south"), ("Shwetha", "श्वेता", "Shweta", "south"),
    ("Ramprasad", "रामप्रसाद", "Ram Prasad", "compound"), ("Jaiprakash", "जयप्रकाश", "Jai Prakash", "compound"),
    ("Shivkumar", "शिवकुमार", "Shiv Kumar", "compound"), ("Rajkumari", "राजकुमारी", "Raj Kumari", "compound"),
    ("Vijayalakshmi", "विजयलक्ष्मी", "Vijaya Lakshmi", "compound"),
    ("Satyanarayana", "सत्यनारायण", "Satyanarayan", "compound"), ("Lalremruati", "ललरेमरुआती", "Lalremruati", "northeast"),
    ("Tomba", "तोम्बा", "Tomba", "northeast"), ("Dorjee", "दोरजी", "Dorji", "northeast"),
    ("Bijoy", "बिजॉय", "Bijay", "northeast"), ("Ibomcha", "इबोमचा", "Ibomcha", "northeast"),
    ("Thoibi", "थोइबी", "Thoibi", "northeast"), ("Rinchen", "रिनचेन", "Rinchin", "northeast"),
    ("Subhash", "सुभाष", "Subash", "east"), ("Debashish", "देबाशीष", "Debasis", "east"), ("Arpita", "अर्पिता", "Arpitha", "east"),
    ("Sourav", "सौरव", "Saurabh", "east"), ("Tanmay", "तन्मय", "Tanmoy", "east"), ("Snehal", "स्नेहल", "Snehal", "west"),
    ("Dnyaneshwar", "ज्ञानेश्वर", "Gyaneshwar", "west"), ("Pratiksha", "प्रतीक्षा", "Pratiksha", "west"),
    ("Bhavesh", "भावेश", "Bhavesh", "west"), ("Hetal", "हेतल", "Hetal", "west"), ("Jignesh", "जिग्नेश", "Jignesh", "west"),
]
OTHER_NAMES = ["Suresh", "Kamla", "Rohit", "Anjali", "Nasreen", "Baldev", "Prakash", "Meena", "Arjun", "Fatima", "Kishore",
               "Lata", "Naveen", "Savitri", "Yusuf", "Gopal"]

HI = {
    "name": "नमस्ते, क्या आप {n} जी हैं?",
    "direct": "यह {n} जी के लिए एक ऑटोमेटेड कस्टमर केयर कॉल है। क्या आप ख़ुद {n} जी हैं?",
    "go_ahead": "मैं Udaharan Bank कस्टमर केयर से कंप्यूटर से चलने वाली आवाज़ हूँ, इंसान नहीं। यह सेल्स नहीं, फ़ीडबैक कॉल है। "
    "बातचीत रिकॉर्ड हो रही है; जानकारी Udaharan Bank के लिखित नोटिस में है। ... क्या दो-तीन मिनट बात करें?",
    "when": "ठीक है। आपको कब कॉल करें?",
    "after": "(the bot answers or asks again)",
}
HIEN = {
    "name": "Hello, क्या आप {n} जी हैं?",
    "direct": "यह {n} जी के लिए एक automated customer care call है। क्या आप ख़ुद {n} जी हैं?",
    "go_ahead": "मैं Udaharan Bank customer care से computer से चलने वाली आवाज़ हूँ, इंसान नहीं। यह sales नहीं, feedback call है। "
    "Call record हो रही है; details Udaharan Bank के written notice में हैं। ... क्या दो-तीन minute बात करें?",
    "when": "ठीक है। आपको कब call करें?",
    "after": "(the bot answers or asks again)",
}
SCRIPTS = ["Devanagari Hindi", "romanised Hinglish (Latin letters)", "mixed: mostly Devanagari with English words in Latin"]

BORROWER = {
    "b_greet": "The speaker IS {n}. Reply 1: greets or chatters first (e.g. namaste, boliye) and confirms being {n}, maybe not crisply. Reply 2 (to 'are you {n} yourself?'): clearly says they are {n} themselves. Reply 3: agrees to talk.",
    "b_trailq": "The speaker IS {n}. Reply 1: confirms but adds a trailing question ('kya baat hai?', 'kis baare mein?', 'kaun bol raha hai?'). Reply 2: clearly confirms being {n} themselves, may ask again what it is about. Reply 3: agrees to talk.",
    "b_hedge": "The speaker IS {n}. Reply 1: a hesitant or sleepy yes with fillers ('haan... haan ji', 'ji bolo'), maybe no name. Reply 2: clearly says 'yes, I am {n}' in their own words. Reply 3: agrees to talk.",
    "b_who_first": "The speaker IS {n}. Reply 1: does NOT confirm yet; asks who is calling or where from. Reply 2 (the bot asks again whether they are {n} themselves): says yes, they are {n}. Reply 3: agrees to talk.",
    "b_spelling": "The speaker IS {n}. When they say their own name they say it as '{v}' / '{d}' (their own way of saying or spelling it). Reply 1: confirms using that form. Reply 2: confirms again they are {v} themselves. Reply 3: agrees to talk.",
    "b_speaking": "The speaker IS {n}. Reply 1: answers like 'speaking' / 'haan bol raha hoon' / 'ji, main hi bol rahi hoon'. Reply 2: confirms being {n} themselves. Reply 3: agrees to talk.",
    "b_busyok": "The speaker IS {n}. Reply 1: confirms being {n} with background chatter ('haan haan, main hi hoon, ek second... haan boliye'). Reply 2: confirms again. Reply 3: agrees to talk, says to go ahead.",
}
THIRD = {
    "tp_spouse": "The speaker is the wife or husband of {n}, NOT {n}. Reply 1: says this is {n}'s phone and they are the spouse. Reply 2: says {n} is not here / is at work; they are the spouse. Reply 3: says they can take a message.",
    "tp_child": "The speaker is the son or daughter of {n}, NOT {n}. Reply 1: says 'papa/mummy' ({n}) is not here or busy, I am the son/daughter. Reply 2: repeats they are the child. Reply 3: asks what to tell {n}.",
    "tp_parent": "The speaker is the mother or father of {n}, NOT {n}. Reply 1: says {n} is their son/daughter and is out. Reply 2: repeats. Reply 3: says call later.",
    "tp_colleague": "The speaker is a colleague, friend or shop worker who picked up {n}'s phone, NOT {n}. Reply 1: says {n} has gone out / left the phone here. Reply 2: says they are not {n}, they are a colleague/friend. Reply 3: says they'll pass a message.",
    "tp_diffname": "The speaker is a different person called {o}, NOT {n}. Reply 1: says no, I am {o}. Reply 2: repeats they are {o}. Reply 3: says {n} is not available.",
    "tp_offer": "The speaker is a relative of {n} (brother, sister, wife), NOT {n}, and offers to handle it. Reply 1: says {n} is not here, but you can talk to me, I handle their bank work. Reply 2: says 'main unka bhai/unki behen/wife hoon, mujhse hi baat kar lo'. Reply 3: says 'haan bolo, kya kaam hai'.",
    "tp_wrongnum": "The speaker does not know {n}. Reply 1: says wrong number / there is no {n} here. Reply 2: repeats no {n} here. Reply 3: says do not call this number for {n}.",
    "tp_yes_twice": "The speaker is a relative of {n} and is NOT {n}, but never says so: Reply 1 is just a bare 'haan' or 'haan ji' or 'ji'. Reply 2 is again only a bare 'haan'/'ji haan'. Reply 3: 'haan bolo'. Do not state who they are.",
}
REFUSAL = {
    "r_not_now": "a refusal to talk now: 'abhi baat nahi karni' / 'abhi nahi'",
    "r_not_interested": "not interested: 'mujhe interest nahi hai', 'nahi chahiye kuch'",
    "r_stop": "an angry stop: 'band karo ye', 'phone rakho', 'pareshan mat karo'",
    "r_remove": "asks to remove the number / never call again: 'mera number hata do', 'dobara call mat karna'",
    "r_human": "asks for a real person: 'kisi insaan se baat karao', 'machine se baat nahi karni, kisi aadmi ko do'",
    "r_mixed": "first confirms being {n} and then refuses in the SAME reply: 'haan main {n}, par abhi baat nahi karni'",
}
CALLBACK = {
    "c_busy": "busy right now: 'abhi busy hoon, baad mein karo'",
    "c_driving": "is driving / on a bike: 'gaadi chala raha hoon, baad mein call karna'",
    "c_evening": "asks to be called in the evening: 'shaam ko call karna'",
    "c_meeting": "is in a meeting / at work: 'meeting mein hoon, thodi der baad'",
    "c_tomorrow": "asks to call tomorrow: 'kal call kar lena'",
}
LANG = {"ta": "Tamil", "kn": "Kannada", "en": "English", "te": "Telugu", "mr": "Marathi", "bn": "Bengali"}
POSITIONS = ["name", "direct", "go_ahead"]


def qtexts(lang: str, name: str, positions: list[str]) -> list[str]:
    table = HI if lang == "hi" else HIEN
    return [table[p].format(n=name) for p in positions]


def bank_a() -> list[dict]:
    cases: list[dict] = []
    names = NAMES[:]
    rng.shuffle(names)
    k = 0

    def pick():
        nonlocal k
        row = names[k % len(names)]
        k += 1
        return row

    def add(kind, sub, positions, scenario, row, event_turn=None, extra=None, gold=None, residual=False, lang=None):
        n, d, v, region = row
        language = lang or rng.choice(["hi", "hi-en"])
        cases.append({
            "id": f"A-{len(cases) + 1:03d}", "kind": kind, "subkind": sub, "first_name": n, "spoken_dev": d,
            "spoken_variant": v, "region": region, "language": language, "positions": positions,
            "bot_questions": qtexts(language, n, positions), "scenario": scenario, "script": rng.choice(SCRIPTS),
            "event_turn": event_turn, "gold": gold, "accepted_residual": residual, **(extra or {}),
        })

    subs = list(BORROWER)
    for i in range(91):
        sub = subs[i % len(subs)]
        row = pick()
        add("borrower", sub, ["name", "direct", "go_ahead"],
            BORROWER[sub].format(n=row[0], d=row[1], v=row[2]), row, gold="pass")
    subs = list(THIRD)
    for i in range(56):
        sub = subs[i % len(subs)]
        row = pick()
        other = rng.choice(OTHER_NAMES)
        add("third_party", sub, ["name", "direct", "go_ahead"], THIRD[sub].format(n=row[0], o=other), row,
            gold="not_pass", residual=(sub == "tp_yes_twice"), extra={"other_name": other})
    subs = list(REFUSAL)
    for i in range(30):
        sub = subs[i % len(subs)]
        row = pick()
        pos = ["name", "direct", "go_ahead"][i % 3]
        if sub == "r_mixed":
            pos = "name"
        positions, ev, pre = _event_positions(pos)
        what = REFUSAL[sub].format(n=row[0])
        scen = (f"The speaker IS {row[0]} (the borrower). {pre}Reply {ev + 1} (to the bot's '{pos}' question) is {what}. "
                f"Reply {ev + 2}: if the bot keeps talking, repeats the refusal more firmly.")
        add("refusal", sub, positions + ["after"], scen, row, event_turn=ev,
            gold={"r_remove": "do_not_call", "r_human": "human_requested"}.get(sub, "declined"),
            extra={"event_position": pos})
    subs = list(CALLBACK)
    for i in range(22):
        sub = subs[i % len(subs)]
        row = pick()
        pos = ["name", "direct", "go_ahead"][i % 3]
        positions, ev, pre = _event_positions(pos)
        scen = (f"The speaker IS {row[0]} (the borrower). {pre}Reply {ev + 1} (to the bot's '{pos}' question) says they "
                f"cannot talk now: {CALLBACK[sub]}. Reply {ev + 2} answers the bot's 'when shall we call you?' with a "
                f"time in their own words.")
        add("call_back", sub, positions + ["when"], scen, row, event_turn=ev, gold="call_back_later",
            extra={"event_position": pos})
    langs = list(LANG)
    for i in range(30):
        code = langs[i % len(langs)]
        row = pick()
        pos = ["name", "direct", "go_ahead"][(i // len(langs)) % 3]
        positions, ev, pre = _event_positions(pos)
        inside_yes = i % 2 == 0
        how = (f"says yes AND asks for {LANG[code]} in the same reply ('haan, par {LANG[code]} mein baat karo')"
               if inside_yes else f"asks to talk in {LANG[code]} because they are not comfortable in Hindi")
        scen = (f"The speaker IS {row[0]} (the borrower). {pre}Reply {ev + 1} (to the bot's '{pos}' question) {how}"
                + (f"; at the name question they also say they are {row[0]}" if pos == "name" else "") + ".")
        add("language", f"lang_{code}", positions, scen, row, event_turn=ev, gold=code,
            extra={"event_position": pos, "inside_yes": inside_yes,
                   "requested": LANG[code].lower(), "has_file": code in ("ta", "kn", "en")})
    return cases


def _event_positions(pos: str) -> tuple[list[str], int, str]:
    if pos == "name":
        return ["name"], 0, ""
    if pos == "direct":
        return ["name", "direct"], 1, "Reply 1: a plain 'haan ji' with no name. "
    return ["name", "go_ahead"], 1, "Reply 1: clearly says 'yes, I am <name>' using the name. "


# ---- bank B: half answers at the consent and kind questions
CONSENT_Q = {"hi": "लोन लेते समय आपने किन-किन चीज़ों के लिए हाँ कही थी? और वो हाँ आपने किस तरह दी थी?",
             "hi-en": "Loan लेते time आपने किन-किन चीज़ों के लिए हाँ बोला था? और वो हाँ आपने किस तरह दी थी?"}
KIND_Q = {"hi": "जो आपने बताया, उसे थोड़ा समझाइए: वो क्या है और किस काम आता है?",
          "hi-en": "जो आपने बताया, उसे थोड़ा explain कीजिए: वो क्या है और किस काम आता है?"}
CONSENT_SUB = {
    "how_only": ("only HOW they agreed (signed a form, gave an OTP, said yes on a call, thumbprint, clicked in an app), "
                 "NOT what they agreed to", {"what": False, "how": True}),
    "what_only": ("only WHAT they agreed to (the loan, some insurance/cover, a card, an add-on), NOT how they gave the yes",
                  {"what": True, "how": False}),
    "both": ("both what they agreed to and how they gave the yes", {"what": True, "how": True}),
    "neither": ("neither: vague chatter like 'sab theek tha, unhone jo bola maine kar diya' that names no thing and no way",
                {"what": False, "how": False}),
    "refusal": ("a refusal to answer this question ('ye sab main nahi bataunga', 'ye personal hai')", {"what": False, "how": False}),
    "dont_know": ("'don't remember / don't know' ('yaad nahi', 'pata nahi kya kya sign karaya')", {"what": False, "how": False}),
}
KIND_SUB = {
    "figure_only": ("only a rupee figure, as words ('pachaas hazaar ka tha'), nothing about what it is or does",
                    {"what": False, "does": False, "figure": True}),
    "does_only": ("only what it does ('agar mujhe kuch ho gaya to loan bhar dega', 'emergency mein kaam aayega'), "
                  "without naming what it is", {"what": False, "does": True, "figure": False}),
    "kind_only": ("only a name for what it is ('insurance hai', 'bima hai', 'ek policy hai'), nothing about what it does",
                  {"what": True, "does": False, "figure": False}),
    "both": ("what it is AND what it does ('bima hai, kuch ho jaye to loan chuk jayega')", {"what": True, "does": True, "figure": False}),
    "dont_know": ("'don't know' ('pata nahi kya tha', 'unhone bataya nahi')", {"what": False, "does": False, "figure": False}),
}


def bank_b() -> list[dict]:
    cases = []
    for i in range(42):
        sub = list(CONSENT_SUB)[i % len(CONSENT_SUB)]
        lang = ["hi", "hi-en"][i % 2]
        desc, halves = CONSENT_SUB[sub]
        cases.append({"id": f"B-{len(cases) + 1:03d}", "slot": "consent", "subkind": sub, "language": lang,
                      "question": CONSENT_Q[lang], "scenario": desc, "halves": halves, "script": SCRIPTS[i % 3]})
    for i in range(30):
        sub = list(KIND_SUB)[i % len(KIND_SUB)]
        lang = ["hi", "hi-en"][i % 2]
        desc, halves = KIND_SUB[sub]
        cases.append({"id": f"B-{len(cases) + 1:03d}", "slot": "kind", "subkind": sub, "language": lang,
                      "question": KIND_Q[lang], "scenario": desc, "halves": halves, "script": SCRIPTS[i % 3]})
    return cases


# ---- bank C: mid-call
TB_Q = {
    "premium": ("उसके लिए आपने कितने पैसे दिए?", "उसके लिए आपने कितना pay किया?"),
    "payment_source": ("वो पैसे कहाँ से और कैसे दिए गए?", "वो payment कहाँ से और कैसे हुई?"),
    "required_for_loan": ("आपको क्या बताया गया था: लोन के लिए यह लेना ज़रूरी है, या आपकी मर्ज़ी है?",
                          "आपको क्या बताया गया था: loan के लिए यह लेना ज़रूरी है, या आपकी choice है?"),
    "cover": ("उससे आपको क्या मिलता है? कोई रक़म जुड़ी हो, तो वो भी बताइए।", "उससे आपको क्या मिलता है? कोई amount जुड़ा हो, तो वो भी बताइए।"),
    "term": ("वो कितने समय के लिए है?", "वो कितने time के लिए है?"),
    "cancel_window": ("उसे बंद या कैंसल कराने के बारे में आपको क्या बताया गया था?", "उसे बंद या cancel कराने के बारे में आपको क्या बताया गया था?"),
    "payment_frequency": ("ये पैसे एक ही बार देने थे, या आगे भी देने होंगे?", "यह payment एक ही बार की थी, या आगे भी करनी होगी?"),
    "open_recall": ("लोन के साथ आपने कुछ और भी लिया था क्या? अगर हाँ, तो क्या, और कितने का?",
                    "Loan के साथ आपने कुछ और भी लिया था क्या? अगर हाँ, तो क्या, और कितने का?"),
}
DEFER = {
    "defer_record": "defers to the record: 'aap records check kar lo', 'aapke system mein sab hoga'",
    "defer_bank": "defers to the bank: 'bank waalon ko better pata hoga', 'branch mein poochh lo'",
    "defer_written": "says it is written down with them: 'aapke paas likha hoga', 'kaagaz mein sab likha hai, dekh lo'",
}
REFUSE_MID = "a real refusal to go on with the call: 'bas, ab aur baat nahi karni, phone rakhiye', 'mujhe aage koi sawaal nahi chahiye'"
MIX_MID = "a mix in one reply: defers to the bank's records AND says they do not want to continue the call"


def bank_c() -> list[dict]:
    cases = []
    tb = ["premium", "payment_source", "required_for_loan", "cover", "term", "cancel_window"]

    def add(group, sub, slot, lang, scen, gold):
        cases.append({"id": f"C-{len(cases) + 1:03d}", "group": group, "subkind": sub, "slot": slot, "language": lang,
                      "question": TB_Q[slot][0 if lang == "hi" else 1], "scenario": scen, "gold": gold,
                      "script": SCRIPTS[len(cases) % 3]})

    for i in range(18):
        sub = list(DEFER)[i % 3]
        add("deferral", sub, tb[i % len(tb)], ["hi", "hi-en"][i % 2], DEFER[sub], "deferral")
    for i in range(7):
        add("deferral", "refusal", tb[(i + 2) % len(tb)], ["hi", "hi-en"][i % 2], REFUSE_MID, "refusal")
    for i in range(6):
        add("deferral", "mix", tb[(i + 4) % len(tb)], ["hi", "hi-en"][i % 2], MIX_MID, "refusal")
    neg = {
        "payment_frequency": "answers that it was paid once and never again, using a NEGATED again/later word: 'ek hi baar diya, dobara kabhi nahi dena pada', 'uske baad phir kabhi nahi', 'aage nahi dena'",
        "payment_source": "says where it was paid from, and adds a negated again word: 'loan mein se kat gaya, phir kisi ne dobara nahi maanga', 'ek baar cash diya, baad mein nahi'",
        "cover": "says what it gives and adds a negated again/later word: 'kuch ho jaye to loan chuk jayega, baad mein kuch dena nahi padega', 'phir dobara koi paisa nahi'",
    }
    for i in range(18):
        slot = list(neg)[i % 3]
        add("negated_again", "neg_again", slot, ["hi", "hi-en"][i % 2], neg[slot], "answer")
    for i in range(14):
        add("recall", "forgot_amount", "open_recall", ["hi", "hi-en"][i % 2],
            "says they DID take something with the loan and names it (insurance, bima, a policy, a card, a scheme) but "
            "forgot how much: 'haan insurance liya tha, kitne ka yaad nahi'", "took_something")
    for i in range(8):
        add("recall", "took_nothing", "open_recall", ["hi", "hi-en"][i % 2],
            "says they took nothing else with the loan, only the loan: 'nahi, sirf loan liya tha, aur kuch nahi'", "took_nothing")
    return cases


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("A", bank_a), ("B", bank_b), ("C", bank_c)):
        rows = fn()
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(name, len(rows), file=sys.stderr)
