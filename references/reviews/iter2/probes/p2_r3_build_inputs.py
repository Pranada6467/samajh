"""P2 round 3 verifier inputs (written blind, before reading any round 3 test or earlier input set).
Writes p2_r3_inputs.json. Record: tests/dialogue/fixtures/record_gold_loan.json (Ramesh, born 1984)."""
import json, re
from pathlib import Path

def lang(t):
    return "hi" if re.search(r"[ऀ-ॿ]", t) else "hi-en"

C = []
def add(group, stage, text, kind, follow=(), second=None, first=None):
    C.append(dict(group=group, stage=stage, text=text, kind=kind, follow=list(follow), second=second,
                  first=first, lang=lang(first or text)))

# ---- Group 1: genuine borrowers
G1_OPEN = ["हाँ जी बोलिए", "हां मै रमेश", "जी हाँ रमेश बोल रहा", "हाँ हाँ बोलो", "हा जी", "जी बोलिये कौन",
 "हाँ रमेश जी से ही बात हो रही है", "अरे हाँ भाई मैं ही हूँ", "हाँ जी, बताइए क्या काम है", "जी, रमेश नमूना",
 "हां बोल रहा हूं बोलो", "हाँजी", "हाँ, आप कौन?", "जी हाँ, कहिए", "हाँ जी मैं ही बात कर रहा हूँ, बोलिए जल्दी",
 "haan ji boliye", "haan main ramesh", "ha ji bol raha hu", "yes speaking", "haan haan bolo kaun",
 "ji haan Ramesh here", "haan bhai bolo", "haanji", "haan matlab main hi hoon", "yes ramesh speaking boliye",
 "arre haan bolo na", "ji boliye", "haan ji Ramesh hi bol raha hai", "yes yes", "haan ji kahiye kya kaam hai"]
for t in G1_OPEN: add("g1", "opening", t, "genuine", follow=["1984" if lang(t)=="hi-en" else "उन्नीस सौ चौरासी"])
G1_YEAR = ["उन्नीस सौ चौरासी", "1984", "चौरासी", "84", "उन्नीस सौ चौरसी", "अरे वो उन्नीस सौ चौरासी", "साल 1984 है",
 "जी, चौरासी में पैदा हुआ था", "1984 जी", "हम्म 1984", "मेरा जन्म 1984 में हुआ", "उन्निस सौ चौरासी जी", "चौरासी का हूँ मैं",
 "nineteen eighty four", "1984 hai", "unnees sau chaurasi", "84 wala", "mera birth year 1984", "ji 1984",
 "eighty four", "haan 1984, jaldi bolo", "uhh 1984", "saal 1984", "nineteen chaurasi", "main 1984 ka hoon"]
for t in G1_YEAR: add("g1", "year", t, "genuine")
G1_REASK = ["हाँ", "हाँ जी", "जी", "yes", "haan ji", "हाँ वही", "जी मैं ही", "haan wahi", "हाँ बोलो", "ji haan"]
for t in G1_REASK: add("g1", "reask", t, "genuine", follow=["1984"])

# ---- Group 2: third parties and false claimants
G2_OPEN = ["नहीं, मैं उनकी पत्नी बोल रही हूँ", "वो घर पे नहीं हैं", "मैं उनका बेटा हूँ, पापा सो रहे हैं", "रॉन्ग नंबर है",
 "यहाँ कोई रमेश नहीं रहता", "मैं उनका भाई, बताइए क्या बात है", "वो बाहर गए हैं, मुझे बता दो", "नहीं जी, ये सुरेश का फोन है",
 "पापा का फ़ोन है, मैं बोल रहा", "उनकी बहू बोल रही हूँ, क्या काम था", "रमेश जी अभी ऑफिस में है मैं उनका ड्राइवर",
 "nahi main unki wife", "wo ghar pe nahi hai", "main unka beta, bataiye", "wrong number", "koi ramesh nahi hai yahan",
 "main unka dost hoon, phone mere paas hai", "papa bahar gaye hain", "unka phone mere paas hai, kya kaam hai",
 "no, this is his son", "nahi ji main suresh"]
for t in G2_OPEN: add("g2", "opening", t, "third_party", follow=["हाँ" if lang(t)=="hi" else "haan", "हाँ बताओ" if lang(t)=="hi" else "haan batao"])
G2_YEAR_TP = ["साल? वो उनसे पूछना पड़ेगा, मैं उनकी पत्नी हूँ", "मुझे नहीं पता, मैं उनका बेटा हूँ", "ये तो पापा ही बताएंगे",
 "pata nahi, main unka bhai hoon", "unse puchna padega, main beta hoon"]
