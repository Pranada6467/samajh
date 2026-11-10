"""`has_doubt_word` and `is_loan_tenure`: markers on answers that carry no number."""

import pytest

from samajh.amounts import has_doubt_word, is_loan_tenure


@pytest.mark.parametrize(
    "text",
    [
        "वापस तो नहीं मिलेगा शायद, बीमा है ना",
        "लगता है बीमा है",
        "मुझे लग रहा है कि वापस मिलेगा",
        "करीब पचास हज़ार",
        "क़रीब पचास हज़ार",
        "लगभग उतना ही",
        "पचास हज़ार के आसपास",
        "आस पास पचास हज़ार",
        "तकरीबन तीन साल",
        "Maybe it is insurance",
        "I think it's an FD",
        "probably three years",
        "around 50,000",
        "about fifty thousand",
        "shayad bima hai",
        "kareeb 50 hazaar",
        "lagbhag teen saal",
        "aaspaas pachas hazaar",
        "mujhe lagta hai FD hai",
    ],
)
def test_a_word_of_doubt_or_approximation_is_found(text):
    assert has_doubt_word(text)


@pytest.mark.parametrize(
    "text",
    ["बीमा है", "पचास हज़ार रुपये", "हाँ, वापस मिलेगा", "it is insurance", "FD hai", "", "लगता नहीं", "thinking"],
)
def test_a_plain_answer_has_no_doubt_word(text):
    assert not has_doubt_word(text)


@pytest.mark.parametrize(
    "text",
    [
        "जब तक लोन चलेगा",
        "जब तक लोन है",
        "लोन जितना ही",
        "लोन की अवधि तक",
        "लोन खत्म होने तक",
        "जब तक लोन चलेगा तब तक",
        "जितने दिन लोन चलेगा",
        "लोन के बराबर",
        "jab tak loan chalega",
        "jab tak loan hai tab tak",
        "loan jitna hi",
        "loan khatam hone tak",
        "till the loan is over",
        "until the loan ends",
        "same as the loan tenure",
        "as long as the loan runs",
        "Till the loan is repaid.",
    ],
)
def test_a_duration_tied_to_the_loan_is_a_loan_tenure(text):
    assert is_loan_tenure(text)


@pytest.mark.parametrize(
    "text",
    [
        "लोन के साथ, तीन साल",
        "जब तक लोन चलेगा, 5 साल",
        "जब तक लोन चलेगा तब तक नहीं",
        "लोन जितना नहीं",
        "not as long as the loan",
        "तीन साल",
        "पता नहीं",
        "लोन लिया था",
        "लोन से कटा",
        "जब तक मैं चाहूँ",
        "loan ke saath",
        "",
    ],
)
def test_a_number_a_negator_or_no_link_to_the_loan_is_not_a_loan_tenure(text):
    assert not is_loan_tenure(text)
