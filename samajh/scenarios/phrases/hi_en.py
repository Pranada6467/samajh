"""Hinglish phrase bank: Hindi in Devanagari with English words in Latin script, as in `data/amounts`.

Model-written and model-reviewed; no human reviewer. Customer lines avoid gendered first-person
verb forms. Amounts mix English number words and Hindi fraction words, as urban speakers do.
"""

from samajh.types import LenderType, LoanKind

FIRST_NAME = "Namoona"
BORROWER = "Namoona Sharma (synthetic)"
PROVIDER = "Namoona Life"
LENDER = {LenderType.bank: "Namoona Bank", LenderType.nbfc: "Namoona Finance"}
LOAN = {LoanKind.gold: "gold loan", LoanKind.personal: "personal loan"}

AMOUNTS = {
    3_500: "साढ़े तीन हज़ार",
    7_500: "seven and a half thousand",
    12_500: "साढ़े बारह हज़ार",
    18_000: "eighteen thousand",
    25_000: "twenty five thousand",
    40_000: "forty thousand",
    52_000: "fifty two thousand",
    100_000: "one lakh",
    125_000: "सवा लाख",
    150_000: "one and a half lakh",
    175_000: "पौने दो लाख",
    200_000: "two lakh",
    250_000: "ढाई लाख",
    300_000: "three lakh",
    500_000: "five lakh",
    1_000_000: "ten lakh",
    2_000_000: "twenty lakh",
}
DURATIONS = {12: "one year", 18: "डेढ़ साल", 24: "two years", 36: "तीन साल", 60: "five years"}
WINDOWS = {15: "fifteen days", 30: "एक महीने"}
YEARS = {1978: "nineteen seventy eight", 1985: "nineteen eighty five", 1990: "nineteen ninety"}

