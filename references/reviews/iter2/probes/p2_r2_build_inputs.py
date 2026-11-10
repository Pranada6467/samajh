"""Author the P2 round-2 verifier's inputs (written before reading _lexicon.py or tests/dialogue)."""
import json, pathlib, sys

H, E = "hi", "hi-en"
cases = []


def add(group, cat, point, lang, turns, record="ramesh", note=""):
    n = sum(1 for c in cases if c["group"] == group) + 1
    PFX = {"third_party": "tp", "refusal": "rf", "genuine": "gi", "genuine_year": "gy", "nonrefusal": "nr"}
    cases.append(dict(id=f"{PFX[group]}-{n:03d}", group=group, category=cat, point=point, lang=lang,
                      record=record, turns=turns if isinstance(turns, list) else [turns], note=note))


# third-party follow-ups appended to every third-party opening
FH = ["कौन बोल रहा है? किस बारे में है?", "मुझे बता दीजिए, मैं उनको बता दूँगी", "किस बैंक से हो आप?"]
FE = ["kaun bol raha hai? kis baare mein?", "aap mujhe bata do na, main bol dunga unko", "kahan se call hai ye, bank se?"]
F = {H: FH, E: FE}

# ---------------- group 1: third parties -----------------
tp_open = [
    ("spouse", H, "नहीं, मैं उनकी पत्नी बोल रही हूँ, वो दुकान गए हैं"),
    ("spouse", E, "nahi ji main unki wife hu, woh abhi naha rahe hai"),
    ("spouse", H, "हाँ जी बोलिए, मैं उनकी घरवाली हूँ"),
    ("spouse", E, "haan haan boliye, Ramesh ji ki missus bol rahi hoon"),
    ("spouse", H, "अरे वो तो सो रहे हैं, मैं वाइफ हूँ उनकी, क्या काम है"),
    ("spouse", E, "ramesh to bahar gaye hain, aap kaun"),
    ("spouse", H, "जी मैं मिसेज़ रमेश बोल रही"),
    ("spouse", E, "unke husband nahi matlab main unki biwi hoon bolo kya baat hai"),
    ("child", H, "पापा अभी घर पे नहीं हैं, मैं उनका बेटा बोल रहा हूँ"),
    ("child", E, "papa office gaye hai, main beta bol raha, kya kaam tha"),
    ("child", H, "हाँ बोलो, मैं बेटी हूँ उनकी, पापा का फोन मेरे पास है"),
    ("child", E, "hello uncle papa ka phone hai ye main unki daughter"),
    ("child", H, "जी वो मेरे पिताजी हैं, अभी बाथरूम में हैं"),
    ("child", E, "haan ji papa hi ka number hai, bolo main sun raha hu"),
    ("parent", H, "बेटा तो ड्यूटी पे गया है, मैं उसकी माँ बोल रही हूँ"),
    ("parent", E, "woh mera beta hai, abhi bahar hai, aap mujhse baat kar lo"),
    ("parent", H, "रमेश का बाप बोल रहा हूँ, क्या बात है बताओ"),
    ("parent", E, "haan ji Ramesh ki mummy hoon, bolo beta"),
    ("colleague", H, "जी ये ऑफिस का नंबर है, रमेश सर मीटिंग में हैं"),
    ("colleague", E, "sir abhi available nahi hai, main unka PA bol raha hoon"),
    ("colleague", H, "मैं उनके साथ काम करता हूँ, उन्होंने फोन मुझे दे दिया है, बोलिए"),
    ("colleague", E, "Ramesh bhai ka phone hai par main uska dost hu, woh gaadi chala raha hai"),
    ("colleague", H, "हाँ हाँ बोलिए, दुकान का नंबर है, सेठ जी बाहर गए"),
    ("wrong_number", H, "गलत नंबर है, यहाँ कोई रमेश नहीं रहता"),
    ("wrong_number", E, "wrong number hai bhai"),
    ("wrong_number", H, "नहीं, मेरा नाम सुरेश है"),
    ("wrong_number", E, "nahi main Rakesh bol raha hu, Ramesh nahi"),
    ("wrong_number", H, "कौन रमेश? यह नंबर तो मैंने अभी नया लिया है"),
    ("wrong_number", E, "ye number pehle kisi aur ka tha shayad, main toh Priya hoon"),
    ("relative", H, "मैं उनका भाई हूँ, सब बात मुझे बता दो, मैं ही देखता हूँ उनका काम"),
    ("relative", E, "main unka bhatija hoon, loan ka sab main hi dekhta hu, mujhe bataiye"),
    ("relative", H, "हम उनके रिश्तेदार हैं, बताइए क्या बात है"),
    ("relative", E, "jija ji ka phone hai, main saala bol raha hoon, haan bolo"),
    ("relative", H, "ये मेरे ससुर जी का नंबर है, वो कम सुनते हैं, मुझसे बात कीजिए"),
    ("relative", E, "mere chachaji hain woh unko hindi theek se nahi aati mujhe bol do"),
    ("handoff", H, "एक मिनट, मैं अपने बेटे को देती हूँ, वो सब देखता है"),
    ("handoff", E, "aap mere bete se baat karo, woh handle karta hai sab"),
    ("other", H, "वो घर पर नहीं हैं"),
    ("other", E, "he is not at home, call later"),
    ("other", H, "साहब अभी पूजा में बैठे हैं, बाद में करना"),
    ("other", E, "abhi woh so rahe hain, main unki nurse hoon"),
    ("other", H, "उनका देहांत हो गया पिछले महीने"),
]
for cat, lang, u in tp_open:
    add("third_party", cat, "opening", lang, [u] + F[lang])

