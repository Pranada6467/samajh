# Samajh: what you personally need to do

**Status (2026-11-10, kept current by the coordinator):** human calls are NOT open yet. Ready now: the dashboard reading, recruiting friends, the decisions in §2.5, and two short answers for the coordinator (§2.7: what the phrase "teen lakh chalis" means, and a go-ahead to copy two reports into the repo). **Hold the wording review (§2.2) until the P2 fix round lands:** an independent check found the call not ready for a live line, its lines are being changed, and `references/pilots/P2-lines-for-review.md` will be regenerated; the coordinator will say when to start. The listening pass and the calls wait for packages P1 and P2 to be verified. Keep the consent messages, the call log and friends' audio in `.samajh-human/` at the repo root; git ignores that folder.

Written 2026-11-10 by the guide agent, from the repo as it stood that evening, and updated the same day with the coordinator's answers. Other agents are still building, so anything marked **coming** is not ready: do not do it yet. What is still open is in section 5. Suggestions that are mine, not the project's, are marked "(guide's suggestion)".

Package names used below: **P1** = the real call on the browser phone, **P2** = the reworded, shorter call, **P4** = the human calls, **P7** = demo video and submission. State of each: `ORCHESTRATION.md`, "Iteration 2 state".

## 1. What I need from you, at a glance

| # | Task | Why it matters | Possible when | Time | Done looks like |
|---|---|---|---|---|---|
| 1 | Read the STT and TTS totals off the Gnani dashboard, twice | Every credit figure in the project is an estimate. A reading turns them into measurements | First reading now; second after the human calls | 5 to 10 min each | Dashboard numbers, the time, and the ledger output sent to the coordinator |
| 2 | Line up one to three friends and get their consent | The human calls cannot happen without people. The judge calls them the single most valuable evidence | Now | 30 min of messages | Each person has sent a written yes to the points in §2.3 |
| 3 | Review the Hindi and Hinglish wording of the bot's lines | No fluent human has read any line. The judge found the wording stiff where it matters | **Hold**: do not start until the coordinator says the P2 fix round has landed; `references/pilots/P2-lines-for-review.md` exists but its lines are changing | About 1 to 2 hours (guide's estimate) | Every line marked keep, change or unsure |
| 4 | Listen to the bot's lines and pick its voice | Nobody has checked by ear how Timbre says the lines, or compared the voices | **Coming**: after P1 pre-generates the bot's audio, the coordinator gives you a local page | Not estimated | A voice chosen per language; lines that sound wrong noted |
| 5 | Make the human calls (P4) | Answers both objections at once: "synthetic voices" and "you scripted the customers" | **Coming**: on the coordinator's go signal (P1 and P2 verified) | About 2 hours with the friends (judge's estimate) | 20 calls made, each with a row in the log, failures included |
| 6 | Record and post the demo video; submit the written explanation (P7) | It is the submission | **Coming**: last | Not estimated | Video posted with the tags; written explanation sent |
| 7 | Make the decisions in §2.5 | Only you can: name, award category, voices, team, publishing the repo | Now; needed before P7 | 30 min of thought | Each answer told to the coordinator |
| 8 | Rotate the Gnani and OpenRouter keys | Both keys were pasted into a chat transcript | At the end of the build | 10 min | Old keys revoked, new ones in `.env` |
| 9 | Keep the agents running | Workers stop when the account's usage limit is hit and do not restart themselves | Throughout | A glance now and then | Coordinator session open; stalled work resumed |
| 10 | Be able to explain the project yourself | Internships are decided in individual interviews | Any time | A few hours of reading | You can explain the rule, the call and the main finding without notes |
| 11 | Read the closing date and submission steps off the challenge page | Nobody in the project knows them (section 5) | Now | 10 min | Date and steps told to the coordinator |
| 12 | Tell the coordinator what the spoken phrase "teen lakh chalis" means: 3,40,000 or 3,00,040 | It decides whether 14 of the 40 held-out number-formatting failures count as errors (section 2.7) | Now | 2 min | One line to the coordinator |
| 13 | Say yes or no to copying two finished reports into the repo (`eval/amounts_v2/REPORT.md` and `references/pilots/gnani-number-formatting-report.md`) | They are written and sit in the coordinator's scratchpad until you agree | Now | 2 min | A yes or a no to the coordinator |

