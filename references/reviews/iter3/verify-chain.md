<!-- Saved by the chain sub-orchestrator on 2026-11-13 from the verifier's final message, unchanged. Verified the working tree before the fix round that answers its failures 1-4; what changed afterwards is in references/pilots/P3a-report.md, "Iteration 3 (chain)". -->
## Verdict: sound with conditions, with one regression to fix before use

I am the independent Opus-high verifier and wrote none of this code. Every input below is typed text: nothing here is about speech or real callers. I made no Gnani calls. LLM spend by the client's counters was **0.0199 USD** (gpt-6-luna through `samajh/clients/llm.py`: 0.0188 + 0.0011 + 0.0000 for a cached rerun). I fixed gold before each run. Probes, all rerunnable, are in `references/reviews/iter3/probes/`: `chain_amounts.py`, `chain_amounts2.py`, `chain_cover_readback.py`, `chain_llm.py`, `chain_mutate.py`.

**Tests.** `uv run pytest tests/core tests/extract -q`: **2506 passed**. Whole suite: **29 failed, 6637 passed, 3 deselected** (162 s).
- To see which failures this package causes, I reran the 19 failing test functions in a scratch copy of a later snapshot, with HEAD's `samajh/amounts` swapped in.
- **12 fail only with the new amount parser:**
  - `test_prompts::test_a_read_back_line_parses_back…[hi, hi-en]`
  - `test_p2_call_v2` (2 cover tests)
  - `test_p2_round2::…cover_question_takes_two_readings`
  - `test_review_findings::…second_reading…`
  - `test_no_leak_and_termination` (4)
  - `test_cli::…heard_twice`
  - `test_interpret::…[bavan hazaar-None]` (an intended change; the test is out of date)
- **8 fail with HEAD's parser too.** They belong to the dialogue, server and P5 lanes (work in progress), not this package.
- The other 9 of the original 29 passed in the later snapshot.

| Claim | Result | n | What failed |
|---|---|---|---|
| A. "sorry" after the number, in a clause of its own, reads | holds only with punctuation | 4 + 7 | Punctuated: 4 of 4 read. Unpunctuated (v2.5 style): 0 of 7 read, for example `जी 41300 रुपये सॉरी नेटवर्क चला गया था` |
| A. "X, sorry, Y" is refused | holds | 4 | none |
| A. Bounds tak / up to / upto / till are refused | holds in part | 17 parser, 4 pipeline | `X तक का/की …` is read as X on any amount, not only a cover. "के अंदर" (within) is read. **The bot's own cover read-back line is now refused** (failure 1) |
| A. A count before the amount is refused; "ek baar X" reads X | holds | 8 + 2 | `41300 ek baar mein kata tha` is newly refused (cost). `har mahine 2000 aur 12 mahine` → 2,000 (not claimed) |
| A. Romanised number words are read | holds | 10 parser, 3 pipeline | 9 of 10 read; `sava lakh` refused, as designed. Pipeline 3 of 3 `clear` |
| A. Collision gate | safe, but costly | 19 | Refuses correctly 5 of 5. **Newly refuses 8 of 8 good amounts** (failure 3) |
| B. Withdrawal with a marker word is not `clear` | holds | 23 | none: 12 one-clause, 6 punctuated, 5 recall-carry |
| B. Withdrawal with no marker word | **fails** | 13 | **10 of 13 `clear` with the value the customer took back** (failure 2) |
| B. Correction away from the record: taken-back value never stated | holds | 10 | none (6 `refer`, 4 `incomplete`) |
| B. Correction toward the record | as claimed | 9 | Punctuated, not an amount: 3 of 3 `clear`. One clause: 5 of 5 `incomplete` (the stated cost). The punctuated premium correction is `incomplete` because the reply holds two amounts (true at HEAD too) |
| B. Informed replies where नहीं/nahi/no is the answer, or with an apology or filler | holds | 19 | 19 of 19 `clear`; the check said `none` 19 of 19. False incompletes: 0 of 19 |
| B. Informed recall carries the premium | holds in part | 4 | 2 of 4 `incomplete`: `…का और कुछ नहीं` and `…bas aur kuch nahi`. The parser's "not in the clause" rule refuses the figure; HEAD does the same |
| C. v2.5-style digits, no punctuation | holds | 9 parser, 2 pipeline | Only the "sorry" case above |
| Mutations | caught | 6 | 6 of 6 killed (see below) |
| The prompt pin catches a one-character docstring change | holds | 1 | none |

