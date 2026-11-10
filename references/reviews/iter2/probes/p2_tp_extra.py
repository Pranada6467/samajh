from p2_kit import play, dump
for lang, turns in [
    ("hi-en", ["main mrs ramesh bol rahi hoon", "haan", "1984"]),
    ("hi", ["मिसेज़ रमेश बोल रही हूँ", "हाँ", "1984"]),
    ("hi-en", ["Mrs. Ramesh speaking", "haan", "1984"]),
    ("hi-en", ["main Sunita bol rahi hoon", "haan", "1984"]),
    ("hi", ["मैं रमेश की मिसेज़", "हाँ", "1984"]),
    ("hi-en", ["haan ji, main hi uthati hoon inka phone", "haan", "1984"]),
    ("hi", ["जी हाँ, घर से ही बोल रही हूँ", "हाँ", "1984"]),
    ("hi-en", ["yes speaking, his secretary", "1984"]),
    ("hi", ["हाँ जी", "हाँ, वैसे मैं उनकी बहू हूँ, बोलिए", "1984"]),
    ("hi", ["हाँ जी", "हाँ", "पति जी का? चौरासी"]),
    ("hi", ["हाँ जी", "हाँ", "उनका चौरासी है"]),
    ("hi", ["हाँ जी", "हाँ", "साहब का जन्म 1984"]),
    ("hi", ["जी", "जी", "मेरे हस्बैंड 1984 के हैं"]),
    ("hi-en", ["haan ji", "haan", "unka birth year 1984 hai"]),
    ("hi-en", ["haan ji", "haan", "husband ka 1984"]),
    ("hi", ["साहब मीटिंग में हैं"]),
    ("hi", ["वो गाड़ी चला रहे हैं, बाद में कॉल करना"]),
]:
    log, outcome, _ = play(turns, lang=lang)
    print(outcome, "|", turns); print(dump(log[2:]) if outcome.startswith("open@recall") or "Udaharan" in str(log[2:]) else "")
