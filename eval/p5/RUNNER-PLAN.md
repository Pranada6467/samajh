# P5 runner plan

**No code here calls Gnani and nothing has been run.** Part 1 is the P5-prep sub-orchestrator's decisions (2026-11-10). Part 2 is the read-only research they rest on, saved as the research agent returned it: file and line references are to the working tree of that day, and the dialogue's line keys are a moving target while the P2 fix round is open. Contract: `references/pilots/P5-contract.md`. Data: `data/p5/` (read its `README.md` first).

## Part 0. What changed after this plan was written (checked 2026-11-10 21:47 IST)

Read this before Part 1; where the two differ, Part 0 wins. A Sonnet research agent checked each item against `samajh/server`, the P1b, P1c and P3a reports and the Gnani ledger, without opening `samajh/dialogue` or `data/prompts`. Part 2's line numbers are from an older tree.

1. **The readings order is decided.** On a turn that asks for two readings (a figure or a read-back) the dialogue gets Prisma v2.5 first when it returned text in time, else v3.0 (`samajh_dialogue.readings`; `references/pilots/P1b-report.md` section 1). Put the case file's `models.dialogue_reads_first` and the git commit in the run manifest; change neither between stages. Part 2's "v3.0 first" is false, and Part 1's "open decision" is settled.
2. **Registering the closed arm.** The stub dialogue is no longer on a default server. Another dialogue is registered only through `create_app(dialogues=..., records=..., profile="patient", batch=..., state=...)`, and a launcher that passes `dialogues` must build the Samajh factory (`samajh_factory(records, load_settings())`) and pass `records` itself. The `Dialogue` protocol now declares `prefetch`: give the closed class a no-op. `replay --dialogue` accepts only `samajh` and `stub`, so name the closed arm with `"dialogue": "closed"` in `call.json` and run replay with `--url` and `--no-case`. Part 2's "`--dialogue closed`" is false.
3. **Batch is set per app, not per call.** "Batch on 12 calls, off elsewhere" needs two launcher modes (or two launches): one with the real Batch client for the 12, one with the null client. Not checked further.
4. **Records, not the loan book.** The phone can now call a loan drawn from the loan book. Do not use that for P5: a loan allows 3 attempts and a completed call ends them, P5 needs up to 6 calls per customer, the closed arm has no loan link, and every loan-book call enters the reviewer queue and the half-yearly report. Keep `SAMAJH_RECORDS_DIR=$PWD/data/p5/records` (the 60 records still load beside the 4 packaged ones: 64, no duplicate id or label).
5. **Own state directory.** Start the launcher with its own `--state` (sessions move there; the Gnani lock, cache and ledger stay shared). Never run `python -m samajh.ops ingest` over it: with `SAMAJH_RECORDS_DIR` set, P5 sessions would be brought into the batch as calls outside the sample.
6. **New fields for the scorer.** Each customer turn has `degraded`; the case file has `degraded_turns` and `speaker_confirmed` (true after the birth-year check). Count degraded turns by arm and level, keep those calls, and expect `speaker_confirmed` false on every third-party call. In the session JSON `acted_on` is a role (primary or second); in the case file it is a model name.
7. **LLM cost.** The extractor now makes a change check on each reply of two or more clauses: about USD 0.0021 per open call with nothing cached, not 0.0015 (`references/pilots/P3a-report.md`, fix round 3: 0.303 USD per 144 calls). For the whole plan (418 open calls through the extractor: 276 on text, 4 smoke, 46 and 92 on voice) that is about USD 0.9 with nothing shared between levels, and at most about USD 0.3 more for the turn classifier: about USD 1, range 0.4 to 1.5 (the researcher's estimate; P5 replies are longer than the frozen set's). The client's cap is USD 1.0 per process: set `SAMAJH_LLM_USD_CAP` to at least 2 for each stage, or a silent cap makes turns degraded.
8. **Credits.** The ledger sums to 310.79 estimated credits (21:45 IST), so about 689 remain of the 1,000 cap, not 710. The fixed lines were re-voiced for the current wording (92 clips, 12.6 estimated credits, `P1c-report.md` section 3) and are cache hits now; if the wording review or the P2 fix round changes lines, about 13 more are needed before stage 2, outside the 265. The 18 + 4 credits for name and lender lines were estimated under the older wording: measure with `prompts build --record ... --dry-run` on one and on two records.
9. **A smaller run is on the table.** The iteration 2 judge (`references/reviews/iter2/judge.md`, item 9 and decision (f)) proposes: stage 1 as planned, then voice on the open arm only. In this plan's terms that is stage 2 without the 46 closed calls: 60 open calls at level 0, about 94 + 18 + 4 = 116 estimated credits with Batch off everywhere, about 135 with the Batch subset, hard stop 160. The closed arm is then measured on text only, and the judge's earlier "at least 120 voiced calls" is not met. The coordinator decides; nothing in the data changes either way.
10. **Run the mapping-coverage test first.** The dialogue's line keys changed in P2 rounds 2 and 3 and are changing again. Matters `references/pilots/P2-contract.md` section 5 names that have no topic of their own in `data/p5/topics.json`: a request to restate the cover figure and a right cover read-back (Part 1 already reuses `benefit_read_back_wrong` and `figure_read_back_right`), the checks after the loan is named (`verify.after_loan`, `close.verify`), the follow-up position after recall, and a language request made by the bot's own line (`end.language`). No topic is added: the bank is frozen. Each such line gets a mapped existing topic or `not_understood`, is logged, and is counted in the report.

