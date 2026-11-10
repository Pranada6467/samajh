"""Fresh refusal and non-refusal probes (verifier, iteration 2), rules only and with the LLM fallback.

Effect is read by playing the reply into the real machine at the named question (samajh.dialogue
__main__.effect_of). For a refusal: ended (decline/human/call back, or "when shall we call?") is right,
a stop check is acceptable, anything else is an error. For a non-refusal: an end is an error, a stop
check is friction.
    uv run python p2_refusals.py [--llm]
"""

from __future__ import annotations

import sys
from collections import Counter

from p2_kit import save

from samajh.dialogue import RuleInterpreter
from samajh.dialogue.__main__ import effect_of
from samajh.types import Language

REFUSALS = [
    ("disclosure.go_ahead", "hi", "मुझे इन सब में नहीं पड़ना, आप रहने ही दीजिए"),
    ("open_recall.ask", "hi", "भाई साहब मेरा दिमाग मत खाओ"),
    ("kind.ask", "hi", "ये सब फ़ालतू की बातें हैं, मैं फ़ोन रख रहा हूँ"),
    ("disclosure.go_ahead", "hi-en", "abhi nahi please"),
    ("disclosure.go_ahead", "hi-en", "abhi bilkul time nahi hai yaar"),
    ("open_recall.ask", "hi", "जो पूछना है लिखकर भेज दो, फ़ोन पे कुछ नहीं बताऊँगा"),
    ("premium.ask", "hi-en", "send it in writing, I won't answer on phone"),
    ("open_recall.ask", "hi-en", "mere bete se baat karo, wahi sab dekhta hai"),
    ("kind.ask", "hi", "ये सब मेरा बेटा संभालता है, उससे पूछ लेना"),
    ("payment_source.ask", "hi-en", "aap log pagal ho kya, din mein das baar call karte ho, band karo ye"),
    ("premium.ask", "hi", "मुझे कोई जवाब नहीं देना है"),
    ("consent.ask", "hi", "नहीं करनी कोई बात, समझे?"),
    ("open_recall.ask", "hi-en", "I'm not comfortable sharing this on a call"),
    ("premium.ask", "hi", "मैं ऐसे फ़ोन पर कुछ नहीं बताता"),
    ("cover.ask", "hi-en", "please mujhe dobara call mat karna"),
    ("kind.ask", "hi-en", "mera number list se hata do"),
    ("term.ask", "hi-en", "ab bas, aur sawal nahi"),
    ("cancel_window.ask", "hi-en", "kitne sawaal poochoge, main ja raha hoon"),
    ("disclosure.go_ahead", "hi", "मैं अभी अस्पताल में हूँ, बात नहीं हो पाएगी"),
    ("open_recall.ask", "hi-en", "ghar pe guest aaye hain, kal karna"),
    ("kind.ask", "hi-en", "yeh sab main branch mein jaake hi baat karunga"),
    ("premium.ask", "hi", "मुझे ब्रांच में बात करनी है, फ़ोन पे नहीं"),
    ("open_recall.ask", "hi-en", "kisi asli bande se baat karao"),
    ("kind.ask", "hi-en", "aap machine ho? mujhe insaan chahiye"),
    ("premium.ask", "hi", "कोई ज़िंदा आदमी है वहाँ? उससे बात कराओ"),
    ("payment_source.ask", "hi-en", "manager ko line pe lao"),
    ("disclosure.go_ahead", "hi-en", "no, I don't want to do this survey"),
    ("disclosure.go_ahead", "hi-en", "nahi chahiye ye feedback-weedback"),
    ("premium.ask", "hi", "इसका जवाब देना मैं ज़रूरी नहीं समझती"),
    ("open_recall.ask", "hi-en", "maaf kijiye, main is baare mein baat nahi karna chahta"),
    ("disclosure.go_ahead", "hi", "अभी मूड नहीं है, बाद में देखेंगे"),
    ("open_recall.ask", "hi-en", "khaana kha raha hoon, thodi der baad"),
    ("kind.ask", "hi-en", "mujhe ye call pasand nahi aayi, rakhiye"),
    ("premium.ask", "hi", "मेरे वकील से बात कीजिए"),
    ("disclosure.go_ahead", "hi-en", "pehle mujhe letter bhejo bank ka, phir baat karenge"),
    ("cover.ask", "hi", "बस बस, हो गया, धन्यवाद"),
    ("consent.ask", "hi-en", "I have to leave now, sorry"),
    ("payment_source.ask", "hi-en", "chhodo yaar, kya fayda"),
    ("open_recall.ask", "hi", "मुझे परेशान मत कीजिए प्लीज़"),
    ("kind.ask", "hi", "अरे यार फिर से ये कॉल, नहीं बताना कुछ"),
    ("premium.ask", "hi", "ये मेरी पर्सनल बात है, मैं नहीं बताऊँगा"),
    ("disclosure.go_ahead", "hi-en", "do minute bhi nahi hai mere paas"),
    ("term.ask", "hi-en", "ruk jao, mujhe ab aage nahi badhna"),
    ("open_recall.ask", "hi", "मैं ये सवालों का जवाब देने के मूड में नहीं हूँ"),
    ("second_check.ask", "hi", "जन्म का साल क्यों दूँ? नहीं बताना, फ़ोन रखो"),
]