CUSTOMER: dict[str, tuple[str, ...]] = {
    "rp": ("हाँ जी, speaking, बोलिए।", "Yes, बोलिए।", "हाँ, मैं ही हूँ। कौन?"),
    "disc": ("Okay, ठीक है, पूछिए।", "हाँ fine, बोलिए।", "ठीक है, no problem, पूछ लीजिए।"),
    "yob": ("{yob}।", "जी, {yob}।", "Birth year {yob} है।"),
    "ctx.gold": ("हाँ हाँ, gold loan लिया था, अभी recently ही।", "जी, gold पर loan लिया था।"),
    "ctx.personal": ("हाँ जी, personal loan लिया था।", "Yes, लिया था, personal loan।"),
    "recall.insurance": (
        "Loan के साथ... हाँ, एक insurance भी लिया था, {premium} का।",
        "देखिए, loan लिया, और साथ में एक insurance policy, उसका premium {premium} था।",
    ),
    "recall.insurance_noamt": (
        "Loan के साथ एक insurance भी लिया था, बस इतना याद है।",
        "एक insurance था साथ में, amount अभी ध्यान नहीं।",
    ),
    "recall.insurance_added": (
        "Loan लिया था। साथ में एक insurance भी add कर दिया गया, {premium} का।",
        "मैंने तो loan लिया था। ऊपर से एक insurance भी लगा दिया, {premium} rupees का।",
    ),
    "recall.fd": (
        "बस एक FD करवाई थी, loan की security के लिए, {premium} की।",
        "और कुछ नहीं, just एक FD बनवाई थी, {premium} की।",
    ),
    "recall.security_deposit": (
        "Loan के लिए एक security deposit जमा करवाया था, {premium} का, और कुछ नहीं।",
        "बस वो security deposit वाला, {premium} rupees, वही दिया था।",
    ),
    "recall.investment": (
        "एक investment plan लिया था साथ में, {premium} का।",
        "Loan के साथ एक plan में पैसा लगाया था, {premium} rupees।",
    ),
    "recall.not_named": ("कुछ नहीं, बस loan ही लिया था।", "और क्या, loan लिया, that's it।"),
    "recall.dont_know": (
        "पता नहीं, papers में जो लिखा होगा वही... मुझे तो बस loan का पता है।",
        "ये सब मुझे नहीं पता, मैंने तो बस loan के लिए बोला था।",
    ),
    "recall.evasive": (
        "जी, जो bank ने दिया वही सब लिया है, सब ठीक है।",
        "हाँ जी, सब ठीक है, कोई problem नहीं है।",
    ),
    "evasive": (
        "जी हाँ, सब ठीक है।",
        "हाँ जी, सब explain कर दिया था, कोई issue नहीं।",
        "Yes yes, बिल्कुल।",
        "हाँ, ठीक है सब।",
    ),
    "evasive.closed": (
        "जो आपके record में है वही सही है।",
        "जैसा bank ने किया वैसा ही है।",
        "वो सब bank वालों को पता है, मुझे कोई problem नहीं।",
    ),
    "kind.insurance": ("Insurance ही है।", "वो तो insurance है ना, loan वाला insurance।"),
    "kind.fd": ("FD है वो, insurance वगैरह नहीं।", "वो तो FD है, वहीं जमा है।"),
    "kind.security_deposit": (
        "वो security deposit है, loan के against जमा रखा है।",
        "Deposit है जी, security के तौर पर।",
    ),
    "kind.investment": ("Investment है, पैसा लगाने वाला plan।", "वो तो एक investment scheme है।"),
    "kind.dont_know": ("ये तो मुझे नहीं पता कि वो क्या है।", "Honestly मुझे नहीं पता वो क्या चीज़ है।"),
    "premium.say": ("{premium} rupees।", "{premium} लगे थे उसके।", "उसका {premium} pay किया है।"),
    "premium.once": ("{premium} rupees, और वो one time ही देना था।", "एक ही बार का है, {premium} rupees।"),
    "premium.taken": ("{premium} rupees कटे हैं।", "{premium} deduct कर लिए उन्होंने।"),
    "premium.forgot": (
        "कितना था, ये अभी याद नहीं, papers देखने पड़ेंगे।",
        "Amount अभी याद नहीं आ रहा, papers में लिखा होगा।",
    ),
    "premium.dont_know": ("Amount का मुझे कुछ पता नहीं।", "कितने का है, ये मुझे नहीं पता।"),
    "readback.yes": ("हाँ, सही है।", "Yes, यही है।", "हाँ हाँ, correct।"),
    "pay.from_loan": (
        "Loan amount में से ही कट गया था।",
        "वो तो loan में से deduct कर लिया था, हाथ में कम पैसे आए।",
    ),
    "pay.separately": ("अलग से दिया था, loan में से नहीं कटा।", "वो मैंने अपनी तरफ़ से separately pay किया था।"),
    "pay.separately_debited": (
        "Loan में से नहीं, वो तो मेरे savings account से अलग से कट गया।",
        "अलग से गया है, directly मेरे savings account से debit हुआ।",
    ),
    "pay.dont_know": (
        "ये नहीं पता कि कैसे गया, loan में से कटा या अलग से।",
        "पता नहीं, वो payment कैसे हुआ।",
    ),
    "req.yes": (
        "हाँ, बोला था कि इसके बिना loan नहीं मिलेगा।",
        "Compulsory था, उन लोगों ने कहा लेना ही पड़ेगा।",
    ),
    "req.no": ("नहीं, compulsory नहीं था, मैंने अपनी मर्ज़ी से लिया।", "ऐसा कुछ नहीं था कि लेना ही पड़ेगा।"),
    "req.no_plain": (
        "Compulsory है, ऐसा तो किसी ने नहीं बोला था।",
        "नहीं, loan के लिए ज़रूरी है ऐसी कोई बात नहीं हुई।",
    ),
    "req.no_soft": (
        "Compulsory तो नहीं बोला था, बस officer ने कहा ले लो तो अच्छा रहेगा, तो ले लिया।",
        "Force नहीं था, उन्होंने suggest किया था, मुझे ठीक लगा।",
    ),
    "req.dont_know": ("ये तो मुझे नहीं पता, ज़रूरी था या नहीं।", "पता नहीं, इस बारे में कुछ बताया नहीं।"),
    "choice.yes": (
        "हाँ, बताया था कि किसी और company से भी ले सकते हैं।",
        "बोला था, दूसरी company का भी चलेगा, पर मैंने यहीं से ले लिया।",
    ),
    "choice.no": (
        "नहीं, ऐसा तो कुछ नहीं बताया, बोला यही लेना है।",
        "दूसरी company की तो बात ही नहीं हुई।",
    ),
    "choice.dont_know": ("याद नहीं कि ऐसा कुछ बोला था या नहीं।",),
    "cover.say": (
        "मुझे कुछ हो गया तो loan insurance company भरेगी, {cover} तक का cover है।",
        "Cover... {cover} rupees का बताया था।",
    ),
    "cover.dont_know": ("Cover का तो कुछ पता नहीं।", "ये नहीं बताया, कितने का cover है मुझे नहीं पता।"),
    "term.say": ("{term} के लिए।", "{term} का है।"),
    "term.dont_know": ("कितने time का है, ये नहीं पता।", "Duration का तो ध्यान नहीं।"),
    "cancel.say": (
        "हाँ, बोला था {window} के अंदर cancel कर सकते हैं।",
        "बताया था, {window} का time होता है cancel करने का।",
    ),
    "cancel.not_told": (
        "नहीं, cancel करने के बारे में तो कुछ नहीं बताया।",
        "ऐसी कोई बात नहीं हुई थी cancel की।",
    ),
    "cancel.dont_know": ("पता नहीं, cancel होता है या नहीं।",),
    "feat.none": (
        "नहीं, वापस कहाँ मिलेगा, insurance है, कुछ हो गया तभी काम आएगा।",
        "Refund तो नहीं मिलता, ये insurance का पैसा है।",
    ),
    "feat.none_window": (
        "वापस नहीं मिलता, बस शुरू के {window} में cancel करो तभी मिलता है, उसके बाद नहीं।",
    ),
    "feat.fd_anytime": (
        "हाँ, FD है तो जब चाहिए तब तुड़वा सकते हैं।",
        "मिल जाएगा ना, FD है, जब ज़रूरत हो निकाल लो।",
    ),
    "feat.deposit_after": (
        "हाँ, {period} बाद वापस मिल जाएगा, deposit ही तो है।",
        "{period} के बाद पूरा पैसा वापस, यही बोला था, deposit amount है।",
    ),
    "feat.after": (
        "हाँ, बोला था कि {period} के बाद कभी भी withdraw कर सकते हैं।",
        "{period} बाद पैसा निकाल सकते हैं, वहाँ यही कहा था।",
    ),
    "feat.guaranteed": (
        "हाँ मिलेगा, और बढ़कर मिलेगा, guarantee है बोला था।",
        "मिलता है ना, guaranteed return है इसमें, पैसा बढ़कर आता है।",
    ),
    "feat.dont_know": ("मिलेगा या नहीं, ये मुझे नहीं पता।",),
    "consent.insurance.signed_form": (
        "Loan और insurance दोनों लिए थे। Insurance के form पर अलग से sign किया था।",
        "Loan के साथ insurance भी। उसके लिए अलग form था, उस पर sign किए थे।",
    ),
    "consent.insurance.otp": (
        "Loan और साथ में insurance। Insurance के लिए phone पर OTP आया था, वो मैंने बता दिया था।",
        "दोनों के लिए हाँ की थी, loan और insurance। Insurance का OTP आया था, वही दिया।",
    ),
    "consent.insurance.digital_click": (
        "Loan और insurance। Insurance के लिए app में ही tick करके accept किया था।",
        "दोनों लिए थे। Insurance वाला तो app में ही select किया था, button दबाकर।",
    ),
    "consent.insurance.recorded_call": (
        "Loan और insurance। Insurance के लिए call आया था, recording चालू है बोलकर पूछा, मैंने हाँ बोला।",
        "दोनों। Insurance के लिए एक call आई थी, बोला call record हो रही है, उसी पर हाँ कही थी।",
    ),
    "consent.insurance.verbal": (
        "Loan और insurance। Insurance के लिए बस verbally हाँ बोल दी थी, sign वगैरह कुछ नहीं।",
        "दोनों के लिए हाँ की थी। Insurance का बस बोलकर ही हुआ, कोई paper या OTP नहीं।",
    ),
    "consent.fd.signed_form": (
        "Loan और वो FD। FD के लिए form पर sign किए थे।",
        "Loan लिया और FD करवाई। उसके papers पर sign किए थे।",
    ),
    "consent.fd.otp": (
        "Loan और FD। FD के लिए phone पर OTP आया था, वो बता दिया था।",
        "Loan, और साथ में FD। उसका OTP आया था, वही दिया।",
    ),
    "consent.security_deposit.signed_form": (
        "Loan और security deposit। Deposit के form पर sign किए थे।",
        "Loan के साथ वो deposit। उसके लिए कई forms पर sign करवाए थे।",
    ),
    "consent.investment.otp": (
        "Loan और वो investment plan। Plan के लिए phone पर OTP आया था, बता दिया था।",
        "Loan, और plan भी। उसका OTP आया था, वही दिया।",
    ),
    "consent.no": (
        "मैंने तो बस loan के लिए हाँ बोली थी। Insurance के लिए मुझसे किसी ने नहीं पूछा।",
        "सिर्फ़ loan। Insurance लेने की हामी मैंने कभी नहीं भरी।",
    ),
    "consent.no_method": (
        "Loan और insurance, दोनों के लिए हाँ बोली थी। कैसे... वो अब याद नहीं।",
        "दोनों के लिए agree किया था। पर कैसे किया था, ये ध्यान नहीं आ रहा।",
    ),
    "consent.dont_know": ("ये मुझे नहीं पता कि किस-किस चीज़ के लिए agree किया था।",),
    "close": ("ठीक है, thank you।", "Okay जी, bye।"),
    "concern.coached_answers": (
        "वैसे सच बताऊँ, agent ने बोला था कि verification call आएगा तो सबमें yes बोल देना।",
    ),
    "concern.learned_after_sale": ("मुझे तो बाद में पता चला, जब account से पैसा कटा।",),
    "concern.signed_without_explanation": (
        "बहुत सारे papers पर sign करवाए थे, किसी ने बताया नहीं कौन सा किस चीज़ का है।",
    ),
    "yn.yes": ("हाँ।", "जी हाँ।", "Yes, सही है।", "हाँ हाँ।", "Yes।"),
    "yn.bought.no_fd": ("Insurance policy? नहीं जी, मैंने तो FD करवाई थी।",),
    "yn.bought.no_security_deposit": ("नहीं, insurance नहीं, वो तो security deposit था।",),
    "yn.bought.no_investment": ("Insurance नहीं जी, वो तो investment plan है।",),
    "yn.bought.no_consent": ("ली नहीं जी, वो तो मुझसे पूछे बिना कर दी गई।",),
    "yn.bought.unsure": ("पता नहीं जी, मुझे इसका कुछ idea नहीं।",),
    "yn.premium.no": ("नहीं, इतना तो नहीं था।",),
    "yn.premium.unsure": ("Amount मुझे याद नहीं, papers देखने पड़ेंगे।",),
    "yn.payment.no_separately": ("नहीं, loan में से नहीं, वो तो अलग से दिया था।",),
    "yn.payment.unsure": ("ये मुझे नहीं पता कि payment कैसे हुआ।",),
    "yn.consent.no": ("नहीं, इसके लिए तो मुझसे पूछा ही नहीं गया।",),
    "yn.consent.unsure": ("पता नहीं, इसके लिए yes किया था या नहीं, याद नहीं।",),
    "yn.explained.no": ("कहाँ explain किया, कुछ नहीं बताया था।",),
    "yn.explained.unsure": ("याद नहीं कि कुछ explain किया था या नहीं।",),
}