11. **Outside the 300 stop** (moved here from the contract to keep it to two pages): re-voicing the bot's lines after a wording change (about 13, item 8); the iteration 1 judge's run of the frozen scenario set on the voice path (72 calls; the coordinator's decision; not planned here); his perturbation suite (not prepared: the `again` replies and the open call's terse `go_along` replies give a small part of it on text). Batch adds about 1.6 estimated credits per open call, which is why it runs on 12 calls only.
12. **Stage tolerance against the stop (round 2 verifier).** Part 1 says to stop and ask if a stage's ledger change exceeds 1.3 times its estimate. Stage 2 at 1.3 times is 273, which leaves 27 for stage 3 under the 300 stop, against about 55 planned: if stage 2 ends above about 245, ask the coordinator before stage 3 instead of starting it.
13. **What the levels may show (round 2 verifier; contract sections 1 and 8).** The two arms are compared only at level 0. Above it, report each arm on its own: the end states of open calls (`incomplete`, ended early, wrongly `clear`, wrongly `refer`) and the closed `confirmed` count. The scorer must not print an open-minus-closed difference above level 0.

## Part 1. Decisions

**What exists and is used as it is:** records outside the package load through `SAMAJH_RECORDS_DIR` (the server and `prompts build --record`); one reply is voiced by the Gnani client's `tts` (cached by text, voice, model, language, rate); `samajh.server.replay` already carries a whole call through the HTTP routes to a case file and resumes after a crash; `samajh.evalkit.score` has `wilson` and `mcnemar_exact`; the client's cache makes a rerun free and `GNANI_CREDIT_CAP` is the ceiling.

