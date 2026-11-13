"""Write references/pilots/P2-lines-for-review.md: every bot line for a fluent reviewer to mark up.

    uv run python tests/dialogue/probes/export_lines.py

Hindi and Hinglish come from data/prompts/; the plain-English meaning and the moment each line is
said are kept here, one per key (tests/dialogue/test_export_lines.py checks none is missing).
"""

from __future__ import annotations

from pathlib import Path

from samajh.dialogue import LINES, load_prompts
from samajh.types import Language

OUT = Path(__file__).resolve().parents[3] / "references" / "pilots" / "P2-lines-for-review.md"

# key -> (plain English meaning, when it is said)
MEANINGS: dict[str, tuple[str, str]] = {
    "right_party.ask": ("Hello, are you {first_name}?", "First line of every call."),
    "right_party.reask": (
        "This is an automated customer-care call for {first_name}. Are you {first_name} yourself?",
        (
            'Once, when the first reply is not an explicit first-person claim ("haan boliye", "ji", "hello", silence). '
            "With no second check (P8 default) it is the direct question: a yes to it passes."
        ),
    ),
    "right_party.who_check": (
        "Sorry, I need to be sure who I am speaking with. Are you {first_name} yourself, or someone else in their place?",
        (
            "Mid-call, after a sign that someone else may have the phone (iteration 3). Resumes only on an explicit "
            "'it is me'; a bare yes, or anything else, ends the call as a wrong party."
        ),
    ),
    "end.third_party": (
        "We will talk to {first_name} later. Thank you.",
        "Ends the call when the speaker is someone else, hands the call to someone else, or never claims to be the borrower.",
    ),
    "end.neutral": (
        "No problem. Sorry to have troubled you. Goodbye.",
        "Ends the call when there is no clear yes to going ahead, after one re-ask.",
    ),
    "disclosure.who": (
        "I am a computer-run voice from {lender} customer care, not a person.",
        "After the borrower claims to be themselves (opening line 1 of 4).",
    ),
    "disclosure.not_sales": ("This is not a sales call; it is a feedback call.", "Opening line 2 of 4."),
    "disclosure.recording": (
        "The conversation is being recorded; the details are in {lender}'s written notice.",
        "Opening line 3 of 4.",
    ),
    "disclosure.go_ahead": (
        "Can we talk for two or three minutes?",
        "Opening line 4 of 4; the customer can say no.",
    ),
    "disclosure.reask": (
        "This is a feedback call from {lender}, not a sales call. Can we talk for two or three minutes now? Just say yes or no.",
        "Once, after an unclear reply to the go-ahead question.",
    ),
    "disclosure.never_ask": (
        "We will never ask you for an OTP, PIN, password or account number.",
        "Just before the birth-year question; with no second check (P8), in the disclosure after the right-party check.",
    ),
    "disclosure.rights": (
        "If you want to stop, or to talk to a person, just say so at any time.",
        "With the first mention of the loan, before the first question about it.",
    ),
    "verify.before_loan": (
        "This is a feedback call from {lender} customer care; what it is about we will tell you once your identity is confirmed. If in doubt, hang up and ask {lender} customer care yourself. We never ask for an OTP or PIN.",
        "When the customer asks who is calling, what this is about or whether it is genuine, after the name claim and before the loan is named (at most twice); then the question again.",
    ),
    "verify.after_loan": (
        "This call is a few short questions about the loan you recently took from {lender}. If in doubt, hang up and call the customer-care number printed on your loan papers. We never ask for an OTP or PIN.",
        "The same, after the loan is named; then the question again.",
    ),
    "second_check.ask": (
        "To confirm, please tell me your year of birth. Just the year.",
        "After the go-ahead.",
    ),
    "second_check.reask": (
        "Once more, just your year of birth please.",
        "Once, whether the year was unclear or did not match (it says neither).",
    ),
    "end.check_failed": (
        "Sorry, we could not confirm this just now, so we will end the call here. If you need to, you can speak to {lender} customer care. Thank you.",
        "Ends the call after a second wrong or unclear year. The loan is never mentioned.",
    ),
    "context.loan": (
        "Thank you. A few questions about the loan you recently took from {lender}.",
        "After the year matches: the first time the loan is named.",
    ),
    "open_recall.ask": (
        "Did you take anything else along with the loan? If yes, what, and for how much?",
        "After the loan line: the key question, before any product is named.",
    ),
    "open_recall.reask": (
        "I mean, was anything else part of the loan when you took it? Tell me whatever you remember.",
        "Once, after an unclear answer to the recall question.",
    ),
    "open_recall.nothing": (
        "I see. When you took the loan, did anyone talk to you about anything other than the loan?",
        "Once, when the customer says they took nothing, does not know, or stays unclear. Never repeated.",
    ),
    "teach_back.intro": (
        "All right, a few short questions about that.",
        "Before the product questions, one product on record, only after the customer has named or affirmed something.",
    ),
    "teach_back.intro_nth": (
        "I see. If you also took anything else with the loan, there are now a few short questions about that.",
        "Before the questions on the second and each later product, when the record has several products.",
    ),
    "kind.ask": ("What is it? Tell me in your own words.", "Product question 1."),
    "kind.reask": (
        "I mean, what would you call the thing you took with the loan?",
        "Once, after an unclear answer.",
    ),
    "kind.ask_named": (
        "What you mentioned, explain it a little: what is it, and what is it for?",
        "Product question 1 instead of kind.ask, when the open-recall reply named something (iteration 3, gain 8).",
    ),
    "ack.neutral": (
        "Ji. (a neutral acknowledgement)",
        (
            "Before every second product question (questions 2, 4, 6, 8, 10), by position only; never on a re-ask, "
            "a stop check, a who-check, a read-back or an end. Hindi and Hinglish only (iteration 3, gain 8)."
        ),
    ),
    "premium.ask": ("How much did you pay for it?", "Product question 2."),
    "premium.reask": (
        "I mean, how much did it cost? Tell me as much as you remember.",
        "Once, after an unclear answer with no figure.",
    ),
    "premium.say_again": (
        "Please tell me the amount once more so it is noted correctly. How much did you pay?",
        "Once per product, when the two speech readings of the amount disagree or only one heard a figure.",
    ),
    "payment_source.ask": (
        "Where did that money come from, and how was it paid?",
        "Product question 3, after the premium read-back.",
    ),
    "payment_source.reask": ("I mean, how was it paid for?", "Once, after an unclear answer."),
    "payment_frequency.ask": (
        "Was this money to be paid only once, or will you have to pay again?",
        "Product question 4.",
    ),
    "payment_frequency.reask": (
        "I mean, did you pay for it once, or do you have to pay again and again?",
        "Once, after an unclear answer or a bare yes/no.",
    ),
    "required_for_loan.ask": (
        "What were you told: is taking this necessary for the loan, or is it your choice?",
        "Product question 5.",
    ),
    "required_for_loan.reask": (
        "I mean, were you told you had to take it, or were you told it was up to you?",
        "Once, after an unclear answer or a bare yes/no.",
    ),
    "provider_choice.ask": (
        "Were you told whether you could get this from somewhere else as well?",
        "Product question 6, skipped when the customer said it was their own choice.",
    ),
    "provider_choice.reask": (
        "I mean, did anyone say you could get this from another place too?",
        "Once, after an unclear answer.",
    ),
    "cover.ask": (
        "What do you get from it? If an amount goes with it, tell me that too.",
        "Product question 7.",
    ),
    "cover.reask": ("I mean, what is it for? Tell me what you understood.", "Once, after an unclear answer."),
    "term.ask": ("How long is it for?", "Product question 8."),
    "term.reask": (
        "I mean, until when does it run? Tell me in months or years.",
        "Once, after an unclear answer.",
    ),
    "cancel_window.ask": ("What were you told about stopping or cancelling it?", "Product question 9."),
    "cancel_window.reask": (
        "I mean, did anyone tell you anything about stopping or cancelling it? Tell me whatever you remember.",
        "Once, after an unclear answer.",
    ),
    "features.ask": (
        "If you wanted the money you put in back, what would happen? What do you think?",
        "Product question 10.",
    ),
    "features.reask": (
        "I mean, what happens to the money put into it later on? Tell me what you know.",
        "Once, after an unclear answer.",
    ),
    "consent.ask": (
        "When you took the loan, what things did you say yes to? And in what way did you give that yes?",
        "After the last product (or straight after the recall follow-up when the customer took nothing).",
    ),
    "consent.reask": (
        "I mean, what were you asked to say yes to, and in what way did you give that yes?",
        "Once, after an unclear answer.",
    ),
    "read_back.confirm": (
        "So you paid {amount_words} rupees for it. Is that right?",
        "Straight after the premium answer (or after the kind question, when the customer already gave the figure in open recall): the customer's own figure, in words only.",
    ),
    "read_back.confirm_about": (
        "So you paid about {amount_words} rupees for it. Is that right?",
        'Instead, when the customer gave the amount as "about X" or "X to Y".',
    ),
    "read_back.cover_confirm": (
        "So you get up to {amount_words} rupees from it. Is that right?",
        "After the cover answer, only when the customer stated a cover amount.",
    ),
    "read_back.reconfirm": (
        "Once more: {amount_words} rupees. Is that right or not?",
        "After an unclear reply to a read-back, or when the two readings of the reply disagree (yes and no).",
    ),
    "read_back.restate": (
        "All right. So what is the right amount?",
        "When the customer says a read-back is wrong without giving another figure.",
    ),
    "bridge.moving_on": (
        "No problem, let's move on.",
        "Before the next question when an answer stayed unclear after one re-ask.",
    ),
    "stop_check.decline": (
        "Shall I go on?",
        "After a weak sign the customer wants to stop, or once when the classifier failed on a free reply. Yes goes back to the question, no ends the call.",
    ),
    "stop_check.human": (
        "Would you like to talk to someone from our team?",
        "After a weak sign the customer wants a person.",
    ),
    "callback.when": (
        "All right. When should we call you?",
        "When the customer asks for a later call without saying when. Any reply ends the call; it is kept as said.",
    ),
    "end.declined": (
        "All right, no problem. Thank you for your time. Goodbye.",
        "Ends the call after a refusal.",
    ),
    "end.human": (
        "All right, that is noted. Someone from our team will contact you. Thank you, goodbye.",
        "Ends the call after a request for a person.",
    ),
    "end.call_back": (
        "All right, we will try to call later. Thank you, goodbye.",
        'Ends the call after a request for a later call ("I am driving", "call in the evening").',
    ),
    "end.language": (
        "All right, we will try to call again in your language. Thank you, goodbye.",
        "Ends the call when the customer asks for another language (no live switch).",
    ),
    "end.no_response": (
        "I cannot hear you. We will try again later. Goodbye.",
        "Ends the call after two silent turns in a row.",
    ),
    "close.thanks": ("Thank you for your time and your answers.", "Close of a completed call."),
    "close.may_call_back": (
        "If needed, our team may call you again.",
        "Close, only when something was left unresolved.",
    ),
    "close.verify": (
        "If you have any doubt, you can ask on the {lender} customer-care number printed on your loan papers.",
        "Close of a completed call.",
    ),
    "close.bye": ("Goodbye.", "Last line of a completed call."),
    "purpose.before_confirm": (
        "This is a customer-care feedback call; the rest once we are sure we are speaking to the right person.",
        "When someone asks who is calling or what it is about before claiming to be the borrower (at most twice); no lender, no loan. Then the re-ask.",
    ),
    "verify.short": (
        "If in doubt, hang up and ask {lender} customer care yourself.",
        "With the birth-year question (claim path); with no second check, in the disclosure. Dropped when the lender turns the call-back line off.",
    ),
    "cover.say_again": (
        "Please tell me that amount once more so it is noted correctly. Up to how much do you get from it?",
        "Once per product, when the two speech readings of the cover amount disagree or only one heard a figure.",
    ),
    "stop_check.disengaged": (
        "Shall I ask on, or stop here?",
        'Once a call, after two unusable replies or three "I don\'t know"s in a row.',
    ),
    "end.do_not_call": (
        "All right, we have noted not to call you again. Thank you, goodbye.",
        "Ends the call when the customer asks not to be called again or to remove the number.",
    ),
    "end.written": (
        "All right, we have noted that you want this in writing. Thank you, goodbye.",
        "Ends the call when the customer asks for this in writing.",
    ),
}


