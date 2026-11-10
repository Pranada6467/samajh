# Iteration 1 verification, part 2: clients, voice, audio evaluation, dialogue

Date: 2026-11-10. Verifier: independent (wrote none of the code under review). Scope: `samajh/clients`, `samajh/server` + `web/`, `samajh/audio`, `samajh/evalkit` + `eval/amounts` + `data/amounts`, `samajh/dialogue` + `data/prompts`.

**Short answer.** The clients, the transport and the evaluation harness do what their reports say, and their numbers reproduce. The dialogue is not ready to be put on a voice line. On fresh inputs it names the loan to people who say they are not the borrower, carries on asking after a refusal it does not recognise, and hangs up on customers who are describing the sale. The two-reading rule for amounts, in the order `DESIGN.md` §7 gives (v3.0 first), protects nothing. In Chrome the phone cuts an answer at a 600 ms pause and loses the rest. The server's `Dialogue` protocol cannot carry the dialogue as built. The verdict is the last section.

## 1. How this was done, and its limits

- Everything marked "ran" was run by me or by one of two helper agents working to my brief (one on the server and phone, one on the audio evaluation). Their rows are marked **(helper)**. I reran the amounts recount and the achieved-SNR measurement myself, read the raw output of the browser runs, and read the code behind H6, M6, M10 and M12. The other helper findings rest on the helper's runs, whose scripts are kept.
- **No Gnani call was made.** The client probe talks to a fake server on 127.0.0.1 with a fake key. The server was started from a launcher with a fake speech client. `tests/clients/probes/gnani_probe.py` was never run. During my full test run the shared ledger gained rows, all of them OpenRouter rows from another worker; no Gnani row was added.
- **OpenRouter: about 0.001 USD** (`LlmClient.spent_usd` read 0.00085 after the one live probe), through `samajh/clients/llm.py`. The client wrote its usual rows to the shared `.samajh/ledger.jsonl` and cache.
- No git command was run. Git history was checked by reading `.git` as files (515 loose objects inflated; there are no pack files).
- No product code, test, data or document was changed. Everything I wrote is under `references/reviews/iter1/`. Mutation runs happened in scratch copies outside the repository.
- Every probe sentence was written by me or a helper (LLMs), not said by a person. Counts of probes are counts, not rates. I read Hindi and Hinglish as a fluent reader would, but I am not a human native speaker and nothing was voiced or heard. Tamil and Kannada probes are not human-reviewed.
- The frozen scenario set (`data/scenarios`) was not used.

Probe scripts are in `references/reviews/iter1/probes/`. Mine: `dialogue_attack.py`, `dialogue_nine_gaps.py`, `dialogue_second_reading.py`, `dialogue_llm_fallback_live.py` (live, spends), `w9b_fixes_recheck.py`, `gnani_client_offline.py`, `w2_fixes_recheck.py`, `secret_scan.py`, `mutation_run.py`, `integration_shape.py`. Helpers': `server_*` and `amounts_*` (except `amounts_fresh.py`, which belongs to another reviewer, as do the other files in that folder). Run any of them with `uv run python <path>`.

## 2. Findings, ranked

Severity is the consequence on a real call. "Where" is the code that decides.

### High

**H1. The loan is named to people who say, in ordinary words, that they are not the borrower.**
- Run: `uv run python references/reviews/iter1/probes/dialogue_attack.py third_party`
- Result: 34 fresh third-party openings (wife, son, daughter, brother, mother, colleague, neighbour), each followed by a yes and the borrower's birth year. The lender was named to 32 and **the loan was named to 31**: Hindi 10 of 10, Hinglish 6 of 8, Tamil 8 of 8, Kannada 7 of 8.
  ```
  [hi] LOAN NAMED  wife   ['हाँ जी, रमेश की वाइफ़ बोल रही हूँ', 'ठीक है', '1984'] -> at recall
  [hi] LOAN NAMED  wife, after the re-ask  ['कौन?', 'हाँ हैं, बुलाती हूँ', 'हाँ', '1984'] -> at recall
  [ta] LOAN NAMED  wife   ['ஆமா, நான் அவர் மனைவி பேசுறேன்', 'சரி', 'அவர் 1984ல பிறந்தார்'] -> at recall
  [kn] LOAN NAMED  child  ['ಅಪ್ಪ ಮಲಗಿದ್ದಾರೆ, ಹೇಳಿ', 'ಆಯ್ತು', '1984'] -> at recall
  ```