NON_REFUSALS = [
    ("disclosure.go_ahead", "hi-en", "aap kaun bol rahe ho, kis bank se?"),
    ("disclosure.go_ahead", "hi", "ये फ्रॉड कॉल तो नहीं है ना?"),
    ("disclosure.go_ahead", "hi", "उम्म... एक मिनट... हाँ बोलिए"),
    ("disclosure.go_ahead", "hi", "हाँ हाँ ठीक है, पर जल्दी करना, बाहर जा रहा हूँ"),
    ("open_recall.ask", "hi", "बैंक वालों ने बहुत परेशान किया था, किसी ने कुछ नहीं समझाया"),
    ("open_recall.ask", "hi", "मैंने तो मना किया था बीमा के लिए, फिर भी उन्होंने जोड़ दिया"),
    ("kind.ask", "hi-en", "I said no to the insurance but they still added it"),
    ("open_recall.ask", "hi-en", "maine mana kar diya tha, phir bhi insurance daal diya loan mein"),
    ("payment_source.ask", "hi", "मैंने कहा था मुझे नहीं चाहिए, पर बाद में देखा पैसे कट गए"),
    ("kind.ask", "hi", "मुझे बीमा नहीं चाहिए था, फिर भी लगा दिया"),
    ("required_for_loan.ask", "hi-en", "insurance mujhe chahiye hi nahi tha, zabardasti kiya"),
    ("required_for_loan.ask", "hi", "उन्होंने बोला कि मना करोगे तो लोन नहीं मिलेगा"),
    ("cancel_window.ask", "hi-en", "agent bola ki band nahi kar sakte"),
    ("cancel_window.ask", "hi", "मुझे नहीं पता कैसे बंद होता है"),
    ("open_recall.ask", "hi-en", "bank pe mera bharosa nahi raha ab"),
    ("features.ask", "hi-en", "pehle yeh batao, ye paise wapas milenge kya?"),
    ("kind.ask", "hi", "आपकी आवाज़ कट रही है, फिर से बोलिए"),
    ("premium.ask", "hi-en", "kya bola? samjha nahi"),
    ("kind.ask", "hi", "मैंने उस बंदे को बोला कि रहने दो, फिर भी उसने कर दिया"),
    ("premium.ask", "hi-en", "pata nahi yaar, main itna dhyan nahi deta"),
    ("required_for_loan.ask", "hi", "मैं तो मना करना चाहता था पर मजबूरी थी"),
    ("consent.ask", "hi", "मुझे लगा था कि ये ज़रूरी है, इसलिए हाँ बोल दिया"),
    ("consent.ask", "hi-en", "ji, unhone sirf ek form pe sign karwaya, kuch bataya nahi"),
    ("consent.ask", "hi-en", "hamein to kuch samjhaya hi nahi, bas sign le liya"),
    ("kind.ask", "hi", "देखिए मुझे ज़्यादा नहीं पता, बेटे ने सब किया था"),
    ("premium.ask", "hi", "मेरा बेटा साथ गया था, उसे पता होगा, मुझे इतना याद नहीं"),
    ("disclosure.go_ahead", "hi-en", "abhi thoda busy hoon par chalo pooch lo jaldi"),
    ("disclosure.go_ahead", "hi", "ये कॉल रिकॉर्ड क्यों हो रही है?"),
    ("disclosure.go_ahead", "hi-en", "aapko mera number kahan se mila?"),
    ("cancel_window.ask", "hi", "मैंने तो बीमा कैंसल करने को कहा था, आज तक नहीं हुआ"),
    ("kind.ask", "hi", "उसने कहा था बात मत करो किसी से इसके बारे में"),
    ("open_recall.ask", "hi", "हाँ, मैंने मना किया तो बोले कि फ़ोन रख दो, बाद में बात करेंगे"),
    ("features.ask", "hi-en", "branch wale bole ab kuch nahi ho sakta, phone rakh diya"),
    ("open_recall.ask", "hi-en", "ek FD bhi kar di thi, maine bola nahi chahiye tab bhi"),
    ("required_for_loan.ask", "hi-en", "nahi nahi, required nahi tha, meri marzi thi"),
    ("provider_choice.ask", "hi", "नहीं, कहीं और से लेने का कुछ नहीं बताया"),
    ("kind.ask", "hi-en", "uske baare mein kuch nahi pata, aap batao kya hai"),
    ("payment_source.ask", "hi", "पैसे लोन में से कटे, मुझसे पूछा भी नहीं"),
    ("disclosure.go_ahead", "hi", "मुझे यह सब बकवास लगता है जो बैंक करता है, पर पूछिए"),
    ("kind.ask", "hi", "थोड़ा रुकिए, बच्चा रो रहा है... हाँ अब बोलिए"),
    ("disclosure.go_ahead", "hi-en", "main gaadi mein hoon par bol sakta hoon, poochiye"),
    ("consent.ask", "hi", "मुझसे ज़बरदस्ती हाँ करवाई गई थी, मैं तो मना कर रहा था"),
    ("kind.ask", "hi-en", "agent ne kaha sir aap mana mat karo, isliye le liya"),
    ("required_for_loan.ask", "hi-en", "bas itna yaad hai ki manager ne bola zaroori hai"),
    ("disclosure.go_ahead", "hi", "आप लोग फिर से वही बेचने के लिए तो नहीं फ़ोन कर रहे?"),
    ("open_recall.ask", "hi", "मना करने का मौका ही नहीं दिया, सीधे काट लिए पैसे"),
    ("kind.ask", "hi-en", "maine bola tha mujhe insurance nahi lena, unhone kaha compulsory hai"),
    ("open_recall.ask", "hi", "मैंने बीमा लेने से मना किया था लेकिन वो जोड़ दिया गया"),
]

