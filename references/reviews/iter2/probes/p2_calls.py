"""Fresh whole calls (verifier, iteration 2), rules only. Prints each call with outcome and word-count time."""
import sys
from p2_kit import play, dump
from samajh.dialogue import call_seconds

CALLS = {
 "misled_fd_hinglish": ("hi-en", ["haan ji main Ramesh hi bol raha hoon", "haan boliye", "1984",
     "haan ek FD karwayi thi loan ke saath, bank wale bole the security ke liye",
     "FD hai, fixed deposit, paisa safe rehta hai", "bavan hazaar diye the",
     "haan", "loan ke paise mein se hi adjust kiya tha", "ek hi baar", "zaroori bola tha, bina iske loan nahi milta",
     "nahi, aisa kuch nahi bataya", "FD hai to interest milega na", "teen saal ki hai", "kuch nahi bataya cancel ke baare mein",
     "FD hai to poora paisa wapas milega interest ke saath", "OTP diya tha phone pe"]),
 "took_nothing_hinglish": ("hi-en", ["haan ji, bol raha hoon", "haan theek hai", "1984", "kuch nahi liya, sirf loan",
     "nahi, kisi ne kuch nahi bola", "bas loan ke papers pe sign kiya"]),
 "impatient_hi": ("hi", ["हाँ बोलो", "जल्दी बोलो क्या है", "हाँ पूछो जल्दी", "84", "हाँ बीमा था", "बीमा", "पता नहीं", "कटा था", "पता नहीं",
     "पता नहीं", "पता नहीं", "पता नहीं", "पता नहीं", "पता नहीं", "बस अब और नहीं"]),
 "two_at_once_hi": ("hi", ["जी हाँ, मैं ही हूँ", "हाँ जी", "1984",
     "हाँ, एक बीमा लिया था बावन हज़ार का, लोन में से ही कटा",
     "जीवन बीमा है, और पैसे लोन में से कटे थे", "बावन हज़ार", "जी हाँ",
     "बताया ना, लोन में से कटे", "एक बार", "मेरी मर्ज़ी से", "पाँच लाख का कवर", "हाँ", "दो साल",
     "तीस दिन", "नहीं मिलेगा", "ओटीपी से"]),
 "repeat_hi": ("hi", ["क्या? फिर से बोलिए", "हाँ मैं ही बोल रहा हूँ", "समझा नहीं, फिर से बोलिए", "हाँ ठीक है",
     "क्या बोला?", "उन्नीस सौ चौरासी", "फिर से बोलिए", "हाँ बीमा लिया था", "क्या मतलब?", "बीमा है",
     "दोबारा बोलिए", "बावन हज़ार", "हाँ", "फिर से?", "लोन से कटा"]),
 "what_about_hi": ("hi", ["हाँ मैं ही हूँ, किस बारे में है?", "किस बारे में है ये कॉल?", "किस बारे में है?", "हाँ ठीक है",
     "पहले बताइए किस बारे में है", "1984", "ये किस बारे में है?", "किसलिए कॉल किया है?", "आप कौन हैं?", "हाँ बीमा लिया था",
     "किस बारे में पूछ रहे हो?", "बीमा है", "आप कहाँ से बोल रहे हैं?", "बावन हज़ार", "हाँ"]),
}
for name, (lang, turns) in CALLS.items():
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    log, outcome, end = play(turns, lang=lang)
    print(f"===== {name}: {outcome}")
    print(dump(log))
    if not callable(getattr(end, "transcript")):
        t = end.transcript
        bot = sum(len(x.text.split()) for x in t.turns if x.speaker.value == "bot")
        print(f"[seconds {call_seconds(t):.1f}; bot words {bot}; unresolved {len(end.unresolved)}]")
