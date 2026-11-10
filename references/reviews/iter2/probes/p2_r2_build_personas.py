"""Fresh whole-call personas (verifier-written, before reading _lexicon.py or tests). Replies are keyed by the
bot's last line key; a list is consumed in order and its last item repeats. `switch_on` names a key at which the
persona hands over to `then` (a third party taking the phone)."""
import json, pathlib, sys

W1 = {
    "right_party.ask": "हाँ जी, मैं रमेश ही बोल रहा हूँ", "disclosure.go_ahead": "हाँ जी, पूछिए", "second_check.ask": "1984",
    "open_recall.ask": "हाँ, लोन के साथ एक जीवन बीमा लिया था, बावन हज़ार का",
    "kind.ask": "जीवन बीमा है, मुझे कुछ हो गया तो लोन चुक जाएगा", "premium.ask": "बावन हज़ार",
    "read_back": "हाँ सही है", "payment_source.ask": "लोन की रकम में से ही कट गया था", "payment_frequency.ask": "एक ही बार",
    "required_for_loan.ask": "बताया था कि मर्ज़ी है, ज़रूरी नहीं", "provider_choice.ask": "नहीं, ये नहीं बताया",
    "cover.ask": "पाँच लाख तक", "term.ask": "दो साल का", "cancel_window.ask": "तीस दिन में बंद करा सकते हैं",
    "features.ask": "नहीं और कुछ नहीं", "consent.ask": "मैंने फ़ॉर्म पर साइन किया था और हाँ बोला था",
    "stop_check": "हाँ आगे पूछिए", "callback.when": "कल शाम", "*": "हाँ",
}
personas = [
    dict(id="W01-cooperative-clear", lang="hi", record="ramesh", replies=W1),
    dict(id="W02-wrong-amounts", lang="hi-en", record="ramesh", replies={
        "right_party.ask": "haan ji main hi bol raha hoon", "disclosure.go_ahead": "haan pucho", "second_check.ask": "1984",
        "open_recall.ask": "haan ek insurance liya tha", "kind.ask": "insurance hai, loan cover karta hai",
        "premium.ask": "pachees hazaar diye the", "read_back": "haan", "payment_source.ask": "loan mein se kata",
        "payment_frequency.ask": "ek baar", "required_for_loan.ask": "bola tha zaroori hai", "provider_choice.ask": "nahi",
        "cover.ask": "do lakh ka cover hai", "term.ask": "ek saal", "cancel_window.ask": "pata nahi", "features.ask": "nahi",
        "consent.ask": "unhone bola sign karo to kar diya", "stop_check": "haan", "*": "haan"}),
    dict(id="W03-took-nothing", lang="hi", record="ramesh", replies={
        "right_party.ask": "जी हाँ, मैं रमेश", "disclosure.go_ahead": "हाँ", "second_check.ask": "उन्नीस सौ चौरासी",
        "open_recall.ask": "नहीं, कुछ नहीं लिया, सिर्फ़ लोन", "open_recall.nothing": "नहीं, किसी ने कोई बात नहीं की",
        "consent.ask": "बस लोन के कागज़ पे साइन किए थे", "stop_check": "हाँ", "*": "नहीं"}),
    dict(id="W04-hedged", lang="hi", record="ramesh", replies={
        "right_party.ask": "हाँ जी मैं ही हूँ", "disclosure.go_ahead": "हाँ बोलिए", "second_check.ask": "1984",
        "open_recall.ask": "शायद कुछ बीमा जैसा था, ठीक से याद नहीं", "kind.ask": "बीमा होगा शायद",
        "premium.ask": "पचास हज़ार के आसपास होगा", "premium.say_again": "पचास पचपन हज़ार के बीच", "read_back": "हाँ लगभग",
        "payment_source.ask": "शायद लोन से ही कटा", "payment_frequency.ask": "पता नहीं, शायद एक बार",
        "required_for_loan.ask": "याद नहीं क्या बोला था", "provider_choice.ask": "पता नहीं", "cover.ask": "चार पाँच लाख होगा",
        "term.ask": "शायद दो साल", "cancel_window.ask": "पता नहीं", "features.ask": "नहीं पता", "consent.ask": "याद नहीं",
        "stop_check": "हाँ पूछिए", "*": "पता नहीं"}),
    dict(id="W05-midcall-refusal", lang="hi-en", record="ramesh", replies={
        "right_party.ask": "haan main hi Ramesh", "disclosure.go_ahead": "theek hai", "second_check.ask": "1984",
        "open_recall.ask": "haan ek bima tha", "kind.ask": "life insurance",
        "premium.ask": "bas ab aur nahi, band karo ye call, mujhe aur jawab nahi dena", "stop_check": "nahi, band karo",
        "*": "nahi"}),
    dict(id="W06-midcall-third-party", lang="hi", record="ramesh", replies={
        "right_party.ask": "हाँ मैं ही रमेश बोल रहा हूँ", "disclosure.go_ahead": "हाँ", "second_check.ask": "1984",
        "open_recall.ask": "हाँ, एक बीमा लिया था", "kind.ask": "बीमा है", "*": "हाँ"},
        switch_on="premium.ask", then={
        "premium.ask": "हेलो, मैं उनकी पत्नी बोल रही हूँ, वो बाहर गए, आप मुझे बताइए कितने का था",
        "read_back": "मुझे नहीं पता, मैं उनकी पत्नी हूँ", "stop_check": "हाँ, मुझे ही बता दीजिए",
        "*": "मुझे ही बता दीजिए, मैं उनकी पत्नी हूँ"}),
    dict(id="W07-language-switch", lang="hi", record="ramesh", replies={
        "right_party.ask": "हाँ मैं ही", "disclosure.go_ahead": "मुझे हिंदी ठीक से नहीं आती, तमिल में बात कीजिए",
        "*": "Tamil please"}),
    dict(id="W08-rambling", lang="hi", record="ramesh", replies={
        "right_party.ask": "हाँ जी नमस्ते, मैं रमेश ही बोल रहा हूँ, बताइए क्या बात है, मैं अभी खाना खा रहा था पर कोई बात नहीं",
        "disclosure.go_ahead": "हाँ हाँ, पूछिए, वैसे भी आज छुट्टी है, बच्चे स्कूल गए हैं तो टाइम है",
        "second_check.ask": "देखिए मेरा जन्म, उन्नीस सौ चौरासी में हुआ था, गाँव में, जून का महीना था",
        "open_recall.ask": "अरे वो देखिए, जब मैं बैंक गया था सोना गिरवी रखने, तो वहाँ एक साहब थे, उन्होंने बोला कि ये भी ले लो, एक बीमा था, मुझे लगा कि ज़रूरी है, तो मैंने ले लिया, बावन हज़ार का था शायद, फिर लोन में से ही कट गया",
        "kind.ask": "वो बीमा है ना, मतलब अगर मुझे कुछ हो जाता है तो घरवालों पर लोन का बोझ नहीं आएगा, ऐसा उन्होंने समझाया था, बाक़ी मुझे ज़्यादा नहीं पता",
        "premium.ask": "बावन हज़ार, हाँ बावन हज़ार ही था, मुझे याद है क्योंकि मेरे हाथ में कम पैसे आए थे",
        "read_back": "हाँ जी, बिल्कुल सही, बावन हज़ार",
        "payment_source.ask": "वो सीधा लोन में से काट लिया उन्होंने, मुझे अलग से कुछ नहीं देना पड़ा, पर हाथ में कम आया",
        "payment_frequency.ask": "एक ही बार काटा, फिर कुछ नहीं, वैसे मुझे पक्का नहीं पता कि अगले साल फिर देना है या नहीं",
        "required_for_loan.ask": "उन्होंने तो ऐसे बोला जैसे ज़रूरी हो, पर साफ़ साफ़ नहीं बोला कि लेना ही पड़ेगा, मुझे लगा ज़रूरी है",
        "provider_choice.ask": "नहीं ऐसा कुछ नहीं बोला, मुझे तो पता भी नहीं था कि कहीं और से ले सकते हैं",
        "cover.ask": "पाँच लाख तक का बताया था, मतलब पूरा लोन", "term.ask": "दो साल का, जितना लोन है उतना",
        "cancel_window.ask": "बंद करने का तो कुछ नहीं बताया, मुझे नहीं पता", "features.ask": "नहीं, बाक़ी कुछ याद नहीं",
        "consent.ask": "उन्होंने एक फ़ॉर्म पर साइन करवाया था, बहुत सारे कागज़ थे, मैंने सब पर साइन कर दिया",
        "stop_check": "हाँ हाँ, पूछिए", "*": "हाँ जी"}),
    dict(id="W09-one-word", lang="hi-en", record="ramesh", replies={
        "right_party.ask": "speaking", "disclosure.go_ahead": "ok", "second_check.ask": "1984", "open_recall.ask": "bima",
        "kind.ask": "insurance", "premium.ask": "52000", "read_back": "haan", "payment_source.ask": "loan",
        "payment_frequency.ask": "once", "required_for_loan.ask": "optional", "provider_choice.ask": "nahi",
        "cover.ask": "5 lakh", "term.ask": "2 saal", "cancel_window.ask": "30 din", "features.ask": "nahi",
        "consent.ask": "sign", "stop_check": "haan", "*": "haan"}),
    dict(id="W10-silence-middle", lang="hi", record="ramesh",
         replies={**W1, "kind.ask": ["", "जीवन बीमा है"], "cover.ask": ["", "पाँच लाख तक"]}),
    dict(id="W11-real-phone-opening", lang="hi", record="ramesh",
         replies={**W1, "right_party.ask": "हाँ, रमेश जी से हो रही है।", "right_party.reask": "हाँ जी, बोलिए"}),
    dict(id="W12-suspicious-then-cooperative", lang="hi-en", record="ramesh", replies={
        "right_party.ask": "haan main hi hoon, kya hai?", "disclosure.go_ahead": ["kaun ho tum log, fraud ho kya?", "achha theek hai pucho"],
        "disclosure.reask": "achha theek hai pucho", "second_check.ask": "1984", "open_recall.ask": "haan ek insurance tha bawan hazaar ka",
        "kind.ask": "life insurance", "premium.ask": "bawan hazaar", "read_back": "haan", "payment_source.ask": "loan se kata",
        "payment_frequency.ask": "ek baar", "required_for_loan.ask": "zaroori nahi tha", "provider_choice.ask": "nahi bataya",
        "cover.ask": "paanch lakh", "term.ask": "do saal", "cancel_window.ask": "tees din", "features.ask": "nahi",
        "consent.ask": "haan bola tha form pe", "stop_check": "haan", "*": "haan"}),
    dict(id="W13-dont-know", lang="hi", record="ramesh", replies={
        "right_party.ask": "हाँ, मैं ही रमेश हूँ", "disclosure.go_ahead": "ठीक है", "second_check.ask": "1984",
        "stop_check": "हाँ पूछ लो", "*": "पता नहीं"}),
    dict(id="W14-sunita-cooperative", lang="hi-en", record="sunita", replies={
        "right_party.ask": "ji main Sunita bol rahi hoon", "disclosure.go_ahead": "haan ji pucho", "second_check.ask": "1984",
        "open_recall.ask": "ek insurance liya tha, fifty two thousand ka", "kind.ask": "credit life insurance",
        "premium.ask": "fifty two thousand", "read_back": "haan sahi", "payment_source.ask": "loan amount se cut hua",
        "payment_frequency.ask": "one time", "required_for_loan.ask": "meri marzi thi", "provider_choice.ask": "nahi bataya tha",
        "cover.ask": "paanch lakh", "term.ask": "do saal", "cancel_window.ask": "tees din", "features.ask": "nahi",
        "consent.ask": "maine form sign kiya tha", "stop_check": "haan", "*": "haan"}),
]
out = pathlib.Path(sys.argv[1])
if out.exists():
    sys.exit(f"{out} exists")
out.write_text(json.dumps(personas, ensure_ascii=False, indent=1) + "\n")
print(len(personas))