# Lines added or reworded in review round 2 (after the iteration-2 verifier), marked in the export.
ROUND2_NEW = frozenset({"purpose.before_confirm", "verify.short", "cover.say_again", "stop_check.disengaged",
                        "end.do_not_call", "end.written"})  # fmt: skip
ROUND2_CHANGED = frozenset({
    "right_party.ask", "end.third_party", "disclosure.who", "disclosure.recording", "disclosure.reask",
    "verify.before_loan", "verify.after_loan", "context.loan", "consent.ask", "consent.reask", "read_back.confirm",
    "read_back.cover_confirm", "read_back.reconfirm", "stop_check.decline", "stop_check.human", "end.human",
})  # fmt: skip
# Lines reworded in round 3; the English meaning above translates the current text.
ROUND3_CHANGED = frozenset({"verify.before_loan", "teach_back.intro_nth", "cancel_window.reask"})
# Lines added in iteration 3 (P8 and the round 4 follow-ups).
ITER3_NEW = frozenset({"right_party.who_check", "ack.neutral", "kind.ask_named"})
# Lines reworded in the iteration 3 fix round: gender-neutral ("क्या आप ख़ुद {first_name} जी हैं?", no "बोल रहे हैं").
ITER3_CHANGED = frozenset({"right_party.reask"})