## Failures, ranked

**1 (high, regression: costs informed customers, not a safety failure). The cover read-back line no longer parses.** The bound guard refuses `read_back.cover_confirm` in both files: `तो उससे {amount} रुपये तक मिलता है। सही है?` (hi and hi-en; the line is unchanged since HEAD). I tested it with a scripted model on the informed BASE call plus that line and the reply "हाँ जी।":
- Tree: `understanding_gap`, cover read-back `Unclear(readback_mismatch)`.
- HEAD: `clear`.
- So every confirmed cover read-back in a case file now gives a false gap.

A related cost: the bot's re-ask "उससे कितने तक का मिलता है?" invites answers such as `साढ़े तीन लाख तक मिलता है`. That reply → `understanding_gap` (`value_not_parsed`); HEAD read it as 350,000. No test in `tests/core` or `tests/extract` catches either problem; only the dialogue tests do.

**2 (medium, safety). One-clause withdrawals with no marker word end `clear`.** Missing words include "भूल गया/bhool gaya", "kya pata", "कौन जाने" and "या कुछ और". These ended `clear` with the value the customer took back, and no check ran:
- premium: `41300 tha ya kuch aur bhool gaya`, `इकतालीस हज़ार तीन सौ था कौन जाने`, `41300 kya pata`
- carried from recall: `बीमा लिया था इकतालीस हज़ार तीन सौ का या कुछ और भूल गया`, `insurance liya tha 41300 ka kya pata`, `बीमा लिया था इकतालीस हज़ार तीन सौ का कौन जाने`
- kind: `insurance tha bhool gaya kya tha`, `बीमा था भूल गया क्या था`
- payment: `loan se kata tha kya pata`
- required: `optional tha kya pata`

Caveats:
- In the premium and carried cases the customer later said yes to the 41,300 read-back. Under the contract that yes does not rescue a withdrawn figure: the same replies with a marker word end not `clear`.
- 6 of the 10 are a "who knows" tail. The project's prompt treats doubt with no take-back word as leaning to the answer.
- When the reply offered two options, the answer model caught it (3 of 3), for example `insurance hai ya FD kya pata`.

**3 (medium, cost, regression). The collision gate refuses any romanised amount when "saath", "do", "tera" or "bara" stands before any ordinary word.** HEAD read all 8 of these; the tree refuses all 8:
- `loan ke saath ek insurance liya tha 41300 ka`
- `loan ke sath insurance tha 41,300 ka`
- `insurance ke saath 41300 kata`
- `mere saath 41300 ka dhokha hua`
- `tera kya 41300 hi diye the`
- `bara amount tha 41300`
- `unhone kaha de do 41300`
- `41300 saath mein diye`

"लोन के साथ" is how the bot itself opens recall.

**4 (low to medium, parser).**
- `चालीस हज़ार तक का था`, `chalis hazaar tak ka tha` and `40000 tak ki premium thi` → 40,000: a premium bound read as the figure. In the pipeline the model's span saved the one case I ran.
- `चालीस हज़ार के अंदर` → 40,000.
- Unpunctuated "sorry" still refuses an informed figure (0 of 7), so the "sorry" fix does little on v2.5 figure turns.

**Mutations** (scratch copy only; tests in `tests/core` + `tests/extract` that fail):
- Marker check off: 17
- Carry without a check: **1**
- One-clause correction allowed to stand: 5
- "sorry" never refuses: 5
- Bound guard off: 8
- Collision gate off: 4

**Prompt pin.** Changing "value." to "value!" in the `ChangeReply` docstring (scratch copy) failed 2 of 5 pin tests (wire schemas, change-check schema). After restoring, 5 of 5 passed; I cleared `__pycache__`. During my run someone else added a 3-line comment above `ChangeReply` in the repo's `_wire.py` (08:27). Comments are not sent to the model and the pin still passes.