## 2. The tasks, step by step

### 2.1 Dashboard reading (now)

No API reports credit cost. The dashboard at app.gnani.ai is the only source. The project's guard runs on rounded-up estimates (0.010 credits per STT audio second, 0.002 per TTS character) from one earlier reading of a chart, so each rate could be 20% off or more.

1. Tell the coordinator you are about to take the reading. A quiet moment (no agent calling Gnani) is best. If that is not possible, note the time to the minute.
2. Sign in at app.gnani.ai and find the usage or credits view. I have not seen the dashboard; the pilot read its split "off a chart".
3. Write down: total credits used, STT credits, TTS credits. If Batch or streaming is shown separately, write those too. Say whether each number is exact or read off a chart.
4. Straight away, in the repo folder, run `uv run python -m samajh.clients.gnani ledger`. It only reads a local file and makes no API call. It prints a short JSON block (when I ran it: `est_credits_spent` 270.59 of the 1,000 cap). Copy all of it.
5. Send the coordinator: date and time (IST), the dashboard numbers, and the ledger block. A screenshot is fine if no API key is visible in it.

Do not edit `samajh/clients/defaults.toml` yourself. An agent will work out the rates and update it.

Take one reading now and a second, the same way, after the human calls.

### 2.2 Hindi and Hinglish wording review (coming, do not start yet)

**What it will be.** `references/pilots/P2-lines-for-review.md`: the bot's lines for you to read. A copy exists now, but the lines are still changing: wait until the coordinator regenerates it and tells you to start. The lines themselves live in `data/prompts/hi.toml` and `hi-en.toml`. **Do not edit those files.** They are guarded by a lint and tests, and P2 is rewriting them now. Tamil and Kannada are out of scope for you: the project has cut them to an experimental appendix.

**How to mark it up** (convention confirmed by the coordinator). Add one line directly under each bot line, starting with `REVIEW:` and one of three words:

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
- Words Timbre may say badly: mixed-script lines, "ए-आई", "ओ-टी-पी". The listening pass below is where you hear them.

**What your new wording must not do.** These are hard rules (`CLAUDE.md`, `data/prompts/`), and an agent will reject a change that breaks one:
- No digits. No product words: insurance, policy, premium, cover, FD, deposit (in any language).
- No hint of how it was paid for or how consent was given (for example "sign", "form").
- No statement of a right, and no promise of money back.
- Never ask for an OTP, PIN, password, account number or date of birth. The second check asks for the year of birth only.

**When you are done:** save the file and tell the coordinator. An agent applies the changes, reruns the tests, and comes back only about your `unsure` lines.