**What is missing (build order; each is small, all under `eval/p5/` except the closed dialogue):**
1. `bank.py`: load `customers.jsonl`, `replies.jsonl`, `gold.jsonl`; the disposition draw of `data/p5/topics.json`; the voice rule below; a check of every hash in `data/p5/FROZEN.json`, failing closed.
2. `player.py`: the reply-bank player (Part 2, section 2, item 1): the replay loop with the reply chosen at run time from the bot's last line. A test that every key in the dialogue's `LINES` is mapped or listed as "no reply", so a changed line key fails the test and not the run.
3. `text_run.py`: the same player on text (`start`/`step`, then `run_text`), no audio. This is stage 1 and the dry run of every later stage.
4. The closed dialogue (`samajh/server/closed_dialogue.py`, or a launcher that registers it; it needs the coordinator's leave to touch `samajh/server`): the Samajh opening, then the ten statements of `data/p5/closed_statements.jsonl`, each reply read as yes, no or other by the dialogue's own yes/no reader; outcome `closed_confirmed` or `closed_not_confirmed` in the last utterance's tags.
5. `serve.py`: a launcher that starts the server with the P5 records, the closed dialogue and, for calls outside the Batch subset, a null Batch client (the tier does not depend on Batch; a skipped Batch must not mark the case failed).
6. `score.py`: the tables of contract section 4 from the case files, the session logs (third-party leak check: a `context.loan` line or any later step said) and gold.
7. `run.py`: the stage driver with the ledger reading before and after each stage and the stop rule.

**Rules fixed now, before any audio:**
- *Topic to line:* the mapping in Part 2, section 2, item 1. Gaps settled: a right read-back of the benefit figure uses `figure_read_back_right`; a request to restate the benefit figure uses `benefit_read_back_wrong`; `cover.say_again` uses `what_it_gives` (`again`); `stop_check.human` uses `want_a_person`; any unmapped line uses `not_understood` (the verifier found three line keys the P2 fix round added with no mapping: `bridge.moving_on`, `end.do_not_call`, `end.written`; the mapping test must settle each before a run); `silence_prompt` is used only after a turn whose transcript came back empty. A line the player cannot map is logged and counted, never skipped.
- *Two topics are not what the bot asks (verifier):* `anything_else` invites the customer to name an amount that was taken, which the bot's follow-up to "I took nothing" does not; and the two `_wrong` read-back replies were written under the instruction to say the figure again. Both are listed as limits in `data/p5/README.md`; the read-back replies fire only after a mishearing, so never on the text path.
- *Read-back right or wrong:* compare the figure the bot read back (from the call state, or parsed from the line) with the figure in the customer's own reply text that was voiced for that turn (parsed by `samajh.amounts`). Equal: `figure_read_back_right`. Different: the `_wrong` reply. The gold belief is not used for this: the customer confirms what they said.
- *Re-asks and disposition:* as `topics.json` says: one draw per customer and matter, shared by the arms. A customer who gives way says `defer` in the open call and `go_along` in the closed call, and repeats it on a re-ask; one who answers gives `own`, then `again`. The open call's `go_along` replies (short answers that still carry the content) are not part of the disposition rule: they are a separate "terse customer" condition on the text path only.
- *Voices:* Shivani is the bot. For each gender, sort the customer ids, shuffle with `random.Random("samajh-p5-2026-11-10:voice:" + gender)`, and give `pool[rank % 6]` from Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika (f) or Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad (m). The speaker's gender is `speaker.gender` in `customers.jsonl` (for a third party, the person who answers). The same voice serves both arms and every level.
- *Batch subset:* Batch runs on 12 open calls at level 0 (the first 12 full-call customers in the seeded order, 6 per language) and is off elsewhere. Reason: Batch does not change the tier and is the largest cost of a call.
- *The two readings:* the order (v3.0 or v2.5 first) is the coordinator's open decision (`DESIGN.md` section 15 item 34). Settle it before stage 2 and record it in the run's manifest; do not change it between stages.
- *The live classifier:* a turn whose LLM classifier call timed out is logged as degraded and kept. A rerun may read it differently; the first completed call counts.

**Order once P1, P2 and P3a are verified:** Part 2, section 4, with these stages and ceilings (contract section 7): stage 1 text, all levels, 0 credits; smoke test of 4 customers, ceiling 35; stage 2 voice level 0 (60 open calls, 46 closed), about 210; stage 3 voice levels 1 then 0.5, the 46 customers who talk through the call, both arms (184 calls), about 55 (level 0.5 reuses clips of levels 0 and 1); hard stop at 300 in total. That is 290 voiced calls; the judge's "at least 120" needs stage 3. Each customer's open and closed calls run next to each other. Stop and ask if a stage's ledger change exceeds 1.3 times its estimate.

**Cost arithmetic behind those figures** (rates are client estimates; Part 2, section 3 gives the per-call sums): 46 customers talk through the call and 14 end at the opening. Open, level 0, Batch off: 46 x 1.95 + 14 x 0.3 = 94. Closed, level 0: 46 x 1.5 (about four statements per customer carry that record's own values; the others are shared) + 4 of shared lines = 73. Lines with a first name: 18. The second lender name ("नमूना फ़ाइनेंस", 29 NBFC records): about 4. Batch on 12 calls: 19. Stage 2 = about 210. Levels 1 and 0.5: open 46 x 0.7 = 32, closed 46 x 0.5 = 23; stage 3 = 55. Total about 265. The verifier checked this against the replies as written: the open `own` text of a customer who talks through the call is 584 characters on average (838 at most) against the 700 assumed; it put the closed arm at about 78 against 73 and stage 3 at about 45 against 55. STT seconds are assumed from text length; no audio has been measured. Part 2's larger totals assume Batch on every call and all 60 customers voiced in full at three levels.

## Part 2. Research report (Sonnet, read-only, 2026-11-10; saved as returned)

Checked on 2026-11-10 against the working tree, before `references/pilots/P5-contract.md` and `data/p5/records/` were written. Ran only `--help`, `prompts build --dry-run`, `prepare --dry-run` and local file reads (ledger, case files).

### 1. What exists

| Need | Where | Command or function |
|---|---|---|
| (a) unpackaged records | `records.py:88-91` `default_book()` adds `SAMAJH_RECORDS_DIR`. `create_app` calls it once at startup (`app.py:961-965`), so restart after adding records. The picker lists them: `/api/records` (`app.py:1015`), `web/phone.js:845`. A file must be a `CallRecord` named `<id>.json`, id matching `^[a-z0-9][a-z0-9-]{0,40}$` (`records.py:21,70`). One bad file stops the server starting. | `SAMAJH_RECORDS_DIR=$PWD/data/p5/records uv run python -m samajh.server --port 8085` |
| (a) bot lines for new records | `prompts build` honours the env var only with `--record` (`prompts.py:126-132`). It builds every `--lang` for every `--record`, so run it once per language. | `SAMAJH_RECORDS_DIR=$PWD/data/p5/records uv run python -m samajh.server.prompts build --lang hi --record ID1 --record ID2 --dry-run` (drop `--dry-run` to pay) |
| (b) voice a reply | `prepare.py` is no use: `script()` loads `PACKAGED_DIR` only (`prepare.py:144`) and the CLI takes three hard-coded personas (`:135,201`). Reusable parts: `customer_voice()` (`:159`) and `to_line_pcm` (`server/audio.py:119`). One reply by CLI, same request, cached: | `uv run python -m samajh.clients.gnani tts "TEXT" --voice Avinash --language hi-IN --sample-rate 8000 --out OUT/01.wav` (`hi-en` for Hinglish) |
| (c) whole call to case file | `replay.py`; resumable with `--out`; `call.json` params win over `--param` (`replay.py:92`). Without `--url` it runs the app in-process with the patient client profile (`:343`). | `uv run python -m samajh.server.replay DIR --url http://127.0.0.1:8085 --out OUT` (DIR holds `call.json` with `params {record, language}` and the wavs) |
| (d) text path to a tier | No CLI takes a `CallRecord`. `python -m samajh.dialogue play --record` and `eval/text_path/run_transcript.py` both want a bare `LoanRecord` (`dialogue/__main__.py:53`), i.e. the `.record` field. In code: `core.start/step` then `samajh.pipeline.run_text(transcript, record.record, llm)` then `.result.tier` and `samajh.rules.summarise`. | `uv run python -m samajh.dialogue play --record LOAN.json --lang hi` (interactive, no bank) |
| (e) credit ceiling | The cap is ledger-wide, not per run: `_check_cap` compares the whole ledger total (`client.py:480-483`), and `GNANI_CREDIT_CAP` overrides the 1000 (`:176`, read at server start). Cache hits skip lock and cap (`:543`). evalkit `--budget` covers only evalkit jobs (`runner.py:341`). | `GNANI_CREDIT_CAP=<spent+ceiling> uv run python -m samajh.server ...`; read spend with `uv run python -m samajh.clients.gnani ledger` (`est_credits_spent`) |
| (f) statistics | `samajh.evalkit.score.wilson(correct, n)` (`:108`), `mcnemar_exact(only_a, only_b)` (`:120`). No CLI. Table pattern: `eval/text_path/triage.py` (`TriageRow`, `table`). | `uv run python -c "from samajh.evalkit.score import wilson, mcnemar_exact; ..."` |

Do not use a separate `SAMAJH_STATE_DIR`: it gives a fresh ledger, cache and cap, so the project cap stops protecting you.

### 2. What is missing (size: S under 50 lines, M 50-150, L 150-400)

1. **Reply-bank player** (`eval/p5/player.py`, M-L). Reuse the `replay_call` loop (`replay.py:221-304`) with a `next_turn(asked_event)` hook in place of the fixed script. Choose the reply at run time from `GET /api/sessions/{id}`, because `bot_json` has no tags (`app.py:367-378`). From the last non-superseded `BotEvent` (`sessionlog.py:134`) read:
 - `lines[-1].key`, and `lines[0].key` for prefix lines;
 - `lines[-1].tags` (`step`, `asks`, `product_id`; set in `samajh_dialogue.py:88-100`);
 - `listen` (yes_no, short, amount or open) and `second_reading` (`samajh_dialogue.py:40-50`);
 - `end_call` and `tags.outcome`.

 Rules:
 - **Re-ask:** key ends `.reask`, or the topic was already presented in this call (a "who is this?" answer repeats a `.ask`). Then use `again`, falling back to `own`.
 - **Read-back right or wrong:** the bot reads back only the figure it understood, so compare it with the fact sheet. The exact figure is `core.CallState.position.amount_inr` (and `.low`, `.item`) in `<state>/sessions/<id>/session.json` via `call_state()` (`samajh_dialogue.py:199`). The HTTP log drops `dialogue_state` (`app.py:1087`). Parsing the line text with `parse_amount` is the alternative (inferred).
 - Keep the choice a pure function of (customer, level, events), so a resume repeats it. Record (seq, topic, variant, text, voice) in the runner's own manifest.
 - **Why a precomputed script fails:** `prepare` scripts with the fallback off and feeds `second=reply` (`prepare.py:141-155`). A live call uses the LLM fallback with a 2.5 s wall clock (`llm_fallback.py:230`, 2.5 s default). A first run that times out can differ from its cached rerun.

 Mapping, from `LINES` (`dialogue/prompts.py:40-102`) and `machine.py:418-468`. **Line keys are a moving target**: add a test that every key in `LINES` is mapped or listed "no reply".
 - `is_this_you` = `right_party.ask`; `is_this_you_again` = `right_party.reask` (after "who is this?" it follows `purpose.before_confirm`).
 - `can_we_talk` = `disclosure.go_ahead` (utterance starts `disclosure.who`); `can_we_talk_after_check` = `disclosure.go_ahead` preceded by `verify.before_loan`. `disclosure.reask` has no topic, so reuse `can_we_talk` own.
 - `year_of_birth` = `second_check.ask`, with `second_check.reask` as again. `when_to_call` = `callback.when`. `anything_else` = `open_recall.nothing`.
 - `what_did_you_take` = `open_recall.ask` (utterance is `context.loan`, `disclosure.rights`, `open_recall.ask`), with `.reask` as again.
 - `what_is_it` = `kind.*`; `how_much` = `premium.*`; `say_amount_again` = `premium.say_again`; `how_paid` = `payment_source.*`; `how_often` = `payment_frequency.*`; `needed_or_choice` = `required_for_loan.*`; `where_to_take_it_from` = `provider_choice.*` (skipped when the customer said it was their own choice); `what_it_gives` = `cover.*`; `how_long` = `term.*`; `can_cancel` = `cancel_window.*`; `money_back` = `features.*`; `what_you_agreed_to` = `consent.*`. Each is `.ask`, with `.reask` as again.
 - `figure_read_back_right/wrong` = `read_back.confirm | confirm_about | reconfirm` with `asks=premium`. `what_is_right_amount` = `read_back.restate` with `asks=premium`. `benefit_read_back_wrong` = `read_back.cover_confirm`, or `reconfirm` with `asks=cover`.
 - `carry_on` = `stop_check.decline` and `stop_check.disengaged`.
 - If the customer gives a figure in open recall, `premium.ask` is skipped and the premium is read back directly (`machine.py:657-675`).

 **Unmapped, or that cannot work as built:**
 - `stop_check.human` ("would you like to speak to a person?") has no topic.
 - `cover.say_again` has no topic.
 - `read_back.restate` with `asks=cover` has no topic, because `what_is_right_amount` is about the premium.
 - A right cover read-back has no topic. Use `figure_read_back_right` (inferred).
 - `silence_prompt` has no triggering line: nothing says "I could not hear you", and two empty turns end the call as `no_response` (`machine.py:778`). It is only usable as a reply to a re-ask after empty STT, so a rule is needed.
 - `not_understood` has no line either. Use it as the default for unmapped keys.
 - `topics.json` does not say which reply a `go_along` customer gives on a re-ask (`again` or `go_along`); the contract must.

2. **Closed arm** (`samajh/server/closed_dialogue.py` M-L, plus `data/p5/closed_<lang>.toml`, wording needs a human read).
 - **Plug-in point:** `Dialogue.start/step` plus a factory (`server/dialogue.py:75-90`). `create_app` registers dialogues only when `dialogues is None` (`app.py:959-965`). Add one line there, or use a launcher that passes both `dialogues=` and `records=`; otherwise `records` stays None. Select with `--dialogue closed` or `call.json "dialogue": "closed"`. The name is stored in the session and the factory is called again on resume.
 - **Opening:** delegate the first three steps to `SamajhDialogue` until `state.position.at == "recall"`, then switch to statements. State is an opaque string, so wrap the core state.
 - **Statement lines:** each is a `BotLine` of at most 600 characters, voiced on first fetch by `Sessions._speak` (`app.py:634`), with `listen="yes_no"` and no second reading. The `load_prompts` lint bans digits and product words, so these lines cannot live in `data/prompts/`.
 - **Reading:** `RuleInterpreter().interpret(text, language, expecting=Expecting.confirmation, question=...)`, or the fallback, gives `Intent.yes`, `Intent.no` or other.
 - **Outcome:** put `tags={"outcome": "confirmed"|"not_confirmed"}` on the last utterance and per-statement readings in per-line tags, because the HTTP log hides the state. `Outcome.not_confirmed` already means "nobody claimed to be the borrower" (`machine.py:65`), so namespace the closed value.
 - **No case file:** `CaseJobs._record` refuses any dialogue other than `samajh` (`app.py:718`), so use `--no-case`.

3. **Batch off** (S). `CaseJobs` takes an injectable client (`create_app(batch=...)`, `app.py:951,976`). A launcher `eval/p5/serve.py` can pass a null client whose `batch_transcribe` returns an empty `BatchTranscript`; that needs no package edit. The case then has status `ready` with 0 segments and no speaker labels. The alternative is a `[batch] enabled` field in `BatchConfig` (about 10 lines; none exists today).
 - **The tier does not depend on Batch.** Extraction reads the dialogue transcript, not Batch (`casefile.py:280,330`). The extract step is not nested under the batch step (`:341-345`).
 - **If Batch fails or is skipped by raising**, `failed=["batch","align"]` and `status="failed"`. `tier` and `result` are still filled, but replay exits 1 and the file is documented as not meaningful.
 - **Cost:** Batch is billed per recorded second and is the largest part of a call (section 3).

4. **Customer voices** (S, in `eval/p5/bank.py`). Timbre v3.0 has 13 voices (`gnani/types.py:92-96`). The bot is Shivani (`settings.toml`); the other 12 are available:
 - Female: Lakshmi, Kalpana, Chetana, Vasudha, Riyaa, Tarika.
 - Male: Avinash, Shubham, Prakash, Devansh, Yashraj, Harshad.

 Rule: sort the customer ids of each gender and shuffle them with `random.Random("samajh-p5-2026-11-10:voice:"+gender)`, as `evalkit/plan.py:148-175` does. Give voice `pool[rank % 6]`, so each voice gets about 5 of 60. Gender is not on `Borrower` (`types.py:405`), so it comes from `customers.jsonl` (inferred). Batch separated Shivani from a male voice in 4 of 4 P1 calls; a female customer voice is untested.

5. **Text-path runner** (M, `eval/p5/text_run.py`). Loop `core.start/step`, pick the reply with the same mapping on `core.Line` (`.key`, `.step`, `.asks`) and `core.expecting(position)`, then `run_text`.
 - Use `LlmFallbackInterpreter(..., timeout_s=None)` for repeatability, or `RuleInterpreter()` alone for zero network.
 - Cost is OpenRouter only, about USD 0.0015 per transcript (`defaults.toml`).
 - The server's LlmClient USD cap is per instance (default 1.0, `llm.py:191`); set `SAMAJH_LLM_USD_CAP`. A silent `CapExceeded` makes fallback turns "degraded".

6. **Scorer** (M, `eval/p5/score.py`). Read each `case.json` (`tier`, `call_outcome`, `status`) and the gold rows (`eval/p5/gold-rules.md`). Count by customer kind, arm and level: miss (problem with clear or understanding_gap), referral, false referral, incomplete shown separately. Use Wilson per 100. Run McNemar on open versus closed for the same customer and level. The closed outcome maps to refer or clear (inferred).

7. **Third-party leak check** (S, in the scorer). In the session log, any non-superseded `BotEvent` line with key `context.loan` or `verify.after_loan`, or `tags.step` in {context, open_recall, teach_back, consent_check, read_back}, is a leak. `BotEvent.audio` (or `lines[].tts`) non-null shows it was synthesised.

8. **Smaller items:**
 - Freeze-hash script (S).
 - Run driver with stage, ceiling and ledger-delta bookkeeping (S-M).
 - Discrepancy to settle first: `readings()` passes v3.0 first (`samajh_dialogue.py:54-61`), but P2-contract §5 asks for v2.5 first on amount turns. This changes which figure is read back.

### 3. Cost (estimates; the rates may be 20% or more off)

- **Rates:** STT 0.010 per second, TTS 0.002 per character, Batch 0.010 per recorded second. The ledger agrees for Batch: 9 jobs, 884.5 s, 8.84 credits.
- **P1 measured:** STT 0.294 (hero) and 0.378 (informed) per call. `call.wav` 157-160 s, so about 1.6 credits of Batch. One read-back is about 50 characters, so 0.10. The personas' replies were 318 and 479 characters.
- **Open call, level 0, Batch on:**
- Customer reply TTS, 700 characters (assumed; P5 replies are unseen): 700 × 0.002 = 1.4.
- Read-backs, 1.5 × 0.10 = 0.15.
- STT, 0.4.
- Batch, 1.6.
- Total about 3.5, or about 1.95 with Batch off.
- **Same customer at another level:**
- Cached turns are free. Reply text and voice are identical, so TTS bytes are identical. The upload is canonical 8 kHz mono, so it keeps its bytes (`audio.py:119-127`), and the STT key hashes those bytes (`client.py:305`). A non-canonical upload goes through ffmpeg with bit-exact flags (`audio.py:93-101`); that is deterministic (inferred, not tested).
- TTS keys on text, voice, model, language, speed, rate and container (`client.py:349`); STT on model, language_code, format and audio bytes.
- Each flipped topic costs about 0.06 (20 characters of TTS plus about 1.5 s of STT). With about 11 grouped topics: 0.5 gives about 0.3, 1.0 gives about 0.7.
- Batch is re-billed because `call.wav` differs (its key is its bytes, `client.py:404`). So about 1.9 at level 0.5 and about 2.3 at level 1 with Batch, or 0.3 and 0.7 without.
- **Closed call, level 0:**
- Statement TTS, 10 × about 85 characters, less shared text: about 1.5.
- Replies TTS, 10 × about 30 characters: 0.6.
- STT, 13 turns: 0.2.
- Total about 2.3, plus 0.25 at level 0.5 and 0.5 at level 1. There is no Batch.
- **New names:** per name, `right_party.ask` + `right_party.reask` + `end.third_party` = 30+87+46 = 163 characters in Hindi, 168 in Hinglish, so 0.33 credits. 60 names cost about 20 credits. Skipping `end.third_party` would save about 5. A new lender name adds about 986 characters (2.0 credits) once per language.
- **Totals, 60 customers at 3 voice levels (assumes all voiced at all three):**
- Batch on: open 60 × (3.5 + 1.9 + 2.3) ≈ 465; closed 60 × 3.05 ≈ 183; names 20. Total ≈ 670.
- Batch off: open 60 × (1.95 + 0.3 + 0.7) ≈ 177. Total ≈ 380.
- **Headroom:** the ledger reads 279.21 (CLAUDE.md says about 295), against a cap of 1000. That leaves about 720 of headroom, so Batch-on uses about 93% of it. Batch is not needed for the tier.
- **Time (inferred):** about 1 minute per open call. Wall time is dominated by STT, the fallback LLM and about 10 s of Batch (19 polls for 10 jobs at 3 s). Sequential, the run is about 5 hours.

### 4. Order of operations (once P1 and P2 are verified)

1. **Freeze:**
 - Record `git rev-parse HEAD` and `git status --porcelain samajh data/prompts`; it must be clean.
 - Take sha256 of `data/prompts/*.toml`, `samajh/server/settings.toml`, `data/p5/{topics.json,customers.jsonl,replies.jsonl}`, `data/p5/records/*.json` and the gold. Compare them with the hashes pinned in the contract.
 - Fail closed on any mismatch. The pattern to copy is `uv run python -m samajh.scenarios verify`.
2. **Idle check, before each stage:**
 - `lsof -i :8085` must be empty, and `lsof .samajh/gnani.lock` must show no holder.
 - Run `uv run python -m samajh.clients.gnani ledger` twice, 30 s apart; `rows` must be unchanged. Note `est_credits_spent` as S0.
3. **Zero-credit checks:** `prompts build --dry-run` per language, the mapping-coverage test, and a text-path pass on a few customers (OpenRouter only).
4. **Bot lines:** `prompts build` once per language with that language's records (about 20 credits), then the closed statement lines.
5. **Server:** `GNANI_CREDIT_CAP=<S0+ceiling> SAMAJH_RECORDS_DIR=$PWD/data/p5/records SAMAJH_LLM_USD_CAP=<n> uv run python eval/p5/serve.py --port 8085`. Use the patient client profile; the default server is the live profile (`__main__.py:26`), whose 5 s lock wait gives `gnani_busy`. Check `/api/health` for the dialogues and `/api/records` for the 60 records.
6. **Smoke:** 4 customers (hi and hi-en, one female voice, one male, one third party), open and closed, level 0. Estimate about 23 with Batch on or 17 off; set the ceiling at 30-35. Pass when:
 - every call ends, with no `script_drift` or `gnani_busy`;
 - the case is `ready`;
 - the third-party call has no leak;
 - the ledger delta is within 30% of the estimate;
 - **rerunning the same smoke costs 0.**
7. **Stages:**
 - A: level 0 open, 60.
 - B: level 0 closed, 60.
 - C: level 0.5, both arms.
 - D: level 1, both arms.
 - Order customers by a fixed seed, with each customer's open and closed calls adjacent. Rerun the idle check between stages and stop if the ledger delta exceeds 1.3 times the estimate.
8. **Nothing else may use the account during a run** (concurrency is 1 per account, and STT and TTS share the slot). Do not run the phone, `evalkit`, `prepare` or `repro_number_formatting.py` meanwhile.
9. **Crash resume:**
 - Rerun the same command with the same env, records dir and state dir. Sessions persist as `<state>/sessions/<id>/session.json`.
 - `OUT/replay.json` names the session, and a turn sent twice is answered once (`replay.py:17-21`, `app.py:_plan`).
 - A finished call is skipped when its `case.json` is `ready`. A case left `running` restarts on request (`app.py:801`).
 - Clients cache Gnani and LLM answers, so repeats are free. A second reading or fallback call that timed out the first time was not cached and can differ on resume; log `degraded_turns`.
 - Do not change the dialogue, prompts, settings or records between a crash and its resume.