**Tree state.** I edited nothing in the repo outside `references/reviews/iter3/probes/`. `git diff --stat` changed during my run because other lanes were editing (ORCHESTRATION.md, USER-GUIDE.md, samajh/dialogue, the `_wire.py` comment), not because of me.

## Not checked
- Speech, real callers, Prisma's punctuation rate.
- Tamil and Kannada; models other than gpt-6-luna.
- Whether the live P2 dialogue reads a premium back after a withdrawal.
- The frozen sets: data/scenarios, data/amounts_v2 and data/p5 not touched.
- No native speaker judged my gold. The builders' probe files I read only afterwards, for coverage: none of my failure inputs are in them.

## Wording
**May say:**
- "On 23 typed withdrawals that hold a marker word (one-clause, punctuated or carried from recall), none ended `clear`."
- "On 19 typed informed replies where नहीं/nahi/no is the answer, or with an apology or filler, 19 ended `clear`."
- "On 10 typed corrections away from the record, the taken-back value was never the stated answer."
- "On 9 typed bounds (tak, up to, upto, till) the parser read no figure."
- "On 10 romanised Hindi amounts the parser read 9 correctly and refused the fraction word."
- "6 of 6 targeted mutations were caught."

**May not say:**
- "A one-clause withdrawal is never `clear`": 10 of 13 with no marker word were.
- "An apology no longer blocks a figure": it still does in unpunctuated text, 0 of 7 read.
- "Bounds are refused": "X तक का" is read as X (3 of 3), and the cover read-back line is now refused.
- "Romanised Hinglish amounts are read": 8 of 8 common replies containing "saath", "do" or "tera" are newly refused.
- "No regression": informed cover read-backs now end `understanding_gap`, and 12 dialogue tests fail because of this package.
- Any claim about speech, real callers, or a pooled rate.

## Fix before use
1. Exempt the read-back line from the bound guard, or reword the line; add a core test on the real line.
2. Add the missing take-back words to the marker list: भूल गया, bhool, kya pata, कौन जाने, ya kuch aur.
3. Keep a collision word as a number only when it stands right before a number or unit.
4. Limit the "X तक का" exemption to cover answers.

---

<!-- Recheck addendum, saved by the chain sub-orchestrator on 2026-11-13 from the same verifier's second message, unchanged. Run after the fix round (bounds marked, collision gate narrowed, "sorry", take-back tail rule). The four items under "Fix" were then fixed once by the builders and NOT re-verified (references/pilots/P3a-report.md, "Iteration 3 (chain)"). -->
## Addendum: recheck of the r2 fixes (chain verifier, one round)

**Verdict: holds with conditions.** The cover read-back regression, the premium bounds, the collision cost and the unpunctuated "sorry" are fixed on new inputs. Two problems remain:
- **Unsafe:** "या फिर कुछ और / ya phir kuch aur" is not one of the take-back tails, so a withdrawal ending in it still comes back `clear`.
- **New, unsafe:** a romanised count before an ordinary noun ("do kisht mein") is now read as an amount.

The take-back tail rule also has a high cost: 9 of 13 informed one-clause replies became `incomplete`.

All inputs are typed text and new (none of my earlier failure sentences), with gold fixed before each run. No Gnani calls. LLM spend this round was **0.0117 USD** by the client counter, **0.0316 USD** for the whole engagement. New probes: `references/reviews/iter3/probes/chain_r2_amounts.py` and `chain_r2_llm.py`.

**Tests.**
- `uv run pytest tests/core tests/extract -q`: **2588 passed**.
- Whole suite: **4 failed, 7238 passed, 3 deselected**.
  - 3 failures are the dialogue lane's stale "bavan hazaar" examples, as expected: `test_cli::…heard_twice`, `test_interpret::…[bavan hazaar-None]`, `test_review_findings::…second_reading…`.
  - 1 is P5 lane work in progress: `test_p5_player::…line_key_is_mapped` (new dialogue line keys not mapped).
  - None comes from this package. The 12 tests this package broke last round now pass.