**The listening pass (coming, after P1 pre-generates the bot's audio).** The coordinator will give you a local page that plays each line, with two or three candidate Timbre voices per language.
1. Pick the voice you prefer by ear for Hindi and for Hinglish, and tell the coordinator.
2. For any line that sounds wrong (a mispronounced word, an odd pause, wrong stress), add a line under it in the same review file with a `LISTEN:` prefix, for example `LISTEN: "ओ-टी-पी" is read as one word`. Lines that sound fine need no `LISTEN:` line.

**To get a feel for the call today (optional).** You can play the call as text in the terminal. It uses no Gnani credits and no network:
`uv run python -m samajh.dialogue play --record tests/dialogue/fixtures/record_gold_loan.json --lang hi` (or `--lang hi-en`). You type the customer's replies. P2 is changing this code right now, so it may be mid-edit or briefly broken. Do not start the review from it; wait for the file.

### 2.3 The human calls (coming, do not make them yet; you can recruit now)

**The plan** (set by the coordinator, from the judge's request). 20 improvised calls by you and one to three consenting friends, through the real browser phone, each from a brief card, scored against the card. Each speaker uses whichever of Hindi or Hinglish is natural to them; aim for roughly half the calls in each. The design's bar for calling a language "supported" is at least 10 real-voice calls in it.

| Calls | Customer type on the card |
|---|---|
| 6 | Misled: told it was an FD; or the premium was taken from the loan without their knowing; or never agreed to anything |
| 4 | Ordinary informed: knows roughly what they bought, not every figure |
| 3 | Well informed |
| 2 | Says they took nothing |
| 2 | Someone who is not the borrower answers |
| 1 | Busy, asks to be called later |
| 1 | Suspects a fraud call |
| 1 | Coached: was told to say yes to everything |

**You do not record anything yourself.** The call is a live conversation with the bot in Chrome on your laptop. The page takes the microphone, and the server saves the whole call by itself (see "What happens to the recordings"). WhatsApp voice notes and iPhone Voice Memos cannot be used: a recorded message is not a conversation, because the bot's next line depends on what it just heard and when the speaker stopped. Each person sits at your laptop for their calls; calling from another place or from a phone is not set up.

**No script for the speakers.** They get a brief card and answer in their own words. A scripted call would bring back the objection these calls exist to answer ("you scripted the customers"). What you can prepare is what you say to them: the invitation and consent message, and a two-minute briefing before their first call (how the page works, play the person on the card, never say anything real, "I don't know" is a fine answer).

**Practice calls** (decided by the coordinator). Each speaker makes one practice call before their counted calls, on the record "Ramesh: a gold loan and one add-on". It is logged with card id `practice-hero` and left out of every number. You may make a handful of practice calls now, with these limits:
- Use the server that is already running. Do not restart it: a restart would load call code that an agent is editing.
- If a bot line sounds odd, note it. It may be a mid-edit artefact, not a finding.
- Stop when the coordinator says in chat that re-voicing or an evaluation is starting, until it says the key is clear.
- A practice call is described only as "practice, n = 1, not scored", never as a result.

**Who can take part.** You, and adults (18+) who agree; family members count the same as friends. The challenge's own wording is "record yourself or your teammate with consent". The coordinator's recommendation follows from it: friends' recordings are used for the evaluation numbers only, stay on your machine, and never enter the repo or the video; the public video uses only your own voice. Whether to list a friend as a team member is your decision (§2.5).

**What each person must be told and agree to.** A written message from each person saying yes to the points below is enough; no form is needed. Send the points, get a written "yes, I agree" back, and keep the messages (screenshots or exports) in a local folder outside the public repo. Keep them in `.samajh-human/` at the repo root: git ignores that folder (checked in `.gitignore`), so nothing in it is published. Create it if it is not there.
- What it is: a student project for Gnani AI's internship challenge. They play an invented bank customer on a short test call with a bot.
- The whole call is recorded. Their voice is personal data under India's DPDP Act.
- Where it goes: the audio is sent to Gnani's speech API to be transcribed. The text of what they say is sent to AI models through OpenRouter. The recording is kept on your laptop.
- It is used only to measure how well the project works. It is never put in the public repo or in the video.
- Whether short written quotes of what they said may appear in the project's public report, without their name. Ask for a clear yes or no in their message: quotes are used only if they said yes.
- They can stop at any time. If they withdraw later, their recordings are deleted and their calls are dropped from the numbers (the report states how many calls were dropped).
- They will play a made-up person. They must not say their real name, bank, loan, phone number, account number, Aadhaar, PAN or any other real detail. The bot never asks for an OTP, PIN, password or account number; if anything on the call seems to, they should not answer, and you note it.

**What a brief card is.** One card per call. It is a fact sheet, not a script: it gives the speaker everything their character knows, in plain words, and marks what the character does not know. The speaker needs no knowledge of loans or insurance. They say those facts in their own words, the way they would on a real call, and nothing on the card is read aloud. Not knowing an answer is realistic and useful: "pata nahi" is a valid reply. An agent writes the real cards before the go signal; you do not write them. An illustration, built on the phone's existing demo record "Ramesh: a gold loan and one add-on":

```
CARD H-01 (example only)                         Language: Hinglish
You are Ramesh, born 1984. (An invented person.)
What happened: last month you took a gold loan of about five lakh from your bank.
What you know:
- The officer said you also had to open an FD "for loan security".
- About fifty-two thousand was cut from the loan money for it.
- He said without it the loan would not be passed.
- You signed many pages at the branch. Nobody explained them.
- You believe the money is yours and you can take it out later.
What you do not know: how long it runs, whether you could cancel it, what you get from it.
How you talk: friendly, a little busy, short answers, Hindi mixed with English.
Rules: say these things in your own words. For anything not on the card, say what
this person would honestly say. Never say anything real about yourself.
```

The bot asks about the same topics on every call: who you are, your year of birth, what you took with the loan and for how much, what that thing is, how and how often it was paid for, whether it was required, what you get from it, how long it runs, whether you could cancel, what happens if you want the money back, and what you agreed to. A real card covers each of these, as something the character knows or does not know.

**Equipment and room.**
- Chrome on the laptop that runs the server. Nothing else is tested: no human has used the phone yet, and Safari, mobile browsers, real microphones, echo and noisy rooms are all untested. Friends sit at your laptop; remote calling is not set up.
- Allow the microphone when Chrome asks. The page turns on the browser's echo cancellation, noise suppression and auto gain.
- Two setups, about half the calls in each: (a) headphones in a quiet room; (b) the laptop speaker in an ordinary room. Setup (b) is the untested echo case, where the bot's voice can leak into the microphone, so it is tested on purpose. Write the setup in the log for each call.
- The recording is put together by the server from the bot's audio and your microphone turns, so headphones do not remove the bot from the recording.
- Page options for every call: line **8 kHz · phone line**, turn mode **Hands-free** (not push to talk), the loan record and language the card names. Never pick Tamil or Kannada.

**How to start the phone** (verified against the code and `--help`; needs `GNANI_API_KEY` in `.env` and ffmpeg):
1. Wait for the go signal. The coordinator tells you in chat and updates the Status line at the top of this file.
2. Tell the coordinator the time of your calling session first. Gnani allows one request at a time for the whole key. If an agent runs an evaluation during your call, your turns fail with `gnani_busy`.
3. In the repo folder: `uv run python -m samajh.server --port 8085`
4. Open `http://127.0.0.1:8085/` in Chrome. Pick the record and language the card names. Press "Place demo call", then "Answer". When the call ends, copy the id shown beside "Session" into the log, and wait until the "Case file" box on the page has finished before the next call (guide's suggestion: the after-call work also uses the Gnani key).
5. Every call spends Gnani credits. The code on disk now starts the Samajh call by default, but P1 is mid-build and unverified, and `README.md` still describes the older three-question stub. **Wait for the coordinator to say P1 and P2 are verified before making any call that counts.**

**The "who to play" note stays on screen.** The page shows a note under the header (for example "Play Ramesh, born 1984, ...") from the start screen through the whole call. The three demo records: "Ramesh: a gold loan and one add-on" and "Ramesh: a sale he understood" are both Ramesh, born **1984**; "Sunita: someone else answers" is Sunita, born 1979, and there you play a family member who picks up her phone.

**Keep a call log**: one CSV file in `.samajh-human/`, beside the consent messages, one row per call, written during or right after it. A failed call gets a row too. Columns:

```
date,time,card_id,speaker_initials,language,setup,session_id,note
2026-11-14,16:05,H-01,RK,hi-en,headphones quiet room,<the session id the phone shows>,bot cut me off on the amount answer
```

`setup` is headphones or speaker, plus the room. `note` is free text on anything that went wrong; leave it empty if nothing did. The example row is invented.

**If a call goes wrong.** Failures are evidence. The project reports them; it does not hide them.
- Do not quietly redo a call to get a cleaner one. The first attempt counts. If you repeat a card, log it as a second attempt.
- Write down what happened before you press anything. If a turn fails, the page offers "Send again" and "Record the turn again": you may use them, and you log that you did.
- If the bot mishears, cuts you off, hangs up early or says something odd, carry on as the character would, then log it.
- If you see `gnani_busy`, stop. An agent is using the key. Tell the coordinator.
- Never delete, rename or edit a session. The one exception is a person who withdraws: then tell the coordinator, and their session folders are deleted and their calls dropped from the numbers, with the count stated.

**What happens to the recordings.** Each call is saved under `.samajh/sessions/<session id>/`: `call.wav` (the whole call), `audio/` (one file per turn), `session.json` (the log) and `case.json` (the result). `.samajh/` and all `.wav` files are ignored by git, so they stay on your laptop and out of the repo. Leave them where they are; agents score them there. A friend's audio never goes public. A short anonymous quote from a friend's transcript appears in the report only if that person said yes to quotes in their consent message.

### 2.4 Demo video and submission (coming, last)

**What the challenge requires** (`RESEARCH.md` §1):
- A working app shown in a public demo video, posted on LinkedIn and/or X, tagging Gnani AI, with `#GnaniAI` and `#GreatIndianAIInternshipChallenge` (use exactly this hashtag; some of Gnani's own posts drop the "AI").
- One nominated post link per platform.
- A written explanation: title, problem, target users, the Gnani models and APIs used with exact versions, and each member's contribution.
- Solo or a team of two; Indian college students, 18+.
- Only engagement recorded by the closing cutoff counts for internship selection. Nobody in the project knows the closing date or the submission steps: read them off the challenge page (section 5).

**The 60-second structure the judge proposed** (`references/reviews/iter1/judge.md` §4):
1. 0 to 5 s: one line of the RBI rule (85Y) and the date 1 January 2027.
2. 5 to 15 s: the usual confirmation call. "Aapne policy li hai?" "Haan." Confirmed. Caption: this customer was told it is an FD.
3. 15 to 40 s: the Samajh call on the browser phone, **a real human voice in Hinglish**. "Loan ke saath aapne kya-kya liya?" "Ek FD, security ke liye, bavan hazaar." Split screen: the record, the quote lighting up against it, the two Prisma readings of the amount side by side, then the read-back.
4. 40 to 50 s: the reviewer's card, then the half-yearly report page.
5. 50 to 60 s: two numbers with their n and source, then "Prisma v2.5 and v3.0, Timbre v3.0, Prisma Batch".

**What you do yourself.**
- Screen-record the browser while the pages play. QuickTime is enough.
- Speak the borrower's part in step 3, in your own voice (the coordinator's recommendation: only your voice in the public video).
- Edit the video, or hand the raw recordings to an agent, which can cut and caption them with ffmpeg.
- Post from your own LinkedIn or X account and nominate the link.
- Read and approve every claim in the written explanation, and write the contributions part.

**What the agents prepare.** The shot list, the script, the on-screen captions and the pages to record (the working call, the reviewer card, the report page); the "usual confirmation call" in step 2, voiced with Timbre; the numbers with their caveats; a two-page brief; a draft of the written explanation; a last check of every claim against `references/claims/claims-ledger.md`. No real phone number, account number or other real detail may appear on screen or in the audio.

### 2.5 Decisions only you can make

Tell the coordinator each answer. None blocks the build today; all are needed before P7.

| Decision | Options | Recommendation on file |
|---|---|---|
| Final name | Keep "Samajh" (the working name) or pick another | Judge: defer, it is not a constraint. It must be fixed before the video and the written title |
| Award category (a team can win only one) | Real Deal; Demo Day Drop; Jugaad Genius; others in `RESEARCH.md` §1 | Design and judge: **Real Deal**, with the video cut so it can also stand for Demo Day Drop. Judge's best alternative: Jugaad Genius (two Prisma versions checked against each other as the confidence score Prisma does not return). Frame the user as the borrower who was sold an "FD" |
| Whose voice is in the public video | (a) only yours; (b) also a teammate's or friend's | Coordinator: **(a), only your own voice.** The challenge wording covers recordings of yourself or your teammates. Friends' recordings are for the evaluation numbers only |
| Team and contributions | Solo, or a team of two (this also decides Solo Ninja versus Two-Person Army eligibility). Whether to list a friend who records as a team member | None on file; your decision. The written explanation must state each member's contribution. Coding agents wrote most of the code, so decide how you describe your own part accurately; you will be interviewed on it |
| Publish the repo | Public, or keep it private | Coordinator: **yes, publish**, since build quality is the point. Only after both keys are rotated (§2.6), and with friends' audio and the real-voice dataset material kept out (both are already gitignored) |
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

### 2.7 The order from here (coordinator, 2026-11-10)

No clock times: each step depends on verification results and the account's usage limit.
1. **Now:** recruit and collect consent messages; take the dashboard reading; answer the "teen lakh chalis" question below; optional practice calls; fill in `.samajh-human/practice-call-1-check.md` for your first practice call.
2. **On the coordinator's word:** the wording review. Wait: the lines are still changing, and the coordinator will regenerate the review file and tell you.
3. **After the final lines are re-voiced:** the listening page.
4. **Then:** the brief cards arrive, then the go signal (P1 and P2 verified), then the 20 calls.

Two more things the coordinator is waiting on from you (`ORCHESTRATION.md`, "Waiting on the user"):
- **A language question.** When someone says "teen lakh chalis", do they mean 3,40,000 or 3,00,040? Your answer decides whether 14 of 40 number-formatting failures count.
- **A go-ahead** to copy two finished reports into the repo: `eval/amounts_v2/REPORT.md` and `references/pilots/gnani-number-formatting-report.md`.

## 3. What you do not need to do

- Write or fix code, tests, prompts files or documents. Do not edit `data/prompts/` or `defaults.toml`.
- Run tests, evaluations or anything under `eval/`. Never run `tests/clients/probes/gnani_probe.py`.
- Write the brief cards, score the calls, or build the tables. Agents do that from your recordings and log.
- Write the video's shot list, script or captions, or voice the confirmation call in it.
- Run git commands. The coordinator commits.
- Check regulatory claims or sources. The claims ledger and an agent cover that.
- Accept dataset terms for the public real-voice data. That evaluation has already run; its data is on your laptop only.
- Review Tamil or Kannada.
- Watch the credit budget. The client enforces the 1,000 cap.

## 4. Things you can prepare today

1. **Take the first dashboard reading** (§2.1).
2. **Read the challenge page** (gnani.ai/internship and the challenge blog) for the closing date, the engagement cutoff, how the written explanation and post links are submitted, and whether you name an award category yourself. Tell the coordinator (section 5).
3. **Ask one to three friends.** Explain the ask in two lines: a short role-play call with a bot, in Hindi or Hinglish, about two hours in total at your laptop, recorded, with a made-up identity. Send them the consent points from §2.3 and collect each written yes. Find out who is more natural in Hindi and who in Hinglish; the aim is roughly half the calls in each.
4. **Check Chrome, a microphone and headphones.** Make sure Chrome is installed and that the laptop's microphone setting allows Chrome. Have a pair of headphones ready: half the calls use them. Do not place phone calls for this yet: they spend credits and can collide with running agents.
5. **Draft your one-line description of the project.** A starting point from the README: "a callback in which a borrower explains in their own words what they bought with their loan, and plain code compares that with the bank's record". Do not claim nobody else does this: adjacent vendors exist.
6. **Think about the decisions in §2.5**: name, category, whose voice, team and contributions, publishing the repo.
7. **Optional:** play the text call once (§2.2, last paragraph) to hear what the bot asks.
8. **Start the interview reading** (§2.6, last paragraph).

## 5. Still open

**For you to find out and tell the coordinator.** The coordinator does not know these; they are on the challenge page (gnani.ai/internship, and the challenge blog linked in `RESEARCH.md` §1).
1. The closing date for submissions, and the cutoff after which engagement on your post no longer counts.
2. How the submission is made: where the written explanation and the nominated post links go, and whether you name an award category yourself or the judges assign one.

**For the coordinator to supply.**
3. The go signal for the human calls: given in chat and in the Status line at the top of this file.
4. The local listening page, once P1 has pre-generated the bot's audio.
5. The brief cards, before the go signal. Each card should cover every topic the bot asks about, as a fact the character knows or a stated "does not know".

**For you to decide** (§2.5): the final name, the award category, team and contributions, and whether to publish the repo.