BOT: dict[str, str] = {
    "rp": "नमस्ते, क्या मेरी बात {name} जी से हो रही है?",
    "disc": (
        "मैं {lender} की customer care team की ओर से बोल रही हूँ। मैं एक automated AI assistant हूँ। "
        "यह sales call नहीं है और इसमें कुछ बेचा नहीं जाएगा। यह call सिर्फ़ आपका feedback लेने के लिए है "
        "और सही record रखने के लिए record हो रही है। आप मना कर सकते हैं, कभी भी रोक सकते हैं या किसी "
        "कर्मचारी से बात करने को कह सकते हैं। मैं आपसे OTP, PIN, password या account number कभी नहीं "
        "पूछूँगी। क्या हम आगे बढ़ें?"
    ),
    "yob": "Verification के लिए, please सिर्फ़ अपना birth year बताइए।",
    "ctx": "Thank you। आपने हाल ही में हमसे {loan} लिया है, यह call उसी के बारे में है। ठीक है?",
    "recall": "Loan के साथ आपने क्या-क्या लिया, और कितने का?",
    "kind": "Loan के साथ जो चीज़ ली गई, आपकी समझ में वह क्या है: insurance, FD, या कुछ और?",
    "premium": "उसके लिए आपने कितने rupees दिए?",
    "pay": "वह amount कैसे pay हुआ: loan amount में से, या अलग से?",
    "req": "क्या loan पाने के लिए उसे लेना ज़रूरी था?",
    "choice": "क्या आपको बताया गया था कि वही चीज़ आप किसी दूसरी company से भी ले सकते हैं?",
    "cover": "उसमें कितने amount का cover है?",
    "term": "और वह कितने time के लिए है?",
    "cancel": "क्या आपको बताया गया था कि आप उसे cancel कर सकते हैं या नहीं, और कब तक?",
    "feat": "अगर आप वह पैसा वापस चाहें, तो क्या मिल सकता है, और कब?",
    "consent": "Loan लेते समय आपने क्या-क्या लेने के लिए हाँ की थी, और हाँ कैसे की थी?",
    "readback": "{canon}, यानी {inr} rupees, सही है?",
    "close": "Thank you। आपने time दिया, इसके लिए धन्यवाद। नमस्ते।",
    "yn.intro": (
        "नमस्ते, मैं {lender} से बोल रही हूँ। आपके {loan} के बारे में कुछ details confirm करनी हैं। "
        "Please हाँ या ना में जवाब दीजिए।"
    ),
    "yn.bought": "हमारे records के अनुसार आपने loan के साथ {provider} की एक insurance policy ली है। सही है?",
    "yn.premium": "इस policy का premium {canon} rupees है। सही है?",
    "yn.payment.from_loan": "यह premium आपके loan amount में से deduct किया गया है। सही है?",
    "yn.payment.separately": "यह premium आपने अलग से pay किया है। सही है?",
    "yn.consent": "यह policy आपने अपनी consent से ली है। सही है?",
    "yn.explained": "Policy के terms आपको explain कर दिए गए थे। सही है?",
    "yn.close": "Thank you। नमस्ते।",
}
