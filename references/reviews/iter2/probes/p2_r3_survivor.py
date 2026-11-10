from samajh.dialogue import start, step, EndOfCall, RuleInterpreter
from samajh.types import Language, LoanRecord
import samajh
r=LoanRecord.model_validate_json(open("tests/dialogue/fixtures/record_gold_loan.json").read())
def play(ts):
    st,s=start(r,Language("hi"),lender_name="X")
    for t in ts:
        st,s=step(st,t,interpreter=RuleInterpreter())
        if isinstance(s,EndOfCall): return "END "+s.outcome.value
    return type(st.position).__name__+str([l.key for l in s.lines])
print(samajh.__file__.split("scratchpad/")[-1])
for ts in (["हाँ जी","1984 या 1985"],["हाँ जी","1984, नहीं 1985"],["हाँ जी","चौरासी पचासी"],
           ["हाँ जी","1984","हाँ","मैं उनका बेटा बोल रहा हूँ, पापा बाहर चले गए","हाँ, मैं उनका बेटा, बोलो"],
           ["हाँ जी","1984","हाँ","रुको, मैं उनकी वाइफ हूँ, उन्होंने फोन दे दिया","हाँ जी, मैं उनकी वाइफ"]):
    print(ts[-1],"->",play(ts))