for t in G2_YEAR_TP: add("g2", "year", t, "third_party", follow=["1984"])
G2_FC = [("हाँ मैं ही रमेश हूँ", "1990", "wrong_year"), ("हाँ मैं ही रमेश हूँ", "पता नहीं, शायद अस्सी", "guess"),
 ("हाँ मैं ही रमेश हूँ", "1984", "right_year"), ("haan main hi ramesh", "1979", "wrong_year"),
 ("haan main hi ramesh", "shayad 1985", "guess"), ("haan main hi ramesh", "1984", "right_year"),
 ("जी मैं ही बोल रहा हूँ", "उन्नीस सौ अस्सी", "wrong_year"), ("जी मैं ही बोल रहा हूँ", "लगभग चौरासी पचासी", "guess"),
 ("ji main hi bol raha", "eighty four", "right_year"), ("हाँ, मैं रमेश", "सत्तासी", "wrong_year"),
 ("हाँ, मैं रमेश", "याद नहीं, 82 होगा", "guess"), ("haan main hoon", "1983", "wrong_year")]
for o, y, k in G2_FC: add("g2", "year", y, "false_" + k, first=o, follow=["1984", "हाँ"])
G2_MID = ["मैं उनका बेटा बोल रहा हूँ, पापा बाहर चले गए", "रुको, मैं उनकी वाइफ हूँ, उन्होंने फोन दे दिया", "हेलो? मैं उनका भाई, क्या पूछ रहे थे",
 "पापा ने फ़ोन पकड़ा दिया, मुझे बताओ", "ये मेरे पति का लोन है, मुझसे बात करो", "hello main unka beta, papa chale gaye",
 "unki wife bol rahi hoon ab, bataiye", "main unka dost, unhone phone diya", "haan ab main bol raha hoon, unka bhai",
 "sir wo chale gaye, main unka driver"]
for t in G2_MID:
    for st in ("recall", "kind"):
        add("g2", st, t, "takeover", follow=["हाँ" if lang(t)=="hi" else "haan", "पता नहीं" if lang(t)=="hi" else "pata nahi"])

# ---- Group 3: refusals, do-not-call, call-back, human
R = {"refuse": ["मुझे बात नहीं करनी", "नहीं करनी कोई बात, रखो", "bas karo, mujhe interest nahi", "नहीं चाहिए, फोन रखिए"],
     "dnc": ["मेरा नंबर लिस्ट से हटा दो", "दोबारा फ़ोन मत करना", "mera number hata do, call mat karna"],
     "callback": ["अभी टाइम नहीं है बाद में करना", "kal call karna abhi meeting mein hoon"],
     "human": ["किसी इंसान से बात कराओ", "kisi real aadmi se baat karao"]}
for st in ("opening", "year", "go_ahead", "recall", "kind"):
    for k, ts in R.items():
        for t in ts: add("g3", st, t, k)
FIG = {"refuse": ["मुझे बात नहीं करनी", "bas, nahi karni baat"], "dnc": ["मेरा नंबर हटा दो", "call mat karna dobara"],
       "callback": ["बाद में फोन करना", "baad mein call karo"], "human": ["किसी इंसान से बात कराओ", "agent se baat karao"],
       "takeover": ["मैं उनका बेटा बोल रहा हूँ", "main unki wife hoon"]}
for k, ts in FIG.items():
    for t in ts:
        add("g3", "premium", "बावन सौ", k + "_second", second=t)
        add("g3", "premium", t, k + "_first", second="बावन सौ")
for k in ("refuse", "dnc", "human"):
    for t in R[k][:2]: add("g3", "premium", t, k)

# ---- Group 4: cooperative with refusal words; "now" at the call-back question
G4 = ["बंद मत करो, बोलो", "नहीं नहीं, पूछिए", "मना नहीं कर रहा, पूछो", "रुकना नहीं है, आगे बोलो", "नहीं, कोई दिक्कत नहीं, बोलिए",
 "बाद में क्यों, अभी पूछ लो", "फोन मत काटो, सुन रहा हूँ", "मुझे कोई परेशानी नहीं, चलो", "नहीं भाई बिज़ी नहीं हूँ, बोलो",
 "kaato mat, bolo", "nahi nahi, poochiye", "mana nahi hai, bolo", "busy nahi hoon, go ahead", "no problem, pucho",
 "band mat karo, haan bolo", "nahi yaar time hai, bolo", "रोको मत, बताओ", "no no, continue", "baad mein nahi, abhi bolo",
 "मैं मना नहीं कर रहा"]
for t in G4: add("g4", "go_ahead", t, "cooperative")
G4_MID = ["नहीं, मना नहीं किया था, बीमा लिया था", "बंद मत कीजिए, हाँ एक बीमा था", "nahi nahi, ek insurance liya tha",
 "रुकिए मत, हाँ कुछ लिया था", "naa, kuch problem nahi, ek policy li thi"]