| Claim | Result | n | What failed |
|---|---|---|---|
| Cover read-back on the real `read_back.cover_confirm` line (hi, hi-en) ends `clear` | holds | 3 | none |
| A bounded cover answer is accepted | holds | 4 real model + 9 parser | none (the parser marks `bound=True` in 9 of 9) |
| A bounded premium is never `clear` and never the stated premium (carried from recall included) | holds | 7 | none |
| Romanised words in ordinary use (saath/sath/do/tera/bara/das) read the amount | holds | 8 real model + 10 parser | Parser cost: `bees hazaar sath mein processing` is refused |
| Count + product noun is refused | holds | 3 real model + 3 parser | none |
| Other romanised counts | **fails** | 5 parser | A romanised count before a non-product noun now reads the figure: `do kisht mein 41300` → 41,300; also `do EMI mein 41300`, `teen kishton mein 41300`, `do hisson mein 41300 diye`. The Devanagari `दो किस्तों में 41300` is still refused |
| An unpunctuated "sorry" after the figure reads | holds | 4 real model + 2 parser | Still refused: `sorry 41300` (by design) and `इकतालीस हज़ार तीन सौ सॉरी आवाज़ नहीं आ रही थी` (the parser's "नहीं in the clause" rule) |
| One-clause withdrawal with a who-knows or forgot tail is not `clear` | holds in part | 13 | **2 of 13 `clear` with the value the customer took back** (check said `none`): `इकतालीस हज़ार तीन सौ कहा था या फिर कुछ और` (premium) and `policy thi 41300 ki ya phir kuch aur` (carried from recall). "या फिर कुछ और" is not in `_TAILS` |
| Punctuated "…, कौन जाने।" (rests on the check) | holds | 5 | none |
| Informed one-clause reply, tail about another field or about exactness (cost) | **high cost** | 13 | **9 of 13 false `incomplete`**, listed below |

The 9 false incompletes:
- The tail is about another field (7): `बीमा है पता नहीं कितने का`, `बीमा है रकम याद नहीं`, `insurance hai amount yaad nahi`, `लोन से कटा था कितना कटा याद नहीं`, `loan se kata tha kab kata yaad nahi`, `ज़रूरी नहीं था बाकी मुझे कुछ नहीं पता`, `nahi zaroori nahi tha baaki pata nahi`.
- A word that looks like a tail (1): `बीमा है जो भूल से ले लिया था` ("by mistake", not "forgot").
- Exactness (1): `loan se kata tha theek se yaad nahi`. The romanised "se" is missing from `_EXACTNESS`, so "theek se yaad nahi" still fires the rule. The Devanagari "ठीक से याद नहीं" does not.
- Ended `clear` (4): `mujhe pata hai insurance hai`, `हाँ याद है बीमा है`, `बीमा है पक्का नहीं पता`, `zaroori nahi tha bilkul pakka`.

**Not checked:** speech; Tamil and Kannada; mutations of the r2 code. Inferred but not run: the Devanagari "से" in `_EXACTNESS` would also exempt a withdrawal such as "लोन से या कैश से याद नहीं".

## Wording (updates)
**May say (add):**
- "On 3 typed calls, a confirmed cover read-back on the bot's real line ended `clear`."
- "On 7 typed bounded premiums, none ended `clear` and the bound was never taken as the premium."
- "On 8 typed romanised replies using saath, do, tera, bara or das as ordinary words, the amount was read in 8 of 8."
- "On 5 typed punctuated 'who knows' withdrawals, none ended `clear`."

**May not say:**
- "A one-clause withdrawal is never `clear`": 2 of 13 with "ya phir kuch aur" were.
- "Counts before an amount are refused": 4 of 4 romanised counts before a non-product noun are read.
- "Informed customers are rarely made incomplete": 9 of 13 informed one-clause replies with a tail about another field or about exactness ended `incomplete`.
- Any claim about speech, real callers, or a pooled rate.

**Fix:**
1. Add "या फिर कुछ और / ya phir kuch aur" (and similar) to `_TAILS`.
2. Add the romanised "se" to `_EXACTNESS`.
3. Make a romanised count word before any noun count, as Devanagari "दो" does.
4. Decide whether a tail about another field ("कितने का", "amount", "kab") should fire the rule at all.