tp_year = [
    ("spouse", H, "मेरा या उनका? उनका तो 1984 है"),
    ("spouse", E, "unka saal? ruko puchti hoon... 1984 bol rahe hain"),
    ("child", H, "मैं तो उनका बेटा हूँ, पापा का साल 1984 है"),
    ("child", E, "papa ka birth year 1984, main beta hu"),
    ("other", H, "जी मेरा नहीं, मैं तो उनकी तरफ़ से बोल रहा था"),
    ("relative", E, "actually main unka bhai hoon, unka saal mujhe nahi pata"),
    ("spouse", H, "वो तो अस्पताल में हैं, मैं उनकी पत्नी हूँ"),
    ("colleague", E, "sorry main Ramesh nahi hoon, main unke office se hoon"),
    ("spouse", H, "मेरी उम्र? मैं तो 1990 की हूँ, रमेश जी 1984 के"),
    ("other", E, "uncle ka 1984 hai na? haan wahi likh lo"),
]
for cat, lang, u in tp_year:
    add("third_party", cat, "birth_year", lang, [u] + F[lang])

tp_mid = [
    ("handoff", H, "mid_recall", "रुकिए, मेरी बीवी से बात कीजिए, वो सब जानती है"),
    ("child", E, "mid_recall", "ek minute, main beta hoon, papa ne phone de diya, kya puch rahe the aap?"),
    ("child", H, "mid_recall", "हेलो, मैं इनकी बेटी हूँ, पापा को सुनाई नहीं देता, मुझे बताइए क्या लिया था"),
    ("relative", E, "mid_recall", "hello? papa bahar chale gaye, main unka bhai hu, kya baat chal rahi thi"),
    ("spouse", H, "mid_recall", "मेरे पति को कुछ नहीं पता, मैं बताती हूँ, मैं उनकी पत्नी हूँ"),
    ("colleague", E, "mid_recall", "main unka CA hoon, unke saare loan main manage karta hoon, aap mujhe bolo"),
    ("child", H, "mid_kind", "बेटा बोल रहा हूँ, पापा की तबीयत ठीक नहीं, आगे क्या पूछना है"),
    ("other", E, "mid_kind", "aunty bol rahi hu padosi, ramesh ji ne phone pakda diya"),
    ("relative", H, "mid_kind", "हाँ जी, मैं उनका दामाद हूँ, आप मुझे बताओ कितने का था"),
    ("spouse", E, "mid_kind", "sorry woh kisi aur se baat kar rahe hain, main unki wife, aap continue karo"),
    ("parent", H, "mid_kind", "ये कौन है? रमेश किससे बात कर रहे हो... मैं उनकी माँ हूँ"),
    ("colleague", E, "mid_kind", "hello main unka dost hoon, phone mere paas reh gaya"),
    ("spouse", H, "mid_kind", "वो बाहर चले गए, मैं उनकी पत्नी, जो पूछना है मुझसे पूछो"),
    ("child", E, "mid_kind", "papa gaye, main unki beti, aap mujhe batao kitne paise kate"),
]
for cat, lang, point, u in tp_mid:
    add("third_party", cat, point, lang, [u] + F[lang])