for t in G4_MID: add("g4", "recall", t, "cooperative")
G4_NOW = ["अभी कर लो", "अभी", "abhi", "abhi kar lo", "अभी बोलिए, फ्री हूँ", "नहीं नहीं अभी ही कर लो", "abhi theek hai, bolo",
 "अब फ्री हूँ, अभी पूछो", "abhi hi pooch lo", "अभी चलेगा", "now is fine", "abhi karte hain", "अभी कर लीजिए जी", "haan abhi"]
for t in G4_NOW: add("g4", "callback_q", t, "now")
G4_LATER = ["शाम को छह बजे", "kal subah", "रविवार को", "do ghante baad"]
for t in G4_LATER: add("g4", "callback_q", t, "later")

# ---- Group 5: open recall: confused (something) vs truly nothing
G5_CONF = ["पता नहीं, कुछ पैसे कटे थे", "याद नहीं, पचास हज़ार कुछ काट लिए थे", "नहीं पता क्या था, बावन हज़ार कटा",
 "कुछ नहीं लिया पर लोन में से पैसे कम आए", "मालूम नहीं, उन्होंने बोला ये ज़रूरी है, साइन करवाया", "कुछ याद नहीं, एक फॉर्म भरवाया था",
 "नहीं, बस उन्होंने कुछ करवाया था, नाम नहीं पता", "पता नहीं जी, कुछ चार्ज लगाया था", "हमने तो कुछ नहीं लिया, बस 52000 कट गए",
 "नहीं याद, कोई कागज़ पे दस्तखत लिए", "कुछ नहीं, लेकिन पूरे पैसे नहीं मिले, कुछ कटे", "ठीक से नहीं पता, कुछ लेना ज़रूरी बोला था",
 "पता नहीं क्या था पर हर साल पैसे देने हैं बोले", "कुछ नहीं लिया, हाँ एक चीज़ के पैसे कटे", "मुझे नहीं पता, मैनेजर ने कुछ जोड़ दिया",
 "nahi pata, kuch paise kate the", "yaad nahi, 52 hazaar cut hua", "kuch nahi liya, bas loan se paisa kam aaya",
 "pata nahi, unhone bola zaroori hai", "kuch form bharwaya tha, naam nahi pata", "nahi yaad, kuch charge lagaya",
 "kuch nahi, but paise kat gaye the", "pata nahi kya tha, sign karwaya", "maloom nahi, manager ne kuch add kiya",
 "nothing, but they deducted some money"]
for t in G5_CONF: add("g5", "recall", t, "confused")
G5_NONE = ["नहीं, कुछ नहीं लिया", "बस लोन लिया, और कुछ नहीं", "नहीं जी, सिर्फ़ गोल्ड लोन", "कुछ भी नहीं", "नहीं, और कुछ नहीं लिया था",
 "ना, बस लोन", "नहीं नहीं, कुछ और नहीं", "सिर्फ लोन लिया था जी", "नहीं, उसके अलावा कुछ नहीं",
 "nahi kuch nahi liya", "bas loan liya tha", "sirf gold loan", "nothing else", "nahi ji kuch aur nahi", "kuch bhi nahi",
 "na, sirf loan"]
for t in G5_NONE: add("g5", "recall", t, "nothing")

# ---- Group 6: read-back (bot reads back 5,200)
G6 = {"same": ["हाँ बावन सौ", "5200", "बावन सौ", "हाँ, पाँच हज़ार दो सौ", "haan baavan sau", "5200 hi", "paanch hazaar do sau",
               "जी 5200 रुपये", "हाँ हाँ बावन सौ ही", "yes 5200"],
      "different": ["नहीं, बावन हज़ार", "52000", "नहीं जी पचास हज़ार", "nahi, baavan hazaar", "52 hazaar", "नहीं, साठ हज़ार",
                    "nahi 6000 the", "छह हज़ार", "बावन हज़ार था", "nahi, 5 hazaar"],
      "yes": ["हाँ", "हाँ जी सही है", "जी सही", "haan", "haan sahi hai", "yes correct", "बिल्कुल सही", "हाँ यही", "sahi", "ji"],
      "no": ["नहीं", "नहीं, गलत है", "ना", "nahi", "galat hai", "no", "नहीं ऐसा नहीं", "nahi sahi nahi", "गलत", "nope"]}
for k, ts in G6.items():
    for t in ts: add("g6", "read_back", t, k)

for i, c in enumerate(C): c["id"] = f"r3-{i:03d}"
out = Path(__file__).with_name("p2_r3_inputs.json")
out.write_text(json.dumps(C, ensure_ascii=False, indent=0), encoding="utf-8")
from collections import Counter
print(len(C), Counter(c["group"] for c in C))