ENDS = {"decline", "human", "wrong_party"}


def classify(effect: str) -> str:
    if effect in ENDS:
        return "ended"
    if effect.startswith("check_"):
        return "stop_check"
    return "went_on"


def main() -> int:
    use_llm = "--llm" in sys.argv
    if use_llm:
        from samajh.clients.llm import LlmClient
        from samajh.dialogue.llm_fallback import LlmFallbackInterpreter

        interp = LlmFallbackInterpreter(LlmClient.from_env(usd_cap=0.4, timeout=10.0), timeout_s=None
                                        if "--no-timeout" in sys.argv else 2.5)
    else:
        interp = RuleInterpreter()
    rows = []
    for label, items in (("refusal", REFUSALS), ("non_refusal", NON_REFUSALS)):
        tally = Counter()
        for key, lang, text in items:
            eff = effect_of(Language(lang), key, text, interp)
            kind = classify(eff)
            tally[kind] += 1
            bad = (label == "refusal" and kind == "went_on") or (label == "non_refusal" and kind == "ended")
            rows.append({"set": label, "key": key, "lang": lang, "text": text, "effect": eff, "bad": bad})
            if bad or kind == "stop_check":
                print(f"{'ERR ' if bad else '    '}{label:11s} {key:24s} {eff:12s} {text}")
        print(f"== {label}: n={len(items)} {dict(tally)}")
    if use_llm:
        print(f"spent {interp._llm.spent_usd:.4f} USD")
    save("p2_refusals_llm" if use_llm else "p2_refusals_rules", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