# false claims of being the borrower (group 1, reported apart)
fc = [
    (H, ["हाँ मैं ही रमेश हूँ", "हाँ बोलिए", "1985", "1986", "1984"]),
    (E, ["haan main hi Ramesh", "haan", "1983", "1984"]),
    (H, ["जी मैं ही हूँ", "जी", "याद नहीं"]),
    (E, ["speaking", "ok", "yaad nahi hai exact"]),
    (H, ["हाँ मैं बोल रहा हूँ", "हाँ जी", "1984"]),
    (E, ["main hi bol raha hu", "theek hai", "unnis sau chaurasi"]),
    (H, ["हाँ मैं ही हूँ", "ठीक है", "अस्सी के आसपास"]),
    (E, ["haan main Ramesh", "haan", "1984 ya 85"]),
    (H, ["मैं ही रमेश", "हाँ", "पहले आप बताइए कौन सा साल है रिकॉर्ड में"]),
    (E, ["haan main hi", "haan", "1980", "kya galat hai? 1982?"]),
    (H, ["जी हाँ मैं ही बोल रहा", "हाँ", "उन्नीस सौ पचासी"]),
    (E, ["main hi hoon bolo", "haan", "pata nahi, wife se puchna padega"]),
    (H, ["मैं ही हूँ", "हाँ", "1984 है ना? सही है?"]),
    (E, ["yes I am Ramesh", "yes", "84"]),
]
for lang, turns in fc:
    add("third_party", "false_claim", "opening", lang, turns + F[lang][:1])

# ---------------- group 2: refusals and disengagement -----------------
ref = [
    ("busy", "opening", H, "अभी मैं गाड़ी चला रहा हूँ"),
    ("busy", "opening", E, "abhi meeting mein hu yaar"),
    ("busy", "go_ahead", H, "अभी टाइम नहीं है, खेत में हूँ"),
    ("busy", "go_ahead", E, "busy hu abhi, baad me"),
    ("busy", "birth_year", H, "अरे अभी दुकान पे ग्राहक खड़े हैं"),
    ("busy", "mid_recall", E, "bhai abhi bahut kaam hai, main free nahi hoon"),
    ("busy", "mid_kind", H, "बच्चे को स्कूल से लाना है, अभी नहीं हो पाएगा"),
    ("busy", "opening", H, "हम बस में हैं, कुछ सुनाई नहीं दे रहा, बाद में"),
    ("not_interested", "opening", H, "नहीं चाहिए कुछ"),
    ("not_interested", "opening", E, "interested nahi hu"),
    ("not_interested", "go_ahead", H, "नहीं, मुझे कोई बात नहीं करनी"),
    ("not_interested", "go_ahead", E, "nahi nahi rehne do, koi zaroorat nahi"),
    ("not_interested", "birth_year", H, "ये सब मैं नहीं बताऊँगा, रहने दीजिए"),
    ("not_interested", "mid_recall", E, "mujhe in sawalon ka jawab nahi dena"),
    ("not_interested", "mid_kind", H, "छोड़िए ना, क्या फायदा इन सब का"),
    ("not_interested", "mid_kind", H, "मैं जवाब नहीं देना चाहता"),
    ("stop_calling", "opening", H, "बार बार फ़ोन मत करो"),
    ("stop_calling", "opening", E, "please is number pe call mat karna dobara"),
    ("stop_calling", "go_ahead", H, "मेरा नंबर अपनी लिस्ट से हटा दो"),
    ("stop_calling", "birth_year", E, "aage se mujhe call mat karna, samjhe"),
    ("stop_calling", "mid_recall", H, "आज के बाद इस नंबर पर फ़ोन नहीं आना चाहिए"),
    ("stop_calling", "mid_kind", E, "number delete karo mera, roz roz call aate hain"),
    ("stop_calling", "go_ahead", H, "दोबारा कॉल किया तो शिकायत कर दूँगा"),
    ("call_later", "opening", H, "शाम को फ़ोन करना"),
    ("call_later", "opening", E, "kal subah call karo please"),
    ("call_later", "go_ahead", H, "आप एक घंटे बाद कर लीजिए"),
    ("call_later", "go_ahead", E, "sunday ko karna, abhi nahi"),
    ("call_later", "birth_year", H, "बाद में बात करते हैं"),
    ("call_later", "mid_recall", E, "thodi der baad call back karo"),
    ("call_later", "mid_kind", H, "रात को आठ बजे के बाद कीजिए"),
    ("call_later", "mid_kind", H, "परसों करिए, अभी शादी में आए हैं"),
    ("human", "opening", H, "किसी आदमी से बात कराओ, मशीन से नहीं करनी"),
    ("human", "go_ahead", E, "mujhe kisi real insaan se baat karni hai"),
    ("human", "go_ahead", H, "आपके मैनेजर से बात करवाइए"),
    ("human", "birth_year", E, "branch wale se baat karwao"),
    ("human", "mid_recall", H, "ये रोबोट से नहीं, किसी स्टाफ़ से बात कराइए"),
    ("human", "mid_kind", E, "koi agent hai kya? usko line pe lo"),
    ("human", "mid_kind", H, "बैंक वाले भैया से बात करा दो जिन्होंने लोन किया था"),
    ("writing", "opening", H, "जो भी है लिख के भेज दो"),
    ("writing", "go_ahead", E, "email kar do, main padh lunga"),
    ("writing", "go_ahead", H, "मुझे चिट्ठी भेज दीजिए, फ़ोन पर नहीं"),
    ("writing", "birth_year", E, "whatsapp pe message kar do details"),
    ("writing", "mid_recall", H, "ये सब लिखित में दीजिए"),
    ("writing", "mid_kind", E, "sms bhej do, abhi baat nahi kar sakta"),
    ("writing", "mid_kind", H, "मेल पे डाल दो सवाल, मैं जवाब दे दूँगा"),
    ("hostile", "opening", H, "फ़ालतू का फ़ोन, दिमाग़ मत ख़राब करो"),
    ("hostile", "opening", E, "kya bakwaas hai yeh, kaat do phone"),
    ("hostile", "go_ahead", H, "तुम लोग चोर हो, सब फ्रॉड है"),
    ("hostile", "go_ahead", E, "bhaad mein jao"),
    ("hostile", "birth_year", H, "क्यों बताऊँ अपना साल? चलो भागो"),
    ("hostile", "mid_recall", E, "pagal ho kya, kitni baar puchoge, chup karo"),
    ("hostile", "mid_kind", H, "बकवास बंद करो"),
    ("hostile", "mid_kind", H, "तेरी ऐसी की तैसी, फ़ोन रख"),
]
for cat, point, lang, u in ref:
    add("refusal", cat, point, lang, [u])