def _mark(key: str) -> str:
    return (
        " **(new, iteration 3; gender-neutral in the fix round)**"
        if key in ITER3_NEW and key == "right_party.who_check"
        else " **(new, iteration 3)**"
        if key in ITER3_NEW
        else " **(changed, iteration 3 fix round: gender-neutral)**"
        if key in ITER3_CHANGED
        else " **(changed, round 3)**"
        if key in ROUND3_CHANGED
        else " **(new, round 2)**"
        if key in ROUND2_NEW
        else " **(changed, round 2)**"
        if key in ROUND2_CHANGED
        else ""
    )


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main() -> None:
    hi, he = load_prompts(Language.hi), load_prompts(Language.hi_en)
    rows = [
        "# P2 bot lines for review (Hindi and Hinglish)",
        "",
        "Generated by `uv run python tests/dialogue/probes/export_lines.py` from `data/prompts/hi.toml` and",
        "`data/prompts/hi-en.toml`. Written by the build agents; **no fluent human has reviewed any line**.",
        "Please mark up anything unnatural, ambiguous, leading or hard to hear on a phone. Slots in braces",
        "are filled at call time: the first name and lender from the record, `{amount_words}` and",
        "`{amount_digits}` only ever with the figure the customer said. Tamil and Kannada are not listed:",
        "they are experimental and not human-reviewed. Lines are in the order the call can say them.",
        "",
        "**Round 2** (after the iteration-2 verifier): lines marked *new* or *changed* moved; the verifier's",
        "eight wording changes are adopted, and read-backs say the figure in words only.",
        "**Round 3**: lines marked *changed, round 3* were reworded; their English meaning is of the new text.",
        "",
        "| Key | Hindi | Hinglish | Plain English meaning | When it is said |",
        "|---|---|---|---|---|",
    ]
    for key in LINES:
        meaning, when = MEANINGS[key]
        rows.append(
            f"| `{key}`{_mark(key)} | {_cell(hi.templates[key])} | {_cell(he.templates[key])} | {_cell(meaning)} | {_cell(when)} |"
        )
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{len(LINES)} lines written to {OUT}")


if __name__ == "__main__":
    main()