- Where: a speaker is believed to be someone else only if their words are in a list (`samajh/dialogue/_lexicon.py`, `wrong_person`; read at `interpret.py:180`). Any "हाँ", "जी", "बोलिए", "சொல்லுங்க" or "ಹೇಳಿ" elsewhere in the turn is a yes (`interpret.py:188`). The re-ask line makes it worse: "क्या {first_name} जी लाइन पर हैं?" asks whether he is available, and "हाँ हैं, बुलाती हूँ" (yes, I'll call him) is a truthful answer that the machine takes as "I am he" (`data/prompts/*.toml`, `right_party.reask`).
- Limits: the third party must give the borrower's birth year. A spouse, child or parent can; the colleague and neighbour rows assume they can. Without the year the caller still hears the lender's name, "customer care" and "feedback call", then `end.check_failed`. `DESIGN.md` §5 accepts that a false first-name "yes" plus the right year passes. These speakers did not lie: they said who they were.
- Consequence: the bot tells a family member that the borrower "recently took a loan from <lender>" and then asks what was bought with it. This is the disclosure the v2 opening was redesigned to prevent. W9's R1 and R3 fixed the phrases the reviewer tried; the class is open.

**H2. A customer who refuses in words the lists do not hold is asked the next question.**
- Run: `uv run python references/reviews/iter1/probes/dialogue_attack.py refusals`
- Result: 42 fresh refusals at a teach-back question ("मैं गाड़ी चला रहा हूँ", "कल फ़ोन करना", "I'd rather not answer", "நாளைக்கு கூப்பிடுங்க", "ನಾಳೆ ಫೋನ್ ಮಾಡಿ"). The bot went on to the next question on **37**: Hindi 10 of 12, Hinglish 10 of 10, Tamil 10 of 10, Kannada 9 of 10. A customer who repeats one such refusal to every question hears 11 more bot utterances, and the call ends as `completed`.
- With the LLM fallback on (pinned model, live): of 13 of those refusals, 6 got the stop question, 4 were re-asked as off-topic ("I am driving" in three languages, "कल फ़ोन करना"), 3 got the next question (`dialogue_llm_fallback_live.py`).
- Where: `interpret.py:168-176` (lists only); an unlisted turn is `Intent.said`, which `machine.py:643` counts as an answer.
- Consequence: in its disclosure the bot said "आप बीच में कभी भी कॉल रोक सकते हैं". Carrying on is the "nagging" pattern `DESIGN.md` §5 cites as its reason for one re-ask, and the call is logged as completed with a refusal recorded as the answer to each question. W9 lists this as gap 9 (20 of 39 of its own probes).

**H3. An account of the sale that holds refusal-like words ends the call.**
- Run: `uv run python references/reviews/iter1/probes/dialogue_attack.py false_declines`
- Result: 21 fresh answers a misled customer might give. The call **ended on 16**: Hindi 6 of 6, Hinglish 4 of 5, Tamil 2 of 5, Kannada 4 of 5.
  ```
  [hi] ended:declined         मुझे तो इसमें इंटरेस्ट नहीं है, फिर भी जोड़ दिया गया
  [hi] ended:declined         बैंक वाले बोलते हैं बाद में बात करेंगे, आज तक कोई नहीं आया
  [hi] ended:human_requested  मैनेजर से बात करनी है बोलो तो कोई सुनता नहीं वहाँ
  [kn] ended:declined         ನನಗೆ ಆಸಕ್ತಿ ಇಲ್ಲ ಆದ್ರೂ ಸೇರಿಸಿದ್ರು
  ```
- Where: `interpret.py:167-171`. R4 softens a refusal phrase only when the turn also holds a listed past-tense or reported-speech word (`_lexicon.py`, `recounts`). Present and habitual forms ("बोलते हैं", "काट देते हैं", "keeps saying") are not listed, and the Tamil and Kannada lists are empty (W9 gap 8).
- Consequence: the product hangs up on the sentences it exists to hear, says "ठीक है, कोई बात नहीं" and records the case as `declined` or `human_requested`. The remaining questions are never asked, so the rule engine has little to work on. The LLM fallback does not help: it is consulted only when the rules return `said`, and here the rules have already ended the call.

**H4. With v3.0 as the first reading, the second reading changes nothing when v3.0 is wrong.**
- Run: `uv run python references/reviews/iter1/probes/dialogue_second_reading.py`
- Result: the 240 real Prisma transcript pairs of the amounts run (phone condition), played into the premium question. Figure the call holds, and will read back:

  | Order of readings | Right | Wrong figure held | None (re-asked) |
  |---|---|---|---|
  | v3.0 alone | 222 | 16 | 2 |
  | v2.5 alone | 224 | 1 | 15 |
  | **v3.0 first, v2.5 second** (`DESIGN.md` §7) | 224 | **16** | 0 |
  | v2.5 first, v3.0 second | 238 | 2 | 0 |
  | v2.5 `literal` first, v3.0 second | 238 | 2 | 0 |
  | v2.5 `literal` alone (one call) | 238 | 1 | 1 |

- Where: `machine.py:529-536`. The call acts on the first reading whenever it holds a figure. A disagreement is stored (`SecondReading.agreed = False`) and has no other effect.
- Limits: TTS audio, one amount per sentence, and the parser has since been tuned on these 240 sentences, so the counts are in-sample. They compare orders; they are not rates for callers.
- Consequence: `DESIGN.md` §6 says of v3.0's skipped-group errors that "the second reading is what catches it". In the order §7 and §6's diagram give, it does not: the bot reads back 3,02,000 for "three lakh two hundred", and only the customer can catch it. The adapter must put v2.5 first on amount turns, or the machine must treat a disagreement as "ask again" instead of reading back the first figure.

**H5. The server's `Dialogue` protocol cannot carry this dialogue.** Not a defect in anything shipped, since the adapter is not written, but each item stops the wiring. Details and the full adapter list are in section 8.
- The disclosure is one utterance of 672 to 864 characters in every language; the server's `BotUtterance.text` allows 600 (`samajh/server/dialogue.py:23`). The second utterance of every call is refused (`integration_shape.py`).
- The protocol gives the dialogue one transcript per turn from one model fixed for the session (`app.py:367-369`). There is no way to ask for, or pass, a second reading.
- A two-product call in which every answer is unclear needs 43 customer turns; the server stops at 40 with a 409 (`app.py:74`, `345`).

**H6. The browser phone cuts an answer at a pause of about 600 ms, and the rest of the answer is never captured.** (helper ran it; I read its raw output and the code)
- Run: the shipped page in headless Chrome with a 48 kHz file as the microphone, against a fake-backed server: `node tests/server/browser_check.mjs --url http://127.0.0.1:8191 --mic <file> --query "mode=hands-free"` (launcher: `probes/server_launcher.py`).
- Result: answers with a spliced pause of 0 to 500 ms were uploaded whole. At 600 ms the turn was cut at the pause in **7 of 8 runs** (the helper's splice 2 of 2, the builders' own `pa01` 2 of 2, `pa02` 1 of 2, `pa03` 2 of 2); at 800 and 900 ms in 3 of 3. Three clips with no pause came through whole.
  ```
  pause 500 ms (answer lasts 5.52 s): the phone uploaded one turn of 5.42 s -> whole answer
  pause 600 ms (answer lasts 5.62 s): the phone uploaded one turn of 2.20 s -> CUT after the first part
  pa01: clip 4.94 s; in Chrome the phone uploaded one turn of 3.22 s -> CUT at the pause
  ```
- Where: `web/vad.js:26` (`hangoverMs = 700`), `web/phone.js:383-391` (the first end of speech sends the turn), `phone.js:367` (frames outside `listening` are dropped). Under Node on the 8 kHz clips the same detector keeps 600 ms pauses whole, which is what `voice-loop-iter1.md` reports; the browser captures at 48 kHz and behaves differently. Chrome's own audio processing explains part of it, not all.
- Limits: 19 runs, TTS clips, one machine, a file as the microphone. No human pause data exists.
- Consequence: "पाँच लाख … बीस हज़ार" with a thinking pause is sent as "पाँच लाख". Prisma returns a well-formed amount that is wrong, and the rest is spoken while the phone is transcribing, so nothing hears it. Only the read-back can catch it. It also weakens the second reason for choosing REST over streaming (`DESIGN.md` §15 item 12b): at a 600 ms pause the shipped phone cut as streaming's default did.

### Medium

**M1. A "yes" in the second transcript overrides a "no" in the first at a read-back.**
- Run: `dialogue_attack.py read_back`. `step(state, "नहीं", second_reading="हाँ")` at a read-back gives `completed`, the customer turn is stored as "हाँ" and nothing is marked unresolved; "नहीं" alone goes to the restate question. Same in all four languages.
- Where: `machine.py:555-569` (`_brings_no_figure`): a plain yes "stands" in whichever reading holds it.
- Consequence: the `premium` rule passes only on a confirmed read-back. Here a confirmation is recorded that one of the two speech models contradicts. Two readings that disagree on yes and no should be asked again.

**M2. A reply that only repeats the figure counts as confirming it, and the read-back does not say what the figure is.**
- Run: `w9b_fixes_recheck.py`, `dialogue_nine_gaps.py` (item 3).
  ```
  'कौन सा बावन हज़ार?'            -> ended:completed; unresolved 0
  'बावन हज़ार तो लोन की किस्त है'  -> ended:completed; unresolved 0
  'जी हाँ सही, बीस हज़ार तो मैंने अलग से दिए थे' -> premium now 20000; bot reads back 20,000
  ```
- Where: `machine.py:671` (`heard.amount_inr == read` confirms) and `:658` (any other single figure replaces the premium, even after "yes"). The line is "आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?", said after about ten other questions, one of which ("कितनी रक़म तक?") also invites an amount.
- Consequence: false confirmations and false corrections of the one figure the rules compare. W9 lists the second half as gap 3.

**M3. A bare yes or no to "was it required, or your choice?" is taken as an answer** in all four languages (`dialogue_attack.py yes_to_either_or`; `interpret.py:201`, `Expecting.told`). "हाँ जी" to an either/or question says nothing, and the re-ask line reverses the polarity ("would you have got the loan without it?"). The extractor is left to guess, and one guess is a high `bundling` flag.

**M4. Silence does not end a call.** After the opening, a line that goes dead gets every remaining question twice: 26 bot utterances, outcome `completed` (`dialogue_attack.py loops`). There is no "nothing heard N times" exit. On the browser phone a customer who walks away is questioned to the end.

**M5. The credit total is an estimate that has never been checked against the dashboard, and three kinds of call are booked at zero or by assumption.** Ledger total today: **114.34 estimated credits** (my recount of 17,050 lines, all of which parse; `gnani_client_offline.py` step 6 agrees). Details in section 5. The guard is safe against the 1,000 cap only because the cap is far away.

**M6. Following `eval/amounts/REPORT.md` §8 ("Reproduce") overwrites the before-fix evidence.** (helper; I read the code) `python -m samajh.evalkit score` rewrites `eval/amounts/run/scores.jsonl` with today's parser (`samajh/evalkit/__main__.py:97-99`), and `label_failures.py` and `analyze.py` rewrite `failure_labels.tsv`, `FAILURES.md` and the tables of `REPORT.md`. The rows carry no parser hash, and the before-fix parser is not in the working tree (report hash `efbd312d…`, today `ebc402d0…`). In a scratch copy the three commands changed 239 lines of the report. The numbers the design cites for the two-reading decision (221, 214, 199 of 200) can be recounted from the saved file today, and are one command away from being replaced by in-sample numbers.

**M7. The noise conditions are labelled by a whole-clip, full-band SNR, and the TTS voices carry most of their energy below 300 Hz.** (helper, measured on all 480 stored noisy clips) In the 300 to 3400 Hz band, "babble 5 dB" is a median 1.8 dB (range −3.6 to 4.8) and "street 5 dB" a median 7.4 dB. By the code's own definition the mix is exact (10.00 and 5.00 dB). So "street noise at 10 and 5 dB cost nothing" is about 12 and 7 dB in the speech band, and the babble cell is harder than its label. The labels cannot be compared with SNR figures from anywhere else.

**M8. "Two readings that agree are almost always right" is true on the phone cell only.** (helper) Under street noise at 5 dB both models agreed on a wrong amount twice in 111 agreeing pairs; for `amt-kn-irr-10` both dropped the same word. Shared recognition errors are the failure agreement cannot catch, and human speech will produce more of them than TTS. The one phone miss (`amt-ta-irr-06`) is put down to "a sentence whose written form is suspect" in `REPORT.md`, `README.md` and `DESIGN.md` §6; the transcripts do not support that over a voice or recogniser cause, and nobody listened to the clip.

**M9. The lint that guards the prompt files is a word list and passes lines the design bans.** `dialogue_nine_gaps.py` item 7: of 16 bad lines of my own, 11 pass, among them "tell me the code sent to your mobile", "आपके मोबाइल पर आया कोड बताइए", "अपनी माताजी का नाम बताइए", "आपका बावन हज़ार कट चुका है" and "पैसे आपको वापस दिला देंगे". No shipped line holds any of these (I read all 204). The risk is the next edit to a prompt file.

**M10. A response whose headers arrive slowly holds the Gnani key lock with no total limit.** (helper ran it; I read the code) With a 0.5 s deadline and a 1.0 s read timeout, a body dripped a byte at a time was cut after 0.6 s, and headers dripped the same way were cut after 39.1 s. `samajh/server/speech.py:78-87` checks the deadline only when a body chunk arrives. The comment at `speech.py:43-44` and the report's "about 16 s" worst case hold for the body only. Unlikely from Gnani itself; a proxy in between could do it, and every other user of the key waits.

**M11. A call interrupted by a server restart stays `active` for ever and cannot be continued or ended.** (helper) After `kill -9` in mid-turn and a restart on the same state directory: a turn, a resend and `/end` all answer 409 `session_not_active`; the log still reads `status active`, `recording null`; the audio of the turn in flight is on disk with no event pointing to it; the dialogue's state is gone. 6 of the 31 sessions already under `.samajh/sessions` are in this state. The phone has no "call lost" screen for it (`web/phone.js:614-618`, read).

**M12. Exactly-once turns depend on the client sending `reply_to`, which the server does not require.** (helper) Ten uploads with no `reply_to` advanced the dialogue ten times; eight at once advanced it four times. The phone and `replay` send it (`phone.js:194`, `replay.py:99`); any other client need not (`app.py:331`).

**M13. `call.wav` is assembled from files, not recorded, and a prompt can go unspoken without the dialogue knowing.** (helper) A prompt whose audio fetch failed and was skipped stays in the log as asked and answered; `CallView` has no "was spoken" flag (`app.py:204-219`). A prompt cut by a hang-up is in `call.wav` in full; speech outside a captured turn is in it nowhere; `at` is when the server logged the event. For an evidence pack the recording and its timestamps are a reconstruction, and a disclosure that was never voiced would look delivered.

**M14. Several guards added by W7's fix round are not pinned by a test.** (helper) 11 of 34 server mutants survive (section 4), among them the one-upload-per-call guard, the session lock around a turn, the 20 s upload deadline, `limit_concurrency`, the ffmpeg codec whitelist and replay's hang-up of a failed call.

### Low

- **L1. Per-model sampling matches by prefix and case.** `openai/gpt-6-luna-mini` and `openai/gpt-6-luna:nitro` silently lose `temperature`; `OpenAI/GPT-6-Luna` would be sent it and get the 404 (`llm.py:68-70`; `w2_fixes_recheck.py`). `samajh/pipeline.py:30-44` still has the older mechanism beside the new one: `default_llm()` makes an uncached, unledgered GET to OpenRouter's model list on every call to decide the same thing.
- **L2. A WAV whose `data` size understates its length passes the 30 s refusal** and is charged for the declared length (31 s of samples declared as 1 s: sent; `w2_fixes_recheck.py`, fix 12). Sizes of 0 and 0xFFFFFFFF are handled. The live path resamples with ffmpeg first, so only direct callers are exposed.
- **L3. The credit guard re-reads and re-parses the whole ledger before every uncached Gnani call, inside the key lock**: 43 ms at 17,046 lines. The ledger is shared with the LLM client and had passed 27,000 lines by the end of this review, so the cost on a live turn grows with every LLM call anyone makes.
- **L4. "नहीं नहीं, सही है" and "गलत नहीं है" at a read-back are read as a rejection** (`w9b_fixes_recheck.py`). It costs the customer one turn.
- **L5. A reply that holds the two-digit year for another reason passes the second check** ("ग्यारह बजे फ़ोन करना" for a 2011 birth year). I could only make it happen for years from 2010, who are not borrowers; "चौरासी लाख का लोन था" does not pass for 1984.
- **L6. The evaluation runner's store lock has a release-then-unlink race**, four behaviours of the audio harness are not pinned by a test (band-limit low edge, transform version in the store key, item id in the fingerprint, an SNR error under 0.3 dB), and a call that is charged and then fails is not counted by the run budget. (helper; the last is documented by the builders)
- **L7. `ruff check` passes; `ruff format --check samajh tests` would reformat 24 files.** Cosmetic. The dialogue package is formatted, as W9 says.

Server and phone (helper; each reproduced by a run unless marked read):
- **L8. A WAV with two `fmt ` chunks is read one way by the server and the client's credit guard (last chunk) and another by ffmpeg (first chunk).** A file the server passes as 30 s is 120 s to ffprobe. Needs a crafted upload; the phone never sends one. What Prisma's decoder does is unknown.
- **L9. Host and Origin parsing is loose** (`127.0.0.1:8191@evil.example`, a missing Origin and `evil://127.0.0.1:8191` are admitted). A browser cannot send those. The one real exception: `testserver` is in the shipped allow-list (`app.py:84`).
- **L10. 40 idle TCP connections make the server answer 503 to everyone**, for as long as they stay open. Local processes only.
- **L11. Anyone holding a session id can stop that call**: about 1,000 failed uploads reach the event limit, after which a genuine turn gets `409 turn_limit`. The id (48 random bits) is the only protection on a session's log and recording, which is adequate on 127.0.0.1 and not with `--host 0.0.0.0`.
- **L12. A missing audio file turns a hang-up into a 500**, and the log in memory then says `ended` while the file on disk does not.
- **L13. `replay` leaves a call `active` when a prompt fetch fails** (it hangs up only when a turn fails).
- **L14. A 120 ms noise burst is sent as a turn** (Node run of `vad.js`); the phone has no request timeout (`web/api.js:15-26`, read) and no barge-in: an answer begun during the prompt's last word loses its start, and a short "हाँ" finished before the microphone opens is lost (`phone.js:164`, `367`, read).
- **L15. Speaker-to-microphone echo and a phone on the LAN** (no microphone outside a secure context) are suspected and were not run.

## 3. Claims checked

"Ran" means a command was run and its output read. "Read" means the primary artifact was read.

| # | Claim | Source | Reproduced | How |
|---|---|---|---|---|
| 1 | The offline suite passes | ORCHESTRATION.md, README | **yes** | `uv run pytest -q`: `3094 passed, 3 deselected in 179.05s`. By directory: audio 32, clients 295, core 1,300, dialogue 673, evalkit 385, extract 176, scenarios 50, server 183 |
| 2 | ruff clean | all reports | **yes** | `uv run ruff check samajh tests eval`: `All checks passed!` |
| 3 | 183 offline server tests and 1 live | voice-loop-iter1.md | **yes** | `183/184 tests collected (1 deselected)` |
| 4 | 417 W8 tests | ORCHESTRATION.md | **yes** | 32 + 385 |
| 5 | 671 dialogue tests | W9 report §2 | **partly** | 673 today; all pass |
| 6 | 289 client tests | W2 report §2 | **partly** | 295 today (the sampling change added tests); all pass |
| 7 | The tests pin the behaviours that matter | implied | **yes** | 18 mutations of clients and dialogue, all killed (section 4). Helpers: audio and evalkit 31 of 35 killed; server 23 of 34 killed |
| 8 | No key in the repo, history, caches, ledgers, session logs or fixtures | W2 report §2 | **yes** | `secret_scan.py`: 21,417 files (451 MB) and all 515 git objects, 0 hits for either key, its first or last 16 characters, its base64 or URL-quoted form. `.env` is not in the git index; `.samajh` is not tracked; `.env` and the ledger are mode 600 |
| 9 | Two or more processes are serialised by the lock | W2 report §2 | **yes** | `gnani_client_offline.py`: 2 and 4 processes on one state dir, peak in flight 1; control with 4 state dirs, peak 4 |
| 10 | A cache hit makes no network call | W2 report §2 | **yes** | same probe: 2 identical calls, 1 request, second booked at 0 credits |
| 11 | The credit guard refuses before the network | W2 report | **yes** | cap 0.025, four 1 s clips: sent, sent, refused, refused; 2 requests; a cached clip still answers. A body of unknown length is charged as 30 s |
| 12 | Retries are bounded | W2 report | **yes** | always-504: 5 requests then `ServerError`; `Retry-After: 86400` is capped at 30 s per wait; a 400 is not retried; connection refused: 5 attempts |
| 13 | A crash leaves a consistent ledger | W2 report | **yes, with a gap** | SIGKILL mid-request and mid-backoff: every ledger line parses, the lock is free in 0.02 s, no half cache entry. The killed request leaves no row (section 5) |
| 14 | One failing call can hold the lock for about 4.5 minutes at the defaults | W2 report §4 | **yes** | read `_runtime.py`: 5 × 30 s timeouts plus up to 4 × 30 s of `Retry-After` |
| 15 | About 115 estimated credits used | ORCHESTRATION.md | **yes** | 114.34 in the ledger today |
| 16 | W2's 13 review fixes hold | W2 report §2 | **yes** | `w2_fixes_recheck.py` with new inputs (section 7) |
| 17 | `openai/gpt-6-luna` is sent no `temperature`; other models are | DESIGN.md §7, defaults.toml | **yes** | request bodies captured with respx: absent for gpt-6-luna, `0.0` for Mistral |
| 18 | The frozen amounts set has sha256 `62b0dd71…5e0d76`, 240 rows | DESIGN.md §6, CLAUDE.md | **yes** | `shasum -a 256 data/amounts/amounts-v1.jsonl`; the generator regenerates it byte for byte (helper) |
| 19 | Phone audio, n = 240: v3.0 parser 221, naive 220; v2.5 parser 214, naive 156 | REPORT.md, README, DESIGN §6 | **yes** | `amounts_recompute.py` on the saved scores (reran it myself): 221 (88-95), 220 (87-95), 214 (85-92), 156 (59-71) |
| 20 | The parser recovers 58 on v2.5, 43 of them fractions; naive never right where the parser is wrong | DESIGN §6 | **yes** | same |
| 21 | v3.0 failures: 17 wrong amounts and 2 no answer; v2.5: 26 failures, 20 no answer | DESIGN §6 | **yes** | same |
| 22 | Skipped-group amounts: v3.0 6 of 16 (18-61) against 161 of 164 (95-99); v2.5 15 of 16 | DESIGN §6, CLAUDE.md | **yes** | same |
| 23 | Fraction sentences, naive: 9 of 60 (v2.5), 54 of 60 (v3.0) | DESIGN §12 | **yes** | same |
| 24 | The two models agree on 200 of 240 and 199 are right; of the other 40, one is right 37 times | DESIGN §6 | **yes** | same |
| 25 | Model gap not established, McNemar p = 0.32 | DESIGN §6 | **yes** | 22 against 15, exact p = 0.324 (exact binomial; the corrected chi-square gives the same) |
| 26 | Clean against phone: 216 and 214 (v2.5), 221 and 221 (v3.0) | DESIGN §6 | **yes** | same |
| 27 | Noise table: cells of 112 to 128; v3.0 babble 5 dB 102 to 93, 12 lost, 3 gained, p = 0.035; v2.5 102 to 97, p = 0.27; ten comparisons | DESIGN §6 | **yes** | same; Bonferroni makes the 0.035 a 0.35 |
| 28 | Every Wilson interval printed in the report | REPORT.md | **yes** (helper) | 496 cells recomputed, 0 differ |
| 29 | After the parser fix: v2.5 phone 224 (1 wrong), clean 225, literal 238; v3.0 phone 222, clean 221; agreement 208 of 209 | DESIGN §6 | **yes** | twice: the helper's rescoring, and my `dialogue_second_reading.py`, which reaches 222/16/2, 224/1/15, 238 and 208 of 209 through the dialogue's own interpreter |
| 30 | `literal` equals the verbatim wording on 112 of 112 phone clips | CLAUDE.md | **yes** (helper) | byte-identical in all 112 |
| 31 | 2,640 transcriptions, 93.74 estimated credits | ORCHESTRATION.md | **yes** (helper) | 2,640 rows; 93.7432 |
| 32 | v2.5 answered 504 on 15 of 1,184 calls, 14 of them Tamil or Kannada; v3.0 once in 1,456 | CLAUDE.md, DESIGN §13 | **yes** | my ledger recount: 15 and 1. Helper: ta 6, kn 8, hi 1; each 504 came after about 5 s and the retry about 30 s later |
| 33 | The phone condition is 8 kHz mu-law | REPORT.md | **yes** (helper) | every sample of 2,160 8 kHz uploads is on the G.711 decode table; uploaded as linear PCM WAV. It is a resample plus G.711, with no band-limit |
| 34 | The noise is mixed at the stated SNR | REPORT.md §7 | **partly** (helper) | exact by the code's definition; not in the speech band (M7) |
| 35 | The harness is resumable and pays for nothing twice | REPORT.md | **yes** (helper) | SIGKILL at 7 points with a fake client: 88 paid calls each time, none twice |
| 36 | The state holds no tested value, so no line can reveal one | W9 report §5 | **yes** | read `machine.py:78-84`; `dialogue_attack.py differential`: 800 paired calls on two records that differ in every tested value, bot lines identical in all, 0 record values spoken |
| 37 | The bot reads back the customer's figure, never the record's | W9 report §5 | **yes** | record 61,000, customer 52,000: the bot reads 52,000 in all four languages |
| 38 | Every call ends | W9 report §5 | **yes** | 4,000 random calls with 0 to 3 products and the budget at 10,000: 0 crashes, longest 41 utterances; 8 adversarial repeats all end |
| 39 | The only line that names OTP, PIN, password or account number is the denial | W9 report §5 | **yes** | read all 51 lines in each of four files |
| 40 | The loan is not named before the checks pass | W9 report §5 | **no, as a property of real calls** | holds for the phrases in the lists; 31 of 34 fresh third-party probes get the loan named (H1) |
| 41 | The bot does not carry on past a refusal | DESIGN §5, W9 report | **no** | 37 of 42 fresh refusals get the next question (H2) |
| 42 | R4: a refusal quoted in an account of the sale does not end the call | W9 report §5 | **partly** | holds for the listed past-tense words; 16 of 21 fresh accounts end the call (H3) |
| 43 | The LLM fallback no longer fails without a trace | W9 report §5, R11 | **yes** | live: pinned Mistral model, 17 turns, 0 failures, 0.55 to 1.93 s a turn. Given the client default `openai/gpt-6-luna` at 512 tokens: 4 turns, 0 failures, 2.1 to 4.1 s a turn. A failed call logs a warning and re-asks (mutation M14 killed) |
| 44 | The second-reading path catches the 3,02,000 case | W9 report §3 | **partly** | yes after the customer rejects the first read-back; with v3.0 first the wrong figure is what gets read back (H4) |
| 45 | The nine gaps of W9 §5 | W9 report | **yes**, all nine | `dialogue_nine_gaps.py`, `dialogue_attack.py` (section 6.3) |

Server and phone rows (helper, fake-backed server on 127.0.0.1:8191 unless noted):

| # | Claim | Source | Reproduced | How |
|---|---|---|---|---|
| 46 | No route returns a key, a server path, a traceback or a cache key | voice-loop §5b | **yes** | 643 raw responses during attacks and a full stub call: 0 hits. A dialogue raising an error with a path and a token in its text reached the phone as `"message":"RuntimeError"` only |
| 47 | No path traversal through session ids, audio names, clip names or static paths | voice-loop §5b | **yes** | 27 ids on 5 routes, 25 audio names, 8 clip names, 33 static paths over raw sockets; a planted file was never served |
| 48 | Uploads over 6 MiB are refused, with or without Content-Length | voice-loop §3 | **yes** | 6 MiB + 1 byte: 413 both ways; 64 MiB chunked: 413 in 0.09 s, server memory 17 to 35 MB |
| 49 | 30.0 s accepted, more refused | voice-loop §5b | **yes** | 240,000 frames: 200; 240,001: 422 `audio_too_long` |
| 50 | Malformed audio is refused cleanly | voice-loop §3 | **yes** | 67 cases (empty, text, truncated or lying headers, MP3/Ogg/WebM/FLAC bytes, odd rates, 1 to 9 channels, 8/24/32-bit): each refused or stored as mono 16-bit at the line rate. Content-Type is ignored on every POST |
| 51 | The same turn posted at once: one 200, the dialogue advances once | voice-loop §3 | **yes, with `reply_to`** | 10 at once: one 200, nine 409, one `dialogue.next`. Without `reply_to`: M12 |
| 52 | A foreign Host or Origin gets 403 | voice-loop §3 | **yes** for what a browser can send | 26 Host and 21 Origin values (L9) |
| 53 | The log stays valid under concurrent use | implied | **yes** | 85,375 reads of `session.json` during a storm of turns, fetches and hang-ups: 0 invalid, sequence numbers contiguous, no 5xx |
| 54 | A session of an earlier run can be read, not continued | voice-loop §6 | **yes** | kill -9 and restart (M11) |
| 55 | One full stub call runs end to end | README, voice-loop §4 | **yes, with the fake client** | `python -m samajh.server.replay tests/fixtures/server/stub-call`: 7 events, 3 turns, ended by the dialogue; `call.wav` is a valid 8 kHz mono WAV of 17.57 s = the clips plus 6 gaps of 0.5 s, every offset in the log matches the samples. The builders' real-Gnani session on disk is 37.32 s with the sha256 the report gives |
| 56 | REST and streaming latency tables; detector table (685 ms at 700 ms; 1 of 4 pause clips cut) | voice-loop §3 | **yes, from the saved rows and a Node rerun** | `server_w7_numbers.py`, `server_vad_pauses.py`. Not rerun against Gnani |
| 57 | "The detector at 700 ms kept the three 600 ms clips whole" | voice-loop §1 | **no, in the browser** | true under Node at 8 kHz; cut in Chrome (H6) |
| 58 | A slow response is cut at the total deadline | voice-loop §5b | **partly** | the body, yes; the headers, no (M10) |
| 59 | The 244-byte WAV declaring 100 MHz "cost ffmpeg 4.2 s and 820 MiB" before the fix | voice-loop §5b | **no** | 0.04 s and 28 MiB with ffmpeg 8.1.2 today; the fix (refused in 0.00 s) holds |

## 4. Tests and mutation

`uv run pytest -q` from a clean invocation, with `SAMAJH_STATE_DIR` pointed at an empty scratch directory: `3094 passed, 3 deselected, 1 warning in 179.05s`. Nothing was written to the scratch state directory, so the tests keep to their own temporary directories.

Mutations (one small edit each, in a scratch copy; `mutation_run.py`; the copy was confirmed to be what Python imported). All 18 of mine were killed:

| # | Behaviour broken | Killed by |
|---|---|---|
| 1 | Credit guard removed | `test_cap_refuses_before_the_network_but_cache_still_answers` |
| 2 | REST call without the cross-process lock | `test_three_processes_sharing_a_state_dir_never_overlap` |
| 3 | Cache never hits | `test_full_job` (first of several) |
| 4 | One retry more than the policy | `test_retry_504_until_budget_spent_raises_server_error` |
| 5 | Key not redacted from error text | `test_the_key_is_in_no_file_and_no_error` |
| 6 | Credits booked on failed attempts | `test_429_then_200` |
| 7 | `temperature` sent to every model | `test_temperature_is_left_out_for_a_model_configured_without_it` |
| 8 | LLM USD cap never refuses | `test_cap_refuses_before_sending_but_cached_requests_still_return` |
| 9 | Wrong person at the first question is not an end | `test_wrong_person_ends_the_call_with_one_neutral_line` |
| 10 | Wrong person passes the second check with the right year | `test_someone_who_says_they_are_not_the_borrower_cannot_pass_the_second_check` |
| 11 | Stop question has no limit | `test_the_stop_question_is_asked_twice_at_most_...` |
| 12 | No turn budget | `test_the_turn_budget_ends_the_call` |
| 13 | Second reading never used | `test_a_turn_typed_as_two_transcripts_is_heard_twice` |
| 14 | A failed LLM call passed over in silence | `test_a_failed_llm_call_is_read_as_unclear_and_the_reason_is_logged` |
| 15 | The lint accepts every line | `test_the_disclosure_denies_what_it_names` |
| 16 | The call keeps the record's premium | `test_an_unclear_answer_is_asked_once_more_...` |
| 17 | A quoted refusal ends the call (R4 undone) | `test_a_refusal_quoted_in_an_answer_is_asked_about_...` |
| 18 | A single digit is a birth year (R2 undone) | `test_a_single_digit_is_not_a_birth_year` |

Audio and evalkit (helper): 31 of 35 killed. Survivors: an SNR error of 0.25 dB (the test tolerance is 0.3), the band-limit's low edge at 200 Hz instead of 300, the transform version left out of the audio-store key, the item id left out of the fingerprint.

Server (helper): 23 of 34 killed. Killed: the Host guard, the Origin guard, the streamed size limit, the 30 s limit, audio served only by a logged name, `reply_to`, resampling to the line rate, and 16 others. Survivors that matter: the one-upload-per-call guard; the session lock around a turn; the 20 s upload deadline; `limit_concurrency=32`; ffmpeg's `-codec_whitelist`; the two-process ffmpeg cap; replay's hang-up of a failed call; replay sending `reply_to`; the `--allow-host` wiring. Two more survivors are benign (a second check behind each still refuses).

What this shows: the tests hold the code to what it does. They cannot show that the word lists cover what people say; H1 to H3 are all "the tested phrases work, fresh ones do not".

## 5. The Gnani client, offline

All from `gnani_client_offline.py` (fake server on 127.0.0.1, fake key, temporary state) unless noted.

- **Serialisation.** 2 and 4 processes sharing a state directory: peak requests in flight 1. Four processes with their own state directories: peak 4. The lock is the file `gnani.lock` in the state directory, so two checkouts or two `SAMAJH_STATE_DIR` values on one machine do not exclude each other.
- **Cache.** Two identical calls: one request, the second a hit booked at 0 credits. The base URL is part of the key.
- **Credit guard.** Refuses before any request once `spent + estimate > cap`. A cached call is never refused. A non-WAV body is charged as 30 s.
- **Retries.** At most 5 attempts; `Retry-After` is honoured up to 30 s; a 400 is not retried.
- **Crash.** A process killed with SIGKILL while its request was in flight leaves 0 ledger rows, a free lock (the next call acquired it in 0.02 s) and no temporary cache file. Killed during backoff: two `504` rows, both parse. Appends are single `O_APPEND` writes.
- **The key.** Sent as `X-API-Key-ID` per request, never as a client default; not followed across a redirect; stripped from the pre-signed storage request even when an injected client carries it by default; redacted from error codes and messages in five error shapes, a non-JSON body and an unparseable 200, including when it straddles the 300-character cut (`w2_fixes_recheck.py`).

**The ledger's estimated total: 114.34 credits** (17,050 lines when counted). Made of: STT v3.0 44.14 (1,554 calls, 4,384 s), STT v2.5 34.07 (1,231 calls, 3,407 s), TTS v3.0 19.98 (227 calls, 9,988 characters), TTS v2.5 10.21 (126 calls), streaming 2.34 (61 sessions, 234 s), the pilot's imported 2.96, Batch 0.63.

**Is the estimate method sound?** As a guard against a 1,000-credit cap with the total near 114: yes, with margin. As an account of what was spent: not established.
1. The two rates (0.010 per audio second, 0.002 per character) come from one pilot dashboard reading of 2.96 credits split "roughly 1.7 / 1.2" off a chart. They have not been checked against the dashboard since, after about 3,100 paid calls. One reading of app.gnani.ai now would replace an estimate that could be 20% off with a measurement.
2. Credits are booked only on a 2xx row. The 16 calls that returned 504 (each after about 5 s of server time), the 7 TTS transport errors and any request in flight when a process dies are booked at 0. Whether Gnani bills them is unknown.
3. Streaming (61 sessions) is booked at the REST rate and Batch is assumed to bill like STT. Both are assumptions the documents already state.
4. Billing is assumed linear in seconds and characters with no per-call minimum or rounding. With a median clip near 2.8 s, a per-call minimum would move the total.
5. `len(text)` counts code points, so a Devanagari conjunct counts as several characters; what Gnani counts is unknown.

## 6. The dialogue

### 6.1 What held

- **No tested value can be revealed.** `CallPlan` keeps the loan id, first name, birth year and product ids only (`machine.py:78-84`). Two records that differ in kind-relevant fields, premium, cover, term, payment source, required flag, provider choice, cancel window, features and consent got word-for-word identical bot lines in 800 paired calls, and none of record B's values appeared in a line.
- **Read-back is the customer's figure** in all four languages, with the record at 61,000 and the customer at 52,000.
- **Every call ends.** 4,000 random calls, 0 crashes, longest 41 utterances. NUL bytes, an emoji, a 5,000-word reply: no crash.
- **Secrets.** No line asks for an OTP, PIN, password, account number or date of birth. The second check asks for the birth year only and says "सिर्फ़ साल, पूरी तारीख़ नहीं".
- **`DESIGN.md` §11 wording.** No line says mis-selling, refund, RBI, "mandatory", states a right, or promises money. The close says the team "may call again"; `end.human` promises a call with no time.
- **No arguing.** After a refusal it recognises, the bot says one line and stops. It gives no reason to stay anywhere.
- **The LLM fallback works with both models today** (claim 43). It is off by default; `step` uses the rules alone unless the adapter passes an interpreter.

### 6.2 What did not hold

H1, H2, H3, H4, M1, M2, M3 and M4 above.

### 6.3 The nine gaps of W9 §5, reproduced and ranked by risk

| Rank | W9 gap | Reproduced | Why this rank |
|---|---|---|---|
| 1 | 9: refusals the rules miss | yes; 37 of 42 fresh | Every call is exposed; the bot breaks the promise it has just made (H2) |
| 2 | 8: a quoted refusal ends the call (Tamil, Kannada) | yes, and wider: Hindi 6 of 6, Hinglish 4 of 5 with present-tense forms | Loses the cases the product exists for (H3) |
| 3 | 1: "मैं रमेश नहीं हूँ पर 1984" passes the second check | yes; also "रमेश तो मेरा भाई है, 1984" and "ये मेरा नंबर नहीं है वैसे, 1984" | The loan is named to a self-declared non-borrower (H1) |
| 4 | 2: another name is a yes at the first question | yes ("मैं सुरेश बोल रहा हूँ", "सुरेश हियर, बोलिए") | The lender and "feedback call" are told to a stranger; the year check still stands in the way of the loan |
| 5 | 3: yes plus another amount replaces the premium | yes; "हाँ सही, बीस हज़ार तो अलग से दिए" makes it 20,000 | A wrong premium reaches the rules unless the customer catches the second read-back (M2) |
| 6 | 6: the bot's words show a product is on the record | yes; after "कुछ नहीं लिया, बस लोन" the bot says "अब लोन के साथ जो चीज़ ली गई…" and with an empty record it does not | Tells the customer the answer to open recall one turn late, and colours the nine answers that follow |
| 7 | 5: "कुछ नहीं दिया", "फ्री था" re-asked, then unresolved | yes | A clear answer is pressed once; the case goes to a human with the words kept |
| 8 | 7: the lint is a word list | yes; 11 of 16 fresh bad lines pass | Latent until someone edits a prompt (M9) |
| 9 | 4: "no fifty five thousand" costs a turn | yes | One extra turn |

### 6.4 W9b's fixes (R1 to R11)

| Fix | Verdict | Evidence |
|---|---|---|
| R1 wrong person at all three opening steps | **partly** | mutation 10 killed; listed phrases end the call; 31 of 34 fresh ones do not (H1) |
| R2 a single digit is not a birth year | **holds** | mutation 18 killed; 15 fresh replies, only 2010-and-later years pass by accident (L5) |
| R3 third-person replies are not a yes | **partly** | same list as R1 |
| R4 quoted refusal gets the stop question | **partly** | mutation 17 killed; 16 of 21 fresh accounts still end the call (H3) |
| R5 stop question asked twice at most | **holds** | mutation 11 killed; alternating "रहने दो" / "नहीं" ends in 9 to 11 utterances |
| R6 a correction is not answered with the same figure | **holds** | "अरे नहीं भाई, पचपन था" and "बावन नहीं, बयालीस" get the restate question; but see M2 for replies that repeat the figure |
| R7 "पता नहीं" at a read-back is not a no | **holds** | "याद नहीं आ रहा अब", "मालूम नहीं जी…" are recorded and not pressed |
| R8 second reading | **holds as coded; the order matters** | mutation 13 killed; H4, M1 |
| R9 lint extended | **partly** | M9 |
| R10 short refusals get the stop question | **partly** | H2 |
| R11 fallback names its model, leaves room, logs failure | **holds** | live run; mutation 14 killed |

### 6.5 Hindi and Hinglish lines, as heard on a phone

Read line by line. Nothing was voiced, so how Timbre says "ए-आई", "ओ-टी-पी", a Latin-script name inside a Devanagari sentence, or "3,02,000" is unknown.

| Line | Problem | Kind |
|---|---|---|
| `right_party.reask` "यह एक ऑटोमेटेड कॉल है। क्या {first_name} जी लाइन पर हैं?" | Asks whether he is there, not whether the speaker is he. "हाँ हैं" from anyone in the house is a yes | **ambiguous; opens H1** |
| the disclosure, seven lines, 672 characters in Hindi | About 45 to 60 seconds of speech before the customer may say a word, to someone who has only said "हाँ" to a first name. Many will hang up or talk over it, and the phone has no barge-in | stiff |
| `disclosure.verify` "{lender} के काग़ज़ों पर छपे कस्टमर केयर नंबर" | "the bank's papers" is vague because the loan may not be named yet; a listener will ask "कौन से काग़ज़?" | ambiguous |
| `second_check.reask` "ठीक से सुनाई नहीं दिया" | Said also when the year was heard and was wrong. An assistant that has just promised accuracy says something untrue | stiff |
| `open_recall.ask` "लोन के साथ आपने और क्या-क्या लिया, और कितने का?" | "और क्या-क्या" presupposes that something was taken. It is the design's own wording (§5 step 5), and it leans on the `recall` rule's answer | **leading** |
| `teach_back.intro` "अब लोन के साथ जो चीज़ ली गई…" | Tells a customer who has just said "कुछ नहीं लिया" that something was taken | leading (W9 gap 6) |
| "वो चीज़" in ten lines running | "that thing… that thing…" is evasive and slightly comic to the ear; a customer who does not know of any product will ask "कौन सी चीज़?" each time. This is the price of naming no product | stiff |
| `provider_choice.ask` "वो चीज़ कहाँ से लेनी है, इस बारे में आपको क्या बताया गया था?" | "लेनी है" is future or obligation for something already bought; it sounds like "where must you collect it". The re-ask line is the clear one | **ambiguous** |
| `required_for_loan.ask` "…ज़रूरी था, या आपकी मर्ज़ी थी? आपको क्या बताया गया था?" | Two questions in one; a bare "हाँ" is accepted (M3) | ambiguous |
| `cover.ask` "उस चीज़ से आपको क्या मिलता है, और कितनी रक़म तक?" | "कितनी रक़म तक" dangles, hints that a capped benefit exists, and invites a second amount that later muddles the read-back | leading, mildly |
| `cancel_window.ask` "क्या आपको बताया गया था कि… कैंसल करा सकते हैं या नहीं? और अगर हाँ, तो कब तक?" | "नहीं" can mean "I was not told" or "I was told it cannot be cancelled" | ambiguous |
| `consent.ask` "…किन-किन चीज़ों के लिए हाँ की थी, और हाँ कैसे की थी?" (Hinglish: "हाँ कैसे बोला था?") | "How did you say yes?" will get "बोलकर" or "ख़ुशी से", not "signed" or "OTP". No wording both avoids leading and gets the method; the re-ask ("आपकी हाँ कैसे ली गई थी?") is better | ambiguous |
| `read_back.confirm` "आपने बताया था बावन हज़ार, यानी 52,000। क्या यह सही है?" | Spoken, it is the same number twice. It does not say what the number is for (M2) | **ambiguous** |
| `features.ask` "अगर आप यह पैसा वापस लेना चाहें…" | "यह पैसा" has no referent if the customer said they paid nothing | ambiguous |
| `end.human` "हमारी टीम से कोई आपको कॉल करेगा" | A promise with no time, made even before the right party is confirmed | note |

The Hinglish file carries the same problems; its code-mixing reads naturally ("Confirm करने के लिए बस अपना birth year बता दीजिए"). The Tamil and Kannada files share `right_party.reask` ("…லைனில் இருக்கிறார்களா?", "…ಲೈನಿನಲ್ಲಿ ಇದ್ದಾರೆಯೇ?") and call the product "பொருள்" and "ವಸ್ತು" (an object); both remain not human-reviewed.

## 7. Fix rounds that had no independent review

**W2, 13 fixes** (`w2_fixes_recheck.py`, new inputs; respx, fake keys):

| Fix | Verdict | What I tried |
|---|---|---|
| 1, 10 gzip and in-body errors | holds | a body that is not gzip: typed `TransportError` after 5 attempts, 5 ledger rows; a gzip 200 with an in-body 502 that echoes the key: 5 retries, `ServerError`, key redacted |
| 2, 7 Batch billing and resume | holds by reading | `client.py:621-741`; the two crash windows the report names are real and small |
| 3 redaction | holds | key in the code, the message, the location, straddling the cut, in HTML, in an unparseable 200: no leak to any file or message |
| 4 malformed keys | holds | newline, leading space, NBSP, tab, empty, non-ASCII: `ConfigError`, key not in the message |
| 5 TTS body checks | holds | JSON with an audio type, wrong sample rate, no samples, wrong content type, empty: `BadResponse`, nothing cached, credits still booked |
| 6 LLM cap | holds, conservatively | cap 0 sends nothing; with 0.03 spent of 0.05 the next call is refused because the largest call seen is 0.03 |
| 8 redirects and the storage request | holds | a 302 to another host is not followed even by an injected client that follows redirects; the key header is not sent to storage |
| 9 `nan` cap | holds | `nan`, `inf` and negative are refused |
| 11 cache key | holds | 0 and 0.0 share a key; the base URL is in it |
| 12 WAV length | holds for sizes 0 and 0xFFFFFFFF | L2 |
| 13 three surviving mutants | holds | my mutations 1 to 3 of the same kind are killed |

**The LLM client's per-model sampling change:** works as described (claim 17, mutation 7). Two small things in L1.

**W9b's fixes:** section 6.4.

**W8, 8 fixes** (helper): the report names seven items plus the ffmpeg note, not eight. Fingerprint includes the transform version: holds (the audio-store half is unpinned). Torn last line: holds. One run per store: partly (L6). Budget after a crash: holds for the stated case. Mutants: 7 of 8 killed again. Stratum tables on phone only: holds, untested. "The parser was edited during the run and no score moved": cannot be checked (no earlier parser or scores). Tool versions recorded: holds, though the one `runs.jsonl` row is from a later no-call rerun.

**W7, 11 fixes** (helper; fake-backed server, scratch copies):

| Fix | Verdict | Evidence |
|---|---|---|
| 1 a resent turn advanced the dialogue twice | holds when the client sends `reply_to` | 10 simultaneous copies: one 200, one `dialogue.next`; in Chrome with the reply dropped, "Send again" got the stored reply. The upload guard and lock are unpinned; without `reply_to`: M12 |
| 2 total deadline on a response | **partly** | body yes, headers no (M10) |
| 3 a lying WAV header cost ffmpeg seconds and memory | **partly** | the check holds; two `fmt ` chunks get past it at a cost of 0.24 s and 267 MiB. The original cost did not reproduce |
| 4 false `block_align` passed the cap and the 30 s limit | **partly** | `block_align` 1, 4, 2000 are refused or resampled; the two-`fmt` file passes as 30 s (L8) |
| 5 repeated prompt fetches filled the log | holds for that case | 20 fetches, 1 error event; failed uploads still fill it (L11) |
| 6 bodies buffered with no deadline | holds, unpinned | a stalled body gets 408 at 20.0 s; three mutants survive |
| 7 Host and Origin check; finished calls dropped first | holds for a browser | L9 |
| 8 a late microphone grant attached a dead track | holds by reading | not run |
| 9 `eos_wait_ms` grew on an error screen | holds by reading | not run |
| 10 non-PCM decoder inside a WAV | holds | MP3, ADPCM, A-law, extensible subformats: 422. For two-`fmt` files only ffmpeg's codec whitelist stands in the way, and no test pins that flag |
| 11 replay left a failed call active; a prompt was synthesised after a hang-up | **partly** | failed STT: ended; prompt after hang-up: 409 and no TTS call; failed prompt fetch: left active (L13) |

## 8. Integration: what the adapter must do

The server asks a `Dialogue` for `next(call: CallView, heard: Heard | None) -> BotUtterance` (`samajh/server/dialogue.py`). The dialogue offers `start(record, language, lender_name=…)` and `step(state, text, second_reading=…, interpreter=…)`. Between them:

**Changes the server needs first (an adapter alone cannot do these)**
1. **Two readings.** `Heard` has `text`, `literal` and `detected_language`; the server makes one STT call per turn with the session's one model (`app.py:367-369`). The dialogue must be able to say "this turn carries a figure" (it knows: `expecting(state.position)` is `amount` or `confirmation`), and the server must make the second call and hand both over. Either `BotUtterance` gains a field such as `second_reading: bool` and `Heard` gains `second: str | None`, or the server always makes two calls.
2. **Order.** Pass **v2.5 as `customer_text` and v3.0 as `second_reading`** on figure turns (H4), or change the machine. `DESIGN.md` §7 says the opposite. A cheaper variant, in-sample only: v2.5 alone returns `text` and `literal` from one call, and `literal` alone held the right figure on 238 of 240.
3. **A missing second reading is `""`, not `None`.** With `None` the turn leaves no `SecondReading` at all; `""` records a disagreement, which is what `DESIGN.md` §13 asks for.
4. **Timeout for the second call.** The live profile allows 2 attempts with an 8 s deadline each (`speech.py:44-46`), and v2.5's 504s arrive after about 5 s. Two calls run one after the other under the one-slot lock. Nothing sets a shorter limit for the second reading yet.
5. **The 600-character limit.** The disclosure is 672 to 864 characters. Raise the limit or let `next` return several utterances; the protocol has no way to speak twice without a customer turn between, so "send lines one by one" (W9 §6) is not possible today.
6. **The 40-turn limit** against 43 customer turns for two products (25 for one product, so the demo record fits).

**What the adapter itself must do**
7. Keep one `CallState` per session. The server holds `Dialogue` objects in memory only; after a restart the state is gone unless the adapter stores `state.model_dump_json()` somewhere it can read back.
8. Map languages: `hi` → `hi-IN`, `hi-en` → `hi-en`, `ta` → `ta-IN`, `kn` → `kn-IN`. For `hi-en` the server already sends v3.0 the list `hi-IN,en-IN` and v2.5 `hi-IN`.
9. `heard is None` → `start`; `Heard.text == ""` → `step(state, "")`.
10. `EndOfCall` → `BotUtterance(end_call=True)` with the closing lines; then hand `EndOfCall.transcript` to `samajh.pipeline` after the call, with `Turn.start_s` and `end_s` filled from the session log (the dialogue leaves them `None`).
11. Put `Line.key`, `step`, `asks` in `tags`. `tags` is `Mapping[str, str]`, so a `None` product id must be left out.
12. Choose the interpreter. With the rules alone, H2 applies in full. With the LLM fallback, add 0.5 to 2 s of silence per unlabelled turn (Mistral) and build the `LlmClient` with a short timeout and one attempt: the default is 60 s and 5 attempts, and `next` "must not block for long".
13. Supply `lender_name`; `LoanRecord` has none.
14. Decide what a silent line does (M4): the dialogue will not end the call for it.

**Mismatches that will bite later**
- Read-backs and the first-name line cannot be pre-generated; each is a Timbre call on the turn path, taking the same key lock as STT.
- The session's STT `format` is fixed per session. Amount turns want `transcribe`; nothing else in the call needs digits.
- Nothing has been voiced. Whether Timbre reads "यानी 3,02,000" as the amount, and the Indian digit grouping correctly, decides whether the read-back can do the job H4 leaves to it.

**Found by attacking the server (helper), each of which the adapter or its wiring must handle**
- **`next()` can be called twice for one customer turn.** If anything fails after `next()` returns (an utterance over 600 characters, a language the session cannot transcribe, a later error), the log does not advance and the resend calls `next()` again with the same view (`app.py:242-251`, `388-391`; I read this). An adapter that has already stepped its `CallState` would step it twice. Key the stored state on `len(call.exchanges)`, or derive it from the view.
- **`python -m samajh.server` registers only the stub** (`__main__.py:26`), and the page sends only `line_rate` and `stt_model` (`web/phone.js:127`): there is no way to choose a dialogue, a record or a language from the phone.
- **Per-turn STT is not the dialogue's to set.** Model per session; format always `transcribe`; language follows the prompt; no keyterms. The TTS voice is fixed (`timbre-v3.0`, Shivani) and the prompt is synthesised on the browser's first fetch of its audio, not on the turn.
- **`Heard(text="")` covers both "no speech for 8 s" and "Prisma returned nothing".** The dialogue cannot tell them apart.
- **No time limit on `next()`.** It runs holding the call's lock; a log read waited 1.7 s behind a 2 s turn. An LLM fallback inside it stalls the turn for as long as the client allows.
- **A prompt that was never voiced looks answered** (M13). The adapter cannot know the disclosure was heard.
- **The phone sends one turn per end of speech**, and at a pause near 600 ms that is half an answer (H6). The dialogue will read a truncated amount as the amount.

## 9. What the amounts numbers can and cannot support

They show, for one chain (Timbre TTS → simulated channel → Prisma → parser, 240 generated sentences with one amount each): v2.5 `transcribe` leaves fraction words in front of digits; v3.0 `transcribe` writes wrong digits with no sign of it, mostly on amounts that skip a group; the two models fail on different sentences.

They do not show: any rate for human callers (16 TTS voices, 15 sentences each; "upper bound" is plausible and unmeasured); independence from the vendor (STT and TTS are both Gnani's); behaviour on a real phone line or in real noise (the "phone" condition is a resample plus G.711, the noise is modulated synthetic noise with no talkers, at a nominal level: M7); correctness of the Tamil and Kannada sentences (not human-reviewed, and 180 of the 240 sentences take their number words from tables the parser shares); anything about replies with two numbers, a correction or a hesitation; and the after-fix numbers are in-sample. Nothing in them supports skipping the read-back when two readings agree (M8).

Sentences in `eval/amounts/REPORT.md` that say more than the data: "Two readings that agree are almost always right" (phone cell only); "the one miss is a sentence whose written form is suspect" (not shown); "the phone channel costs nothing measurable" (the channel is a resample plus G.711); "an upper bound on what a real caller would get" (asserted); "8 of the 19 are proven formatting errors" (7 are mechanically; the eighth rests on a non-fluent Kannada reading).

## 10. Numbers in `DESIGN.md` and `README.md` I could not reproduce

| Number | Where | Why not |
|---|---|---|
| "1,223 core tests pass" | README, ORCHESTRATION.md | `tests/core` collects 1,300 today (out of my scope; all pass) |
| "671 passed" for the dialogue | W9 report | 673 today |
| Credit rates 0.010 per second and 0.002 per character; "about 0.02 credits per 3-second STT call (n = 78)" | DESIGN §8, CLAUDE.md | a dashboard reading with no saved screenshot; no API reports cost |
| STT and TTS latencies; phone end to end median 1.18 s; detector median 685 ms; streaming 0.78 s against 0.71 s; "3 of 12 live phone turns failed with `gnani_busy`" | DESIGN §8 and §13, README | need live Gnani calls, which this review was barred from. The saved raw rows do reproduce the REST, streaming and detector tables (row 56) |
| "8 of the 19 are proven formatting errors" | DESIGN §6 | 7 confirmed mechanically |
| "The detector at 700 ms kept the three 600 ms clips whole"; "the 700 ms detector split only the 900 ms one" | voice-loop §1, DESIGN §15 item 12b | true under Node at 8 kHz; in Chrome 600 ms pauses were cut in 7 of 8 runs (H6) |
| "61 sessions and 234 s of audio" of streaming | DESIGN §15 item 12c | the saved rows hold 59 stream rows and 230.0 s, plus 4 edge rows (helper); the ledger holds 61 rows and 234 s |
| "4.2 s and up to 820 MiB" for the 100 MHz WAV; worst-case lock hold "about 16 s" | voice-loop §5b | 0.04 s and 28 MiB today; the 16 s bound does not cover slow headers (M10) |
| Parser hash `efbd312d…` and "no score moved" while the parser was edited during the run | REPORT.md | the before-fix parser is not in the working tree |
| "extrapolated to 95 to 107" credits | REPORT.md §1 | method not stated |
| Fallback numbers: fold 1 155 and 187 of 199; latency median 0.74 s | W9 report §4 | not rerun (it would spend on about 400 calls); my 17-turn live run took 0.55 to 1.93 s a turn |
| "LLM extraction … median 1.88 s", the text-path results, the scenario-set numbers | DESIGN §7 and §9, README | part 1's scope |
| The 20-sentence pilot figures | DESIGN §5, §12 | a different run; not rechecked |

Everything else about amounts in `DESIGN.md` §6, §8, §12 and §13 and in `README.md` reproduced (section 3, rows 18 to 33).

Two statements in `DESIGN.md` that the code contradicts: §6 "the second reading is what catches it" (not in the order §7 gives: H4), and §5 step 9 "Someone from our team will call you within N days" (the close says "may call again"; W9 documents this).

## 11. Verdict

**Not yet sound enough to wire into a full voice call; sound enough to build the adapter against.** The lower layers held up: the Gnani client serialises processes, never pays twice, refuses at the cap and leaks no key; the transport survived path traversal, oversized and malformed uploads, concurrent turns and a restart without corrupting a log; the evaluation numbers all recount from the saved artifacts; and 72 of 87 mutations across the scope are killed by the tests. The dialogue's structural promises also hold: it cannot reveal a record value, it reads back only what the customer said, and it always ends. What fails is everything that depends on a word list meeting a person. On fresh inputs the bot named the loan to 31 of 34 people who had said they were someone else, asked the next question after 37 of 42 refusals, and hung up on 16 of 21 customers who were describing the sale. Those are the three harms the design names as the ones to avoid, and none of them is rare phrasing. Around that sit two faults in the amount path, which is the one path the design measured most carefully: in the documented order of readings the second reading never changes what is read back (16 wrong figures held in 240, against 2 with the order reversed), and in Chrome the phone cuts an answer at a 600 ms pause and loses the rest. And the transport cannot yet carry the dialogue: the disclosure is longer than an utterance may be, a turn has one reading, and nothing registers the dialogue with the server. Before a full call is wired: change who is believed at the opening (a speaker must claim to be the borrower, not merely fail to deny it, and the re-ask must ask that), stop on any reply the interpreter cannot place as an answer at least to the point of asking, put v2.5 first or re-ask on disagreement, extend the protocol for a second reading and a long first utterance, and record human pauses before trusting the 700 ms detector. Every number here is from synthetic text or TTS audio and from probes written by a reviewer, so the counts show that the faults exist, not how often a real caller will meet them.
