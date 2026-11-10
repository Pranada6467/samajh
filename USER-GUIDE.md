# Samajh: what you personally need to do

Written 2026-11-10 by the guide agent, from the repo as it stood that evening. Other agents are still building, so anything marked **coming** is not ready: do not do it yet. Where the project has not decided something, this guide says "undecided" and lists the question in section 5. Suggestions that are mine, not the project's, are marked "(guide's suggestion)".

Package names used below: **P1** = the real call on the browser phone, **P2** = the reworded, shorter call, **P4** = the human calls, **P7** = demo video and submission. State of each: `ORCHESTRATION.md`, "Iteration 2 state".

## 1. What I need from you, at a glance

| # | Task | Why it matters | Possible when | Time | Done looks like |
|---|---|---|---|---|---|
| 1 | Read the STT and TTS totals off the Gnani dashboard | Every credit figure in the project is an estimate. One reading turns them into measurements | Now | 5 to 10 min | Dashboard numbers, the time, and the ledger output sent to the coordinator |
| 2 | Line up one to three friends and get their consent | The human calls cannot happen without people. The judge calls them the single most valuable evidence | Now | 30 min of messages | Each person has said yes in writing to the points in §2.3 |
| 3 | Review the Hindi and Hinglish wording of the bot's lines | No fluent human has read any line. The judge found the wording stiff where it matters | **Coming**: after P2 writes `references/pilots/P2-lines-for-review.md` (not there yet) | About 1 to 2 hours (guide's estimate) | Every line marked keep, change or unsure |
| 4 | Listen to the bot's voice reading the lines | Nobody has checked by ear how Timbre says the Hinglish lines, "ए-आई" or "ओ-टी-पी" | **Coming**: after P1 voices the lines. How you will listen is undecided | Undecided | Undecided |
| 5 | Make the human calls (P4) | Answers both objections at once: "synthetic voices" and "you scripted the customers" | **Coming**: after P1 and P2 are built and verified | About 2 hours with the friends (judge's estimate) | 20 calls made, each logged, failures included |
| 6 | Perform and post the demo video; submit the written explanation (P7) | It is the submission | **Coming**: last | Undecided | Video posted with the tags; written explanation sent |
| 7 | Make the decisions in §2.5 | Only you can: name, award category, friends in the video, team and contributions | Now; needed before P7 | 30 min of thought | Each answer told to the coordinator |
| 8 | Rotate the Gnani and OpenRouter keys | Both keys were pasted into a chat transcript | At the end of the build | 10 min | Old keys revoked, new ones in `.env` |
| 9 | Keep the agents running | Workers stop when the account's usage limit is hit and do not restart themselves | Throughout | A glance now and then | Coordinator session open; stalled work resumed |
| 10 | Be able to explain the project yourself | Internships are decided in individual interviews | Any time | A few hours of reading | You can explain the rule, the call and the main finding without notes |

## 2. The tasks, step by step

### 2.1 Dashboard reading (now)

No API reports credit cost. The dashboard at app.gnani.ai is the only source. The project's guard runs on rounded-up estimates (0.010 credits per STT audio second, 0.002 per TTS character) from one earlier reading of a chart, so each rate could be 20% off or more.

1. Tell the coordinator you are about to take the reading. A quiet moment (no agent calling Gnani) is best. If that is not possible, note the time to the minute.
2. Sign in at app.gnani.ai and find the usage or credits view. I have not seen the dashboard; the pilot read its split "off a chart".
3. Write down: total credits used, STT credits, TTS credits. If Batch or streaming is shown separately, write those too. Say whether each number is exact or read off a chart.
4. Straight away, in the repo folder, run `uv run python -m samajh.clients.gnani ledger`. It only reads a local file and makes no API call. It prints a short JSON block (when I ran it: `est_credits_spent` 270.59 of the 1,000 cap). Copy all of it.
5. Send the coordinator: date and time (IST), the dashboard numbers, and the ledger block. A screenshot is fine if no API key is visible in it.

Do not edit `samajh/clients/defaults.toml` yourself. An agent will work out the rates and update it.

### 2.2 Hindi and Hinglish wording review (coming, do not start yet)

**What it will be.** P2 will write `references/pilots/P2-lines-for-review.md`: the bot's lines for you to read. It does not exist yet (checked). The lines themselves live in `data/prompts/hi.toml` and `hi-en.toml`. **Do not edit those files.** They are guarded by a lint and tests, and P2 is rewriting them now. Tamil and Kannada are out of scope for you: the project has cut them to an experimental appendix.

**How to mark it up.** If the file has its own marking instructions, follow those. If not, add one line directly under each bot line, starting with `REVIEW:` and one of three words:

```
REVIEW: keep
REVIEW: change to "आपने लोन के साथ जो लिया था, वो आपके हिसाब से क्या है?"
REVIEW: unsure - sounds like a riddle, but I can't think of a better line
```

Rules for the markup, so an agent can apply it without asking you anything:
- Mark every line, including the ones you keep. An unmarked line reads as "not reviewed".
- A `change to` gives the complete new line in quotes, not a description of the change.
- Keep any `{slot}` placeholders (for example the first name, the lender, an amount) exactly as they are.
- A reason after a dash is welcome and optional.

**What to look for** (the judge's examples, and the design's own open checks):
- Lines that read as a riddle. The judge's example: "आपके हिसाब से वो चीज़ क्या है?". The bot must never name the product, and this is the price of that.
- Stiff or bookish Hindi that nobody says on a phone call. Hinglish that mixes the two languages in a way no real caller would.
- Length. The judge found the old opening was a one-minute monologue. Flag any line that is too long to listen to.
- Anything that sounds like a scam call or a sales call, or that would make you hang up.
- Words Timbre may say badly: mixed-script lines, "ए-आई", "ओ-टी-पी". Flag them; task 4 is where you hear them.

**What your new wording must not do.** These are hard rules (`CLAUDE.md`, `data/prompts/`), and an agent will reject a change that breaks one:
- No digits. No product words: insurance, policy, premium, cover, FD, deposit (in any language).
- No hint of how it was paid for or how consent was given (for example "sign", "form").
- No statement of a right, and no promise of money back.
- Never ask for an OTP, PIN, password, account number or date of birth. The second check asks for the year of birth only.

**When you are done:** save the file and tell the coordinator. An agent applies the changes, reruns the tests, and comes back only about your `unsure` lines.

**To get a feel for the call today (optional).** You can play the call as text in the terminal. It uses no Gnani credits and no network:
`uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi` (or `--lang hi-en`). You type the customer's replies. P2 is changing this code right now, so it may be mid-edit or briefly broken. Do not start the review from it; wait for the file.

### 2.3 The human calls (coming, do not make them yet; you can recruit now)

**What the judge asked for.** 20 improvised calls in Hindi and Hinglish, by you and one to three consenting friends, through the real browser phone, each from a brief card, scored against the card. The design's bar for calling a language "supported" is at least 10 real-voice calls in it. The exact split between Hindi and Hinglish and the mix of customer types are **undecided** (section 5). The judge's own test calls used these types, so expect cards like them: a misled customer, a carefully informed customer, an ordinary informed customer who is unsure of the exact figures, one who says "I took nothing", one in a hurry, one who asks "is this a fraud call?", and a family member answering someone else's phone.

**Who can take part.** You, and adults (18+) who agree. The challenge's own wording is "record yourself or your teammate with consent". The project reads that as covering consenting friends for evaluation. Whether a friend who is not on your team may appear in anything public is your decision (§2.5).

**What each person must be told and agree to.** The project has no consent form yet; how consent is recorded is **undecided**. Until the coordinator says otherwise (guide's suggestion): send each person the points below as a message, get a written "yes, I agree" back, and keep a screenshot on your laptop, outside the repo.
- What it is: a student project for Gnani AI's internship challenge. They play an invented bank customer on a short test call with a bot.
- The whole call is recorded. Their voice is personal data under India's DPDP Act.
- Where it goes: the audio is sent to Gnani's speech API to be transcribed. The text of what they say is sent to AI models through OpenRouter. The recording is kept on your laptop.
- It is not put in the public repo and not shown in the video unless they separately say yes to that.
- Whether short written quotes of what they said may appear in the project's public report (without their name). Ask yes or no.
- They can stop at any time, and can ask you later to delete their recordings.
- They will play a made-up person. They must not say their real name, bank, loan, phone number, account number, Aadhaar, PAN or any other real detail. The bot never asks for an OTP, PIN, password or account number; if anything on the call seems to, they should not answer, and you note it.

**What a brief card is.** One card per call. It tells the caller who they are playing and what they believe, and they answer in their own words. It is not a script: nothing on it is read aloud. The real cards are **coming** (agents write them in P4). An illustration, built on the phone's existing demo record "Ramesh: a gold loan and one add-on":

```
CARD H-01 (example only)                         Language: Hinglish
You are Ramesh. If asked, your year of birth is 1984. (An invented person.)
Your story: last month you took a gold loan of about five lakh. At the branch the
officer said you also had to open an FD "for loan security". About fifty-two thousand
was cut from the loan money for it. You signed many pages without reading them.
You believe the money is yours and you can take it out later.
How you talk: friendly, a little busy, short answers, Hindi mixed with English.
Rules: answer from this story in your own words. If the card does not cover a
question, say what this person would honestly say ("pata nahi" is a fine answer).
Never say anything real about yourself.
```

**Equipment and room.**
- Chrome on the laptop that runs the server. Nothing else is tested: no human has used the phone yet, and Safari, mobile browsers, real microphones, echo and noisy rooms are all untested. Friends sit at your laptop; remote calling is not set up.
- Allow the microphone when Chrome asks. The page turns on the browser's echo cancellation, noise suppression and auto gain.
- Headphones or the laptop speaker: **undecided**. Headphones avoid the bot's voice leaking into the microphone, which is the untested echo case. The recording is put together by the server from the bot's audio and your microphone turns, so headphones do not remove the bot from the recording.
- Quiet room or realistic noise: **undecided**. Whatever is chosen, write the room and noise on the log for each call.
- The page has four options: line (8 kHz phone line or 16 kHz), loan record, language, and turn mode (hands-free or push to talk). Which to use for the 20 calls is **undecided**. Never pick Tamil or Kannada.

**How to start the phone** (verified against the code and `--help`; needs `GNANI_API_KEY` in `.env` and ffmpeg):
1. Tell the coordinator the time of your calling session first. Gnani allows one request at a time for the whole key. If an agent runs an evaluation during your call, your turns fail with `gnani_busy`.
2. In the repo folder: `uv run python -m samajh.server --port 8085`
3. Open `http://127.0.0.1:8085/` in Chrome. Pick the record and language the card names. Press "Place demo call", then "Answer".
4. Every call spends Gnani credits. The code on disk now starts the Samajh call by default, but P1 is mid-build and unverified, and `README.md` still describes the older three-question stub. **Wait for the coordinator to say P1 and P2 are verified before making any call that counts.**

**Keep a log line for every call**, written during or right after it: card number, who spoke (a code such as F1, not a name), language, start time, room and noise, headphones or speaker, page options, and what went wrong if anything. Where this log should live is **undecided**; until told, keep it in a notes file outside the repo.

**If a call goes wrong.** Failures are evidence. The project reports them; it does not hide them.
- Do not quietly redo a call to get a cleaner one. The first attempt counts. If you repeat a card, log it as a second attempt.
- Write down what happened before you press anything. If a turn fails, the page offers "Send again" and "Record the turn again": you may use them, and you log that you did.
- If the bot mishears, cuts you off, hangs up early or says something odd, carry on as the character would, then log it.
- If you see `gnani_busy`, stop. An agent is using the key. Tell the coordinator.
- Never delete, rename or edit a session.

**What happens to the recordings.** Each call is saved under `.samajh/sessions/<session id>/`: `call.wav` (the whole call), `audio/` (one file per turn), `session.json` (the log) and `case.json` (the result). `.samajh/` and all `.wav` files are ignored by git, so they stay on your laptop and out of the repo. Leave them where they are; agents score them there. Nothing from a friend goes public unless that person agreed to it.

### 2.4 Demo video and submission (coming, last)

**What the challenge requires** (`RESEARCH.md` §1):
- A working app shown in a public demo video, posted on LinkedIn and/or X, tagging Gnani AI, with `#GnaniAI` and `#GreatIndianAIInternshipChallenge` (use exactly this hashtag; some of Gnani's own posts drop the "AI").
- One nominated post link per platform.
- A written explanation: title, problem, target users, the Gnani models and APIs used with exact versions, and each member's contribution.
- Solo or a team of two; Indian college students, 18+.
- Only engagement recorded by the closing cutoff counts for internship selection. The closing date is not written down anywhere in the repo (section 5).

**The 60-second structure the judge proposed** (`references/reviews/iter1/judge.md` §4):
1. 0 to 5 s: one line of the RBI rule (85Y) and the date 1 January 2027.
2. 5 to 15 s: the usual confirmation call. "Aapne policy li hai?" "Haan." Confirmed. Caption: this customer was told it is an FD.
3. 15 to 40 s: the Samajh call on the browser phone, **a real human voice in Hinglish**. "Loan ke saath aapne kya-kya liya?" "Ek FD, security ke liye, bavan hazaar." Split screen: the record, the quote lighting up against it, the two Prisma readings of the amount side by side, then the read-back.
4. 40 to 50 s: the reviewer's card, then the half-yearly report page.
5. 50 to 60 s: two numbers with their n and source, then "Prisma v2.5 and v3.0, Timbre v3.0, Prisma Batch".

**What you do yourself.** You are the human voice in step 3 (or a consenting person is: §2.5). You post from your own LinkedIn or X account and nominate the link. You read and approve every claim in the written explanation, and you write the contributions part. Who records the screen and who edits the video is **undecided**.

**What the agents prepare.** The working call, the reviewer card and the report page shown on screen; the numbers with their caveats; a two-page brief; a draft of the written explanation; a last check of every claim against `references/claims/claims-ledger.md`. No real phone number, account number or other real detail may appear on screen or in the audio.

### 2.5 Decisions only you can make

Tell the coordinator each answer. None blocks the build today; all are needed before P7.

| Decision | Options | Recommendation on file |
|---|---|---|
| Final name | Keep "Samajh" (the working name) or pick another | Judge: defer, it is not a constraint. It must be fixed before the video and the written title |
| Award category (a team can win only one) | Real Deal; Demo Day Drop; Jugaad Genius; others in `RESEARCH.md` §1 | Design and judge: **Real Deal**, with the video cut so it can also stand for Demo Day Drop. Judge's best alternative: Jugaad Genius (two Prisma versions checked against each other as the confidence score Prisma does not return). Frame the user as the borrower who was sold an "FD" |
| Whose voice is in the public video | (a) only yours; (b) a friend's, with their explicit written yes to public use | None on file. Note: the challenge wording is "record yourself or your teammate with consent", and (a) plainly fits it (guide's observation) |
| Team and contributions | Solo, or a team of two (this also decides Solo Ninja versus Two-Person Army eligibility) | None on file. The written explanation must state each member's contribution. Coding agents wrote most of the code, so decide how you describe your own part accurately; you will be interviewed on it |
| Tamil and Kannada | Stay cut (experimental appendix), or revive | Coordinator and judge: cut, because no fluent reader exists. Only reopen if you or a friend reads one fluently and will review it |

### 2.6 Housekeeping

**Rotate the keys at the end.** Both the Gnani and the OpenRouter key were pasted into a chat transcript, so treat them as exposed. Do it when the build is finished, not before: every agent reads the keys from `.env`, and a mid-build change stops their work. At each provider, create a new key and revoke the old one. Put the new keys in `.env` (it is ignored by git). Never paste a key into a chat again. Then ask the coordinator to confirm the app still runs. Do this before the repo or the video goes public. The repo has no git remote today (checked), so nothing has been published yet.

**Keep the session open.** The coordinator starts workers and is woken when they finish. Keep the Orca app and the coordinator's session open, and the laptop awake, while agents run.

**Usage limits.** Workers have stopped without warning several times when the account's 5-hour usage limit was reached (packages W1, W5, W9 and the iteration-2 workers). A stopped worker does not wake up by itself. The coordinator has to stop it, save a checkpoint, and start a fresh worker that resumes from what is on disk. What you can do:
- Expect pauses. A stall usually means the limit, not a bug.
- After the limit resets, ask the coordinator to check which workers stopped and to resume them.
- Fewer workers at once last longer (the coordinator's own lesson). If stalls keep happening, ask it to run fewer packages in parallel.
- Avoid other heavy use of the same account while agents are building (guide's suggestion).

**Be ready to explain it (task 10).** Selection ends in individual interviews, and Gnani sells mostly to banks, lenders, insurers and contact centres. Read `README.md`, `DESIGN.md` §1 to §5, and the judge's review §1 and §2. Know the lead finding and its limits. The judge also says to read the saved Gnani page on banking feedback calls (claims ledger item C2.7) before the interview.

## 3. What you do not need to do

- Write or fix code, tests, prompts files or documents. Do not edit `data/prompts/` or `defaults.toml`.
- Run tests, evaluations or anything under `eval/`. Never run `tests/clients/probes/gnani_probe.py`.
- Write the brief cards, score the calls, or build the tables. Agents do that from your recordings and log.
- Run git commands. The coordinator commits.
- Check regulatory claims or sources. The claims ledger and an agent cover that.
- Accept dataset terms for the public real-voice data. That evaluation has already run; its data is on your laptop only.
- Review Tamil or Kannada.
- Watch the credit budget. The client enforces the 1,000 cap.

## 4. Things you can prepare today

1. **Take the dashboard reading** (§2.1). It is the only task fully ready now.
2. **Ask one to three friends.** Explain the ask in two lines: a short role-play call with a bot, in Hindi or Hinglish, about two hours in total at your laptop, recorded, with a made-up identity. Send them the consent points from §2.3. Find out who is comfortable in Hindi and who in Hinglish.
3. **Check Chrome and a microphone.** Make sure Chrome is installed and that the laptop's microphone setting allows Chrome. Find a pair of wired headphones in case they are chosen. Do not place phone calls for this yet: they spend credits and can collide with running agents.
4. **Draft your one-line description of the project.** A starting point from the README: "a callback in which a borrower explains in their own words what they bought with their loan, and plain code compares that with the bank's record". Do not claim nobody else does this: adjacent vendors exist.
5. **Think about the decisions in §2.5**: name, category, whose voice, team and contributions.
6. **Optional:** play the text call once (§2.2, last paragraph) to hear what the bot asks.
7. **Start the interview reading** (§2.6, last paragraph).

## 5. Questions the coordinator must answer before you start

1. **Closing date.** When do submissions and the engagement cutoff close? It is not in the repo.
2. **Where the submission goes.** Is there a form for the written explanation and the nominated links? Does the entrant name an award category, or do the judges assign it?
3. **Wording review format.** Will `P2-lines-for-review.md` carry its own marking instructions, or should the `REVIEW:` convention in §2.2 be used? When will the file be ready?
4. **Listening pass.** Where will the voiced lines be, and how should problems be reported? Should the user also choose the bot's voice by ear (the settings file says nobody has compared the voices)?
5. **Call plan.** How many friends, how the 20 calls split between Hindi and Hinglish, and which customer types in what numbers. Who writes the cards, and when.
6. **Phone options for the calls.** 8 kHz or 16 kHz line, hands-free or push to talk, headphones or speaker, quiet room or realistic noise.
7. **Consent.** Is the written-message approach in §2.3 enough, or will there be a form? Where are the consent records kept?
8. **The call log.** Where should the user's per-call log live, and in what format, so the scoring agent can read it?
9. **Use of friends' recordings.** May a friend who is not a team member be recorded at all under the challenge's "yourself or your teammate" wording? May anonymous quotes from their transcripts appear in the public report? How are recordings deleted if someone withdraws?
10. **Go signal.** How will the user be told that P1 and P2 are verified and human calls may start?
11. **Video production.** Who screen-records and edits, with what tool, and who voices the "usual confirmation call" in step 2 of the video?
12. **Publishing the repo.** Will the repo be made public for the submission? If so, the keys must be rotated first and friends' audio must stay out.
13. **Dashboard reading.** Is one reading enough, or is a second one wanted after the human calls?