for point, turns in [("opening", ["", ""]), ("opening", [" ", ""]), ("go_ahead", ["", ""]),
                     ("birth_year", ["", ""]), ("mid_recall", ["", ""]), ("mid_kind", ["", ""])]:
    add("refusal", "silent", point, H, turns)
for point, lang, turns in [("opening", H, ["[शोर]", "[शोर]", "[शोर]"]), ("go_ahead", E, ["hmm", "...", "hmm"]),
                           ("mid_recall", H, ["उम्म", "अं", "उम्म"]), ("mid_kind", E, ["(background TV noise)", "...", "..."]),
                           ("birth_year", H, ["हैलो? हैलो?", "हैलो", "हैलो?"])]:
    add("refusal", "noise", point, lang, turns)

# ---------------- group 3: genuine borrowers, ordinary confirmation -----------------
g = [
    ("ramesh", H, "हाँ, रमेश जी से हो रही है।", "verbatim real-phone reply, Latin record name"),
    ("ramesh_dev", H, "हाँ, रमेश जी से हो रही है।", "verbatim real-phone reply, Devanagari record name"),
    ("ramesh", H, "हाँ बोलिए", ""), ("ramesh", H, "जी", ""), ("ramesh", E, "speaking", ""),
    ("ramesh", E, "haan bol raha hoon", ""), ("ramesh", H, "रमेश", "name only"), ("ramesh", E, "haan bataiye", ""),
    ("ramesh", E, "ji kahiye", ""), ("ramesh", H, "हाँ जी बोलिए, कौन?", ""), ("ramesh", H, "जी हाँ", ""),
    ("ramesh", E, "haan ji ramesh here", ""), ("ramesh", H, "हाँ रमेश बोल रहा हूँ", ""),
    ("ramesh", E, "Ramesh speaking", ""), ("ramesh", H, "जी, हम ही हैं", ""), ("ramesh", H, "हाँ भाई बोलो", ""),
    ("ramesh", E, "yes yes tell me", ""), ("ramesh", H, "हाँ जी, हम रमेश बोल रहे हैं", ""),
    ("ramesh", H, "हां जी बोल रहे हैं", ""), ("ramesh", E, "haan haan bolo na", ""),
    ("ramesh", H, "जी, बताइए क्या बात है", ""), ("ramesh", E, "ha ji ramesh hi hu", ""),
    ("ramesh", H, "हाँ वही हूँ", ""), ("ramesh", E, "han me hi hu", ""),
    ("ramesh", H, "हाँ जी हाँ, रमेश ही बात कर रहा है", ""), ("ramesh", E, "ji haan, Ramesh Namoona", ""),
    ("ramesh", H, "रमेश नमूना बोल रहा, बोलो", ""), ("ramesh", H, "हाँ जी नमस्ते", ""),
    ("ramesh", E, "hello haan ji", ""), ("ramesh", H, "हाँ जी रमेश जी से बात हो रही है आपकी", ""),
    ("ramesh", E, "haan, Ramesh ji se hi baat ho rahi hai", ""), ("ramesh", H, "अरे हाँ हाँ, मैं ही, बोलिए बोलिए", ""),
    ("ramesh", E, "matlab haan, main hi hoon", ""), ("ramesh", H, "जी सर बोलिए", ""), ("ramesh", H, "हाँजी", ""),
    ("ramesh", E, "yes speaking, who is this", ""), ("ramesh", H, "हाँ मैं हूँ रमेश, कौन बोल रहा है?", ""),
    ("ramesh", E, "woh... haan ji, Ramesh, boliye", ""), ("ramesh", H, "हाँ जी मेरा ही नंबर है", ""),
    ("ramesh", E, "haan mera hi number hai", ""), ("ramesh", H, "हाँ, बोलिए, सुन रहा हूँ", ""),
    ("ramesh", E, "bolo bolo sun raha hu", ""),
    ("sunita", H, "हाँ, सुनीता जी से हो रही है।", ""), ("sunita", H, "जी, सुनीता बोल रही हूँ", ""),
    ("sunita", E, "haan ji, Sunita here, boliye", ""), ("sunita", H, "हाँ बोलिए", ""),
    ("irfan", H, "हाँ, इरफ़ान जी से हो रही है।", ""), ("irfan", E, "ji Irfan bol raha", ""),
    ("irfan", H, "जी हाँ, इरफ़ान", ""), ("irfan", E, "haan irfaan hi hu", "misspelt name"),
    ("gurpreet", H, "हाँ, गुरप्रीत जी से हो रही है।", ""), ("gurpreet", E, "haanji, Gurpreet bol rahi aan", ""),
    ("gurpreet", H, "हाँ जी, गुरप्रीत", ""), ("lakshmi", H, "हाँ, लक्ष्मी जी से हो रही है।", ""),
    ("lakshmi", E, "haan Laxmi speaking", "misspelt name"), ("lakshmi", H, "जी, मैं लछमी", "misheard name"),
    ("ramesh", H, "हाँ जी, रामेश बोल रहा हूँ", "misheard name"), ("ramesh", E, "haan Rames ji se baat ho rahi", "dropped h"),
    ("ramesh", H, "हाँ, आप सही नंबर पे बात कर रहे हैं", ""), ("ramesh", E, "haan ji, aap Ramesh se hi baat kar rahe ho", ""),
    ("ramesh", H, "हम्म हाँ", ""), ("ramesh", E, "ji boliye ji", ""), ("ramesh", H, "हाँ जी हाँ बताइए क्या सेवा करूँ", ""),
    ("sunita", E, "haan main hi Sunita, boliye", ""),
]
for record, lang, u, note in g:
    add("genuine", "identity", "opening", lang, [u], record=record, note=note)

# genuine borrowers answering the year in ordinary ways (record year 1984)
yrs = [(H, "1984"), (H, "उन्नीस सौ चौरासी"), (H, "मेरा जन्म 1984 में हुआ था"), (E, "84"), (E, "nineteen eighty four"),
       (H, "चौरासी"), (E, "mera 1984 hai"), (H, "जी 1984"), (E, "haan 1984 ji"), (H, "साल... 1984, जून का"),
       (E, "1984 mein paida hua tha main"), (H, "पंद्रह जून उन्नीस सौ चौरासी"), (E, "uh 1984"), (H, "1984 है"),
       (E, "ek minute... haan 1984"), (H, "उन्नीस चौरासी")]
for lang, u in yrs:
    add("genuine_year", "birth_year", "birth_year", lang, [u])

# ---------------- group 4: cooperative replies with refusal-like words -----------------
nr = [
    ("opening", H, "नहीं नहीं, बोलिए, मैं ही हूँ"), ("opening", E, "nahi nahi boliye, main Ramesh hi hoon"),
    ("go_ahead", H, "अभी बिज़ी था, अब बोलो"), ("go_ahead", E, "abhi busy tha, ab bolo"),
    ("go_ahead", H, "बंद मत कीजिए, बोलिए"), ("go_ahead", E, "phone mat kaatna, haan pucho"),
    ("go_ahead", H, "ठीक है, पूछिए, पर जल्दी"), ("go_ahead", E, "haan haan two minute hai, pucho"),
    ("go_ahead", H, "मना क्यों करूँगा, पूछिए"), ("go_ahead", E, "koi dikkat nahi, pucho"),
    ("go_ahead", H, "नहीं कोई बात नहीं, पूछ लीजिए"), ("go_ahead", E, "time to nahi hai zyada par chalo pucho"),
    ("go_ahead", H, "हाँ, किसी इंसान से नहीं, आपसे ही कर लेंगे बात"), ("go_ahead", E, "machine ho to bhi chalega, bolo"),
    ("birth_year", H, "बताने में कोई दिक्कत नहीं, 1984"), ("birth_year", E, "nahi chhupana kya, 1984"),
    ("mid_recall", H, "लिख के नहीं चाहिए, फ़ोन पे ही बता दो... हाँ, एक बीमा लिया था"),
    ("mid_recall", E, "likh ke nahi chahiye, phone pe hi bata do, haan insurance liya tha"),
    ("mid_recall", H, "नहीं, और कुछ नहीं लिया, बस लोन"), ("mid_recall", E, "nahi, kuch nahi liya extra"),
    ("mid_recall", H, "मैनेजर ने बोला था लेना पड़ेगा, तो ले लिया एक बीमा"),
    ("mid_recall", E, "agent bola tha ki baad mein call aayega, haan ek policy li thi"),
    ("mid_recall", H, "बैंक वाले ने कहा मना मत करो, तो एक बीमा ले लिया"),
    ("mid_recall", E, "maine mana kiya tha par unhone add kar diya insurance"),
    ("mid_recall", H, "रुकिए मत, बताता हूँ, एक बीमा लिया था"),
    ("mid_recall", E, "nahi nahi, band mat karo, mujhe yaad aa raha hai, ek insurance tha"),
    ("mid_recall", H, "मुझे शिकायत करनी है, उन्होंने ज़बरदस्ती बीमा डाल दिया"),
    ("mid_recall", E, "unhone bola tha phone pe call aayega to haan bolna, bas"),
    ("mid_kind", H, "अब याद नहीं ठीक से, पर शायद बीमा था"), ("mid_kind", E, "nahi pata exactly, kuch insurance type tha"),
    ("mid_kind", H, "मना नहीं करूँगा, वो बीमा है ज़िंदगी का"),
    ("mid_kind", E, "woh life insurance hai, band karna ho to kaise karte hain?"),
    ("mid_kind", H, "बाद में पता चला कि वो बीमा है"),
    ("mid_kind", E, "baad mein bataunga bolke unhone kuch nahi bataya, policy thi shayad"),
    ("mid_kind", H, "इसमें इंसान को कुछ होने पर पैसा मिलता है"),
    ("mid_kind", E, "agar mujhe kuch ho gaya to loan maaf, aisa kuch"),
    ("mid_kind", H, "नहीं जी, मैंने खुद नहीं लिया, उन्होंने डाल दिया"),
    ("mid_kind", E, "stop... matlab ruko, haan yaad aaya, insurance liya tha"),
    ("mid_recall", H, "हाँ लिया था, पर अभी गाड़ी में हूँ, जल्दी पूछो"),
    ("mid_kind", E, "nahi chahiye tha mujhe, par le liya, bima tha"),
    ("mid_kind", H, "मैं किसी इंसान से बात नहीं करना चाहता, आप ही पूछो, वो बीमा है"),
    ("mid_kind", E, "written me mila tha kuch, par yaad nahi, haan ek bima"),
]
for point, lang, u in nr:
    add("nonrefusal", "cooperative", point, lang, [u])

out = pathlib.Path(sys.argv[1])
if out.exists():
    sys.exit(f"{out} exists; inputs are frozen")
out.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n")
from collections import Counter
print(Counter(c["group"] for c in cases))
print(Counter((c["group"], c["point"]) for c in cases))
