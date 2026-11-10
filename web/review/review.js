// The review pages: reviewer queue, one case, the sample and attempt log, the half-yearly report.
// Every label for a rule, tier, outcome or decision is the server's (samajh/ops/views.py).
// Nothing here decides anything: a referral asks a person to look, and the decision is theirs.

const API = "/api/review";
const DASH = "\u2014";

// ---------------------------------------------------------------- fetch

class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function api(path, options) {
  let res;
  try {
    res = await fetch(API + path, { headers: { Accept: "application/json" }, ...options });
  } catch {
    throw new ApiError(0, "no_answer", "The review server did not answer.");
  }
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const err = (body && body.error) || {};
    throw new ApiError(res.status, err.code || String(res.status), err.message || `The server answered with status ${res.status}.`);
  }
  if (body === null) throw new ApiError(res.status, "not_json", "The server's answer could not be read.");
  return body;
}

// ---------------------------------------------------------------- DOM

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

function facts(pairs) {
  return h("dl", { class: "facts" }, pairs.filter(Boolean).map(([k, v]) => [h("dt", null, k), h("dd", null, v)]));
}

// cols: [{label, num, head, wide, cls}]; rows: [{cells: [...], cls}] or {group: "label"}.
// `stack` turns each row into a card on a phone; the roles keep the table semantics when it does.
function table({ cols, rows, caption, stack = false, long = false }) {
  const role = (r) => (stack ? r : null);
  const head = h(
    "thead",
    { role: role("rowgroup") },
    h("tr", { role: role("row") }, cols.map((c) => h("th", { scope: "col", role: role("columnheader"), class: c.num ? "num" : null }, c.label))),
  );
  const body = h(
    "tbody",
    { role: role("rowgroup") },
    rows.map((row) => {
      if (row.group) return h("tr", { class: "group" }, h("th", { colspan: cols.length, scope: "colgroup" }, row.group));
      return h(
        "tr",
        { role: role("row"), class: row.cls },
        row.cells.map((cell, i) => {
          const c = cols[i];
          const cls = [c.num && "num", c.wide && "wide", c.cls].filter(Boolean).join(" ") || null;
          const inner = stack ? h("div", { class: "cell" }, cell) : cell;
          return c.head
            ? h("th", { scope: "row", role: role("rowheader"), class: cls, "data-label": c.label }, inner)
            : h("td", { role: role("cell"), class: cls, "data-label": c.label }, inner);
        }),
      );
    }),
  );
  return h(
    "div",
    { class: stack ? "table-wrap stack" : "table-wrap", tabindex: stack ? null : "0", role: stack ? null : "group", "aria-label": stack ? null : caption || "Table" },
    h("table", { role: role("table"), class: long ? "long" : null }, caption ? h("caption", null, caption) : null, head, body),
  );
}

// ---------------------------------------------------------------- formatting

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// "2027-02-08" and "2027-02-08T10:15:00" both give "8 Feb 2027". Read from the string, so no time zone shifts the day.
function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : DASH;
}

function fmtDateTime(iso) {
  const t = /T(\d{2}):(\d{2})/.exec(iso || "");
  return t ? `${fmtDate(iso)}, ${t[1]}:${t[2]}` : fmtDate(iso);
}

const int = (n) => Number(n).toLocaleString("en-IN");
const inr = (n) => "\u20B9" + Number(n).toLocaleString("en-IN");
const yesNo = (b) => (b ? "Yes" : "No");
const words = (key) => {
  const s = String(key).replaceAll("_", " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
};
const days = (n) => `${int(n)} ${n === 1 ? "day" : "days"}`;

function mmss(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// A Proportion is never shown as a bare percentage: the count and its n always travel with it.
const pCount = (p) => `${int(p.count)} of ${int(p.n)}`;
const pShare = (p) => (p.n === 0 || p.share === null ? DASH : `${Math.round(p.share * 100)}%`);
const pInterval = (p) => (p.n === 0 || p.low === null || p.high === null ? DASH : `${Math.round(p.low * 100)} to ${Math.round(p.high * 100)}%`);
const pBoth = (p) => (p.n === 0 || p.share === null ? pCount(p) : `${pCount(p)} (${pShare(p)})`);

const LANGUAGE_NAMES = { hi: "Hindi", "hi-en": "Hinglish", ta: "Tamil", kn: "Kannada" };
const LANG_ATTR = { hi: "hi", "hi-en": "hi", ta: "ta", kn: "kn" };
const LENDER_TYPES = { bank: "Bank", nbfc: "NBFC" };
const languageName = (code) => LANGUAGE_NAMES[code] || code;

const sevLabel = (severity) => h("span", { class: `sev sev-${severity}` }, words(severity));
const simTag = () => h("span", { class: "tag sim" }, "Simulated");
const caseHref = (id) => `case.html?id=${encodeURIComponent(id)}`;

function remember(key, value) {
  try {
    if (value === undefined) return window.localStorage.getItem(key) || "";
    window.localStorage.setItem(key, value);
  } catch {
    // storage is off or full: the page works without it
  }
  return "";
}

// ---------------------------------------------------------------- header

const NAV = [
  ["queue", "index.html", "Reviewer queue"],
  ["attempts", "attempts.html", "Sample and attempts"],
  ["report", "report.html", "Half-yearly report"],
];

function renderHeader(batch, page) {
  const lender = batch ? batch.meta.book.lender_name : null;
  const header = document.getElementById("site-header");
  // h() drops the empty children, so the header is built inside one element and moved over.
  const parts = h(
    "div",
    null,
    h(
      "div",
      { class: "head-row" },
      h("div", { class: "brand" }, "Samajh ", h("span", null, "post-sale feedback review")),
      lender ? h("div", { class: "lender" }, lender) : null,
    ),
    h(
      "nav",
      { class: "site-nav", "aria-label": "Review pages" },
      NAV.map(([key, href, label]) => h("a", { href, "aria-current": key === page ? "page" : null }, label)),
      page === "case" ? h("span", { "aria-current": "page" }, "Case") : null,
    ),
    batch && batch.simulated_notice
      ? h("div", { class: "sim-band", role: "note" }, h("p", null, h("strong", null, "Simulated"), batch.simulated_notice))
      : null,
  );
  header.replaceChildren(...parts.childNodes);
}

function showError(main, err) {
  const known = err instanceof ApiError;
  const advice =
    known && err.status === 409
      ? ["No batch has been run on this server yet. Run ", h("code", null, "uv run python -m samajh.ops demo"), " first, then reload this page."]
      : known && err.status === 0
        ? ["Check that the server is running (", h("code", null, "uv run python -m samajh.server --port 8085"), "), then reload this page."]
        : known && err.status === 404
          ? ["Go back to the ", h("a", { href: "index.html" }, "reviewer queue"), " and open the case from there."]
          : ["Reload the page. If it happens again, the server log has the detail."];
  main.replaceChildren(
    h(
      "div",
      { class: "panel error", role: "alert" },
      h("h2", null, "This page could not be loaded"),
      h("p", null, known ? err.message : "The page met a problem while showing the data."),
      h("p", null, advice),
      known && err.code ? h("p", { class: "small muted" }, "Code: ", h("code", null, err.code)) : null,
    ),
  );
}

// ---------------------------------------------------------------- queue

const isOpen = (item) => !(item.disposition && item.disposition.final);

async function pageQueue(main, batch) {
  const queue = await api("/queue");
  const items = queue.items;
  const open = items.filter(isOpen).length;
  let show = "all";
  const list = h("div", null);
  const count = h("p", { class: "small muted", role: "status" });

  const draw = () => {
    const rows = items.filter((it) => show === "all" || isOpen(it));
    count.textContent =
      show === "all" ? `Showing ${int(rows.length)} of ${int(items.length)} referred cases.` : `Showing ${int(rows.length)} open of ${int(items.length)} referred cases.`;
    if (items.length === 0) {
      list.replaceChildren(h("div", { class: "panel" }, h("p", null, "No call in this batch has been referred to a reviewer.")));
    } else if (rows.length === 0) {
      list.replaceChildren(h("div", { class: "panel" }, h("p", null, "No case is awaiting a final decision. Choose All to see the decided cases.")));
    } else {
      list.replaceChildren(
        table({
          stack: true,
          caption: "Open cases first, then decided cases, in the order the server sends.",
          cols: [
            { label: "Severity" },
            { label: "Case", wide: true, cls: "case-cell" },
            { label: "Loan and borrower" },
            { label: "Branch and channel" },
            { label: "Day since sale, at the call", num: true },
            { label: "Left in the 30-day window", num: true },
            { label: "Paragraphs" },
            { label: "Decision" },
          ],
          rows: rows.map((it) => ({
            cls: isOpen(it) ? null : "decided",
            cells: [
              sevLabel(it.severity),
              [
                h("a", { class: "case-link", href: caseHref(it.case_id), lang: "en" }, it.headline),
                h(
                  "span",
                  { class: "sub" },
                  h("span", { class: "id" }, it.case_id),
                  ` \u00B7 ${int(it.refer_lines)} ${it.refer_lines === 1 ? "line" : "lines"} for review \u00B7 ${languageName(it.language)} `,
                  it.simulated ? simTag() : null,
                ),
              ],
              [h("span", { class: "id nowrap" }, it.loan_id), h("span", { class: "sub" }, it.borrower)],
              [h("span", { class: "nowrap" }, it.branch), h("span", { class: "sub" }, `${words(it.channel)} \u00B7 sold ${fmtDate(it.sold_on)}`)],
              `Day ${int(it.day_since_sale)}`,
              `${days(it.days_left_in_window)} left`,
              it.may_engage.length ? h("span", { class: "engage" }, `may engage ${it.may_engage.map((m) => m.replace(/^may engage /, "")).join(", ")}`) : h("span", { class: "muted" }, DASH),
              it.disposition
                ? [it.disposition.decision_label, h("span", { class: "sub" }, `${it.disposition.reviewer}, ${fmtDate(it.disposition.recorded_at)}`)]
                : h("strong", null, "Awaiting review"),
            ],
          })),
        }),
      );
    }
  };

  const radio = (value, label) =>
    h(
      "label",
      null,
      h("input", {
        type: "radio",
        name: "show",
        value,
        checked: value === show,
        onchange: () => {
          show = value;
          draw();
        },
      }),
      label,
    );

  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        null,
        h("h1", null, "Reviewer queue"),
        h("p", { class: "muted lead" }, "Calls referred for a person to look at. A referral is a request to review a call against the record, and the decision on each case is the reviewer's."),
      ),
      h("fieldset", { class: "filter" }, h("legend", { class: "vh" }, "Cases to show"), radio("all", `All (${int(items.length)})`), radio("open", `Open (${int(open)})`)),
    ),
    h(
      "ul",
      { class: "stats" },
      h("li", null, h("b", null, `${int(batch.completed)} of ${int(batch.sampled)}`), h("span", null, "sampled loans with a completed call")),
      h("li", null, h("b", null, `${int(batch.referred)} of ${int(batch.completed)}`), h("span", null, "completed calls referred")),
      h("li", null, h("b", null, `${int(batch.awaiting_review)} of ${int(batch.referred)}`), h("span", null, "referrals with no final decision")),
    ),
    count,
    list,
  );
  draw();
}

// ---------------------------------------------------------------- one case

function productFacts(p) {
  const features = [...p.features].sort().map(words);
  return facts([
    ["Kind", words(p.kind)],
    ["Provider", p.provider],
    ["Premium", inr(p.premium_inr)],
    ["Cover", inr(p.cover_inr)],
    ["Term", `${int(p.term_months)} months`],
    ["Paid from the loan", yesNo(p.paid_from_loan)],
    ["Required for the loan", yesNo(p.required_for_loan)],
    ["Recorded as a risk mitigant", yesNo(p.risk_mitigant)],
    ["Choice of provider offered", yesNo(p.provider_choice_offered)],
    ["Cancellation window", p.cancel_window_days === null ? "None on record" : days(p.cancel_window_days)],
    ["Consent", p.consent ? `${words(p.consent.method)}, ${fmtDate(p.consent.at)}` : "None on record"],
    ["Features on record", features.length ? features.join(", ") : "None on record"],
  ]);
}

function recordSide(loan) {
  return h(
    "section",
    { class: "record-side", "aria-labelledby": "record-h" },
    h("h2", { id: "record-h" }, "The lender's record"),
    h(
      "div",
      { class: "panel" },
      h("h3", null, "Loan"),
      facts([
        ["Loan", h("span", { class: "id" }, loan.loan_id)],
        ["Borrower", loan.borrower],
        ["Lender type", LENDER_TYPES[loan.lender_type] || words(loan.lender_type)],
        ["Loan kind", words(loan.loan_kind)],
        ["Sanctioned", inr(loan.sanctioned_inr)],
        ["Disbursed", inr(loan.disbursed_inr)],
        ["Sold on", fmtDate(loan.sold_on)],
        ["Branch", loan.branch],
        ["Channel", words(loan.channel)],
      ]),
    ),
    loan.products.map((p) => h("div", { class: "panel" }, h("h3", null, "Product ", h("span", { class: "id" }, p.id)), productFacts(p))),
    loan.products.length === 0 ? h("div", { class: "panel" }, h("p", { class: "muted" }, "No product on the record for this loan.")) : null,
  );
}

function quoteFigure(q, ctx) {
  return h(
    "figure",
    { class: "quote" },
    h("blockquote", { lang: ctx.lang }, q.quote),
    h(
      "figcaption",
      null,
      h("a", { href: `#turn-${q.turn_id}`, onclick: () => ctx.openTranscript() }, `Turn ${q.turn_id}`),
      q.start_s !== null && ctx.recording
        ? h(
            "a",
            { href: `${ctx.recording}#t=${q.start_s}`, onclick: (ev) => ctx.playFrom(ev, q.start_s) },
            `Play the recording from ${mmss(q.start_s)}`,
          )
        : q.start_s !== null
          ? h("span", null, `At ${mmss(q.start_s)} in the call`)
          : null,
    ),
  );
}

function lineCard(line, ctx) {
  return h(
    "article",
    { class: "line" },
    h(
      "div",
      { class: "line-head" },
      h("h3", null, line.title),
      line.tier !== "refer" ? h("span", { class: `tier tier-${line.tier}` }, line.tier_label) : null,
    ),
    h(
      "p",
      { class: "small muted line-rules" },
      [line.product_id ? `Product ${line.product_id}` : "Whole call", line.rule_labels.join(", ")].join(" \u00B7 "),
      line.may_engage.length ? [" \u00B7 ", h("span", { class: "engage" }, line.may_engage.join("; "))] : null,
    ),
    h(
      "div",
      { class: "sides" },
      h("div", { class: "side record" }, h("span", { class: "side-label" }, "Record"), h("p", null, line.record_value)),
      h(
        "div",
        { class: "side customer" },
        h("span", { class: "side-label" }, "Customer"),
        line.quote ? quoteFigure(line.quote, ctx) : h("p", { class: "small muted" }, "No quote is attached to this line."),
      ),
    ),
  );
}

function dispositionBlock(d) {
  return [
    h("p", { class: "what" }, d.decision_label),
    h("p", { class: "small muted" }, `Recorded by ${d.reviewer} on ${fmtDateTime(d.recorded_at)}. ${d.final ? "Final: the case is closed." : "Not final: the case stays open."}`),
    h("p", { class: "note-text" }, d.note),
  ];
}

function decisionSection(first) {
  const now = h("div", { class: "panel decision-now" });
  const history = h("div", null);
  const msg = h("p", { class: "form-msg", role: "status", "aria-live": "polite" });
  const note = h("textarea", { id: "d-note", name: "note", required: true, maxlength: "2000", rows: "4" });
  const who = h("input", { id: "d-who", name: "reviewer", type: "text", required: true, maxlength: "80", autocomplete: "name" });
  who.value = remember("samajh.review.reviewer");
  const submit = h("button", { class: "btn primary", type: "submit" }, "Record decision");
  const caseId = first.case_id;

  const show = (c) => {
    now.className = `panel decision-now${c.disposition && c.disposition.final ? " final" : ""}`;
    now.replaceChildren(
      h("h3", null, "Current decision"),
      ...(c.disposition ? dispositionBlock(c.disposition) : [h("p", { class: "what" }, "Awaiting review"), h("p", { class: "small muted" }, "No decision has been recorded on this case.")]),
    );
    history.replaceChildren(
      h("h3", null, `Decisions recorded on this case (${int(c.history.length)})`),
      c.history.length
        ? h("ol", { class: "history panel" }, c.history.map((d) => h("li", null, dispositionBlock(d))))
        : h("p", { class: "small muted" }, "None yet."),
    );
  };

  const form = h(
    "form",
    {
      class: "decide panel",
      novalidate: true,
      onsubmit: async (ev) => {
        ev.preventDefault();
        const picked = form.querySelector('input[name="decision"]:checked');
        const problem = !picked
          ? "Choose one of the decisions."
          : !note.value.trim()
            ? "Write a note that says what you looked at and why you decided this."
            : !who.value.trim()
              ? "Enter your name."
              : "";
        msg.className = problem ? "form-msg bad" : "form-msg";
        msg.textContent = problem || "Saving\u2026";
        if (problem) {
          (!picked ? form.querySelector('input[name="decision"]') : !note.value.trim() ? note : who).focus();
          return;
        }
        submit.disabled = true;
        try {
          const saved = await api(`/cases/${encodeURIComponent(caseId)}/disposition`, {
            method: "POST",
            headers: { Accept: "application/json", "Content-Type": "application/json" },
            body: JSON.stringify({ decision: picked.value, note: note.value.trim(), reviewer: who.value.trim() }),
          });
          remember("samajh.review.reviewer", who.value.trim());
          show(saved);
          note.value = "";
          picked.checked = false;
          msg.className = "form-msg ok";
          msg.textContent = saved.disposition ? `Saved: ${saved.disposition.decision_label}.` : "Saved.";
        } catch (err) {
          msg.className = "form-msg bad";
          msg.textContent = err instanceof ApiError ? `Not saved. ${err.message}` : "Not saved. The page met a problem.";
        } finally {
          submit.disabled = false;
        }
      },
    },
    h("h3", null, "Record a decision"),
    h(
      "fieldset",
      null,
      h("legend", null, "Decision"),
      first.decisions.map((d) => h("label", { class: "choice" }, h("input", { type: "radio", name: "decision", value: d.key, required: true }), h("span", null, d.label))),
    ),
    h("div", null, h("label", { class: "field", for: "d-note" }, "Note (required): what you looked at and why"), note),
    h("div", null, h("label", { class: "field", for: "d-who" }, "Your name"), who),
    h("div", { class: "form-row" }, submit, msg),
  );

  show(first);
  return h("section", { "aria-labelledby": "decide-h" }, h("h2", { id: "decide-h" }, "Reviewer's decision"), now, form, h("div", { style: "margin-top:16px" }, history));
}

async function pageCase(main) {
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) throw new ApiError(404, "no_case_id", "This address names no case.");
  const c = await api(`/cases/${encodeURIComponent(id)}`);
  document.title = `Case ${c.case_id} \u00B7 Samajh review`;

  const call = c.call;
  const audio = call.recording_url ? h("audio", { controls: true, preload: "none", src: call.recording_url }) : null;
  const transcript = h("details", { class: "transcript", id: "transcript" });
  const ctx = {
    lang: LANG_ATTR[call.language] || null,
    recording: call.recording_url,
    openTranscript: () => {
      transcript.open = true;
    },
    playFrom: (ev, start) => {
      ev.preventDefault();
      // The #t fragment asks the browser to start there; the listener covers a browser that ignores it.
      audio.addEventListener(
        "loadedmetadata",
        () => {
          if (Math.abs(audio.currentTime - start) > 0.5) audio.currentTime = start;
        },
        { once: true },
      );
      audio.src = `${call.recording_url}#t=${start}`;
      audio.load();
      audio.play().catch(() => {
        // the browser refused to start playback: the controls are still there
      });
      audio.scrollIntoView({ block: "nearest" });
    },
  };

  const cited = c.transcript.filter((t) => t.cited).length;
  transcript.append(
    h("summary", null, `Full transcript (${int(c.transcript.length)} turns, ${int(cited)} cited above)`),
    h(
      "ol",
      { class: "turns" },
      c.transcript.map((t) =>
        h(
          "li",
          { id: `turn-${t.turn_id}`, class: t.cited ? "cited" : null },
          h(
            "div",
            { class: "meta" },
            h("b", null, `Turn ${t.turn_id}`),
            h("span", null, words(t.speaker)),
            t.start_s !== null ? h("span", { class: "num" }, mmss(t.start_s)) : null,
            t.cited ? h("b", null, "Cited above") : null,
          ),
          h("p", { lang: ctx.lang }, t.text),
        ),
      ),
    ),
  );
  if (window.location.hash.startsWith("#turn-")) transcript.open = true;

  const source = call.source.kind === "phone_session" ? ["Phone session ", h("span", { class: "id" }, call.source.session_id)] : ["Scripted, no phone involved (", h("code", null, call.source.script), ")"];

  main.replaceChildren(
    h("p", { class: "small" }, h("a", { href: "index.html" }, "\u2190 Reviewer queue")),
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        { class: "case-title" },
        h("h1", null, "Case ", h("span", { class: "id" }, c.case_id)),
        sevLabel(c.severity),
        h("span", { class: `tier tier-${c.tier}` }, c.tier_label),
        call.simulated ? simTag() : null,
        h("p", { class: "muted" }, `${c.loan.borrower} \u00B7 loan `, h("span", { class: "id" }, c.loan.loan_id), ` \u00B7 ${c.loan.branch}, ${words(c.loan.channel).toLowerCase()} channel`),
      ),
    ),
    h("p", { class: "notice" }, "This call was referred so that a person can compare what the customer said with the record. Nothing on this page is a finding about the sale. The decision is the reviewer's."),
    h(
      "div",
      { class: "case-grid", style: "margin-top:20px" },
      recordSide(c.loan),
      h(
        "div",
        null,
        h(
          "section",
          { "aria-labelledby": "words-h" },
          h("h2", { id: "words-h" }, "The customer's words, against the record"),
          c.refer_lines.map((line) => lineCard(line, ctx)),
        ),
        h(
          "section",
          { "aria-labelledby": "call-h" },
          h("h2", { id: "call-h" }, "The call"),
          h(
            "div",
            { class: "panel" },
            facts([
              ["Call", h("span", { class: "id" }, call.call_id)],
              ["When", fmtDateTime(call.at)],
              ["Language", languageName(call.language)],
              ["Attempt", int(call.attempt_number)],
              ["Day since sale", int(call.day_since_sale)],
              ["Source", source],
              ["Analysis", call.analysis],
              ["Recording", audio ? "Below. The play links beside each quote start it at that turn." : "No recording for this call."],
            ]),
            audio,
          ),
        ),
        c.other_lines.length
          ? h(
              "section",
              { "aria-labelledby": "other-h" },
              h("h2", { id: "other-h" }, "Other issues on the same call"),
              h("p", { class: "small muted", style: "margin-bottom:10px" }, "Questions the call left undecided and understanding gaps. They are counted in the half-yearly report and are not the reason this case was referred."),
              c.other_lines.map((line) => lineCard(line, ctx)),
            )
          : null,
        c.undecided.length
          ? h(
              "section",
              { "aria-labelledby": "undecided-h" },
              h("h2", { id: "undecided-h" }, "Checks that could not decide"),
              h("div", { class: "panel" }, h("ul", { class: "plain-list" }, c.undecided.map((u) => h("li", null, u.label)))),
            )
          : null,
        h("section", { "aria-labelledby": "transcript-h" }, h("h2", { id: "transcript-h" }, "Transcript"), transcript),
        decisionSection(c),
      ),
    ),
  );
}

// ---------------------------------------------------------------- draws (attempt log and report)

function drawsTable(draws, caption) {
  return table({
    caption,
    cols: [
      { label: "Draw", head: true },
      { label: "As of" },
      { label: "Window, days since sale" },
      { label: "Size asked", num: true },
      { label: "Eligible", num: true },
      { label: "Already drawn", num: true },
      { label: "Drawn", num: true },
      { label: "Seed", num: true },
      { label: "Recomputed from the book and matched" },
    ],
    rows: draws.map((d) => ({
      cells: [
        h("span", { class: "id nowrap" }, d.draw_id),
        h("span", { class: "nowrap" }, fmtDate(d.as_of)),
        `${d.min_day} to ${d.max_day}`,
        int(d.size),
        int(d.eligible),
        int(d.already_drawn),
        int(d.drawn),
        String(d.seed),
        yesNo(d.verified),
      ],
    })),
  });
}

async function pageAttempts(main) {
  const log = await api("/attempts");
  const attempts = log.loans.reduce((sum, l) => sum + l.attempts.length, 0);
  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h("div", null, h("h1", null, "Sample and attempt log"), h("p", { class: "muted lead" }, "Which loans were drawn for a feedback call, how each draw can be repeated, and every attempt made to reach each customer.")),
    ),
    h(
      "section",
      { "aria-labelledby": "draws-h" },
      h("h2", { id: "draws-h" }, "Draws"),
      log.draws.length ? drawsTable(log.draws, "Each draw is a seeded random selection from the loans inside the window on its as-of date.") : h("div", { class: "panel" }, h("p", null, "No draw has been made.")),
      h("p", { class: "small", style: "margin-top:8px" }, h("a", { href: `${API}/draws` }, "Raw selection audit (JSON)"), ": every eligible loan id, the seed and the loans drawn."),
    ),
    h(
      "section",
      { "aria-labelledby": "loans-h" },
      h("h2", { id: "loans-h" }, "Sampled loans"),
      h("p", { class: "small muted", style: "margin-bottom:10px" }, `${int(log.loans.length)} sampled loans, ${int(attempts)} attempts, in draw order. Each attempt shows its number, how it ended and the day since the sale.`),
      log.loans.length
        ? table({
            stack: true,
            long: true,
            cols: [
              { label: "Loan and draw", head: true },
              { label: "Sold on" },
              { label: "Language" },
              { label: "Branch and channel" },
              { label: "Attempts" },
              { label: "Final status" },
              { label: "Call outcome" },
              { label: "Case" },
            ],
            rows: log.loans.map((l) => ({
              cells: [
                [h("span", { class: "id nowrap" }, l.loan_id), h("span", { class: "sub id nowrap" }, `Draw ${l.draw_id}`)],
                [h("span", { class: "nowrap" }, fmtDate(l.sold_on)), h("span", { class: "sub nowrap" }, `day ${int(l.day_since_sale_at_draw)} at the draw`)],
                languageName(l.language),
                [h("span", { class: "nowrap" }, l.branch), h("span", { class: "sub" }, words(l.channel))],
                l.attempts.length
                  ? h(
                      "ol",
                      { class: "chips" },
                      l.attempts.map((a) =>
                        h(
                          "li",
                          { class: `chip${a.outcome === "completed" ? " done" : ""}`, title: fmtDateTime(a.at) },
                          h("b", null, a.number),
                          h("span", null, a.outcome_label),
                          h("span", { class: "muted" }, `day ${a.day_since_sale}${a.simulated ? "" : " \u00B7 phone session"}`),
                        ),
                      ),
                    )
                  : h("span", { class: "muted" }, "None"),
                l.status_label,
                l.tier_label ? h("span", { class: `tier tier-${l.tier}` }, l.tier_label) : h("span", { class: "muted" }, DASH),
                l.case_id ? h("a", { href: caseHref(l.case_id), class: "nowrap" }, "Open case") : h("span", { class: "muted" }, DASH),
              ],
            })),
          })
        : h("div", { class: "panel" }, h("p", null, "No loan has been sampled.")),
    ),
  );
}

// ---------------------------------------------------------------- the half-yearly report

const cssString = (s) => `"${String(s).replace(/[\\"]/g, "\\$&").replace(/[\r\n]+/g, " ")}"`;

function proportionTable({ caption, first, rows, bars = false }) {
  return table({
    caption,
    cols: [{ label: first, head: true }, { label: "Count", num: true }, { label: "Share", num: true }, { label: "95% interval", num: true }, ...(bars ? [{ label: "", cls: "bar-cell" }] : [])],
    rows: rows.map((r) => ({
      cells: [
        r.label,
        pCount(r.value),
        pShare(r.value),
        pInterval(r.value),
        ...(bars ? [h("span", { class: "bar", "aria-hidden": "true" }, h("span", { style: `width:${r.value.share === null ? 0 : Math.round(r.value.share * 100)}%` }))] : []),
      ],
    })),
  });
}

function section(id, title, ...kids) {
  return h("section", { "aria-labelledby": id }, h("h2", { id }, title), kids);
}

async function pageReport(main) {
  const r = await api("/report");
  const lender = r.batch.meta.book.lender_name;
  const para = `para ${r.paragraph}`;
  const notice = r.batch.simulated_notice;
  document.title = `Half-yearly report \u00B7 ${lender} \u00B7 Samajh review`;

  // The running title on every printed page.
  const running = `${notice ? "SIMULATED. " : ""}${lender}: feedback under ${para}, ${r.period_label}`;
  document.head.append(
    h(
      "style",
      null,
      `@page { @top-left { content: ${cssString(running)}; font: 8pt system-ui, sans-serif; color: #000; } @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt system-ui, sans-serif; color: #000; } }`,
    ),
  );

  const f = r.funnel;
  const t = r.timing;
  const understanding = r.findings.filter((x) => x.understanding);
  const others = r.findings.filter((x) => !x.understanding);
  const findingRow = (x) => ({
    cells: [
      [x.statement, h("span", { class: "sub" }, x.rule_label)],
      pCount(x.flagged),
      pShare(x.flagged),
      pInterval(x.flagged),
      `${int(x.undecided)} of ${int(x.flagged.n)}`,
      `${int(x.referred)} of ${int(x.flagged.count)}`,
      x.may_engage ? h("span", { class: "engage" }, x.may_engage) : h("span", { class: "muted" }, DASH),
    ],
  });
  const establishedRow = r.referrals.find((row) => row.key === "established");
  const e = r.established_of_decided;

  main.className = "report";
  main.replaceChildren(
    h(
      "div",
      { class: "page-head" },
      h(
        "div",
        null,
        h("p", { class: "eyebrow" }, `Feedback under ${para}`),
        h("h1", null, `Half-yearly report: ${lender}`),
        h("p", { class: "period" }, r.period_label),
        h("p", { class: "meta" }, r.coverage),
        h("p", { class: "meta" }, `Generated ${fmtDateTime(r.generated_at)} \u00B7 batch `, h("span", { class: "id" }, r.batch.meta.batch_id)),
      ),
      h("button", { class: "btn no-print", type: "button", onclick: () => window.print() }, "Print or save as PDF"),
    ),
    h(
      "section",
      { class: "limits", "aria-labelledby": "limits-h" },
      h("h2", { id: "limits-h" }, "What this report is and is not"),
      notice ? h("p", { class: "sim" }, notice) : null,
      h("ul", null, r.limits.map((s) => h("li", null, s))),
    ),
    section(
      "sampling-h",
      "Sampling",
      h("p", null, `${int(f.sampled)} loans were sampled in ${int(r.draws.length)} ${r.draws.length === 1 ? "draw" : "draws"}. Each draw is a seeded random selection that can be recomputed from the loan book.`),
      r.draws.length ? drawsTable(r.draws, "Draws") : null,
    ),
    section(
      "reach-h",
      "Reach",
      h("p", null, `${int(f.attempts)} attempts were made on ${int(f.sampled)} sampled loans, retries included. Every share below is of the ${int(f.sampled)} sampled loans.`),
      proportionTable({ caption: "How far the sampled loans got. Each stage is within the one before.", first: "Stage", rows: f.stages, bars: true }),
      proportionTable({ caption: "Where the loans without a completed call ended", first: "Final status", rows: f.exits, bars: true }),
    ),
    section(
      "timing-h",
      "Timing",
      h("p", null, "Days are counted from the sale to the attempt, not to the draw."),
      table({
        caption: "Timing against the 30-day window",
        cols: [{ label: "Measure", head: true }, { label: "Value", num: true }, { label: "Share", num: true }, { label: "95% interval", num: true }],
        rows: [
          {
            cells: [
              `Days from sale to first attempt, over the ${int(f.stages.find((x) => x.key === "attempted").value.count)} loans attempted`,
              t.first_attempt_days ? `least ${t.first_attempt_days[0]}, median ${t.first_attempt_days[1]}, most ${t.first_attempt_days[2]}` : "No attempt made",
              DASH,
              DASH,
            ],
          },
          { cells: ["Completed calls that were completed within the window", pCount(t.completed_within_window), pShare(t.completed_within_window), pInterval(t.completed_within_window)] },
          { cells: ["Attempts made after the window had closed", `${int(t.attempts_after_window)} of ${int(f.attempts)}`, DASH, DASH] },
        ],
      }),
    ),
    section("tiers-h", "Outcome of the analysed calls", proportionTable({ caption: "One outcome per analysed call", first: "Outcome", rows: r.tiers })),
    section(
      "findings-h",
      "Findings by rule",
      h("p", null, "Each rule runs on every analysed call. Undecided calls had a gap under the rule and no flag. Referred is the number of the flagged calls that went to a reviewer for that rule."),
      table({
        caption: "A paragraph is one that a line may engage. It is not a finding about any sale.",
        cols: [
          { label: "Customers who\u2026", head: true },
          { label: "Count", num: true },
          { label: "Share", num: true },
          { label: "95% interval", num: true },
          { label: "Undecided", num: true },
          { label: "Referred, of those counted", num: true },
          { label: "Paragraph" },
        ],
        rows: [
          ...(understanding.length ? [{ group: `Understanding of the product (the feedback paragraph, ${para})` }, ...understanding.map(findingRow)] : []),
          ...(others.length ? [{ group: "Other checks made on the same call" }, ...others.map(findingRow)] : []),
        ],
      }),
    ),
    section(
      "referrals-h",
      "Referrals and reviewer decisions",
      proportionTable({ caption: "Referred calls by the reviewer's latest decision", first: "Decision", rows: r.referrals }),
      h(
        "p",
        null,
        `Of the referrals with a final decision, ${pCount(e)}: ${establishedRow ? establishedRow.label : words("established")}`,
        e.n === 0 ? "." : ` (${pShare(e)}; 95% interval ${pInterval(e)}).`,
      ),
    ),
    section(
      "breakdowns-h",
      "Findings by loan kind, branch and channel",
      h("p", null, "Each count is of that row's completed calls. Small rows give wide intervals."),
      r.breakdowns.map((b) =>
        table({
          caption: `By ${b.label.toLowerCase()}`,
          cols: [
            { label: b.label, head: true },
            { label: "Sampled", num: true },
            { label: "Completed", num: true },
            { label: "Referred", num: true },
            { label: "95% interval", num: true },
            { label: "Understanding gap", num: true },
            { label: "95% interval", num: true },
          ],
          rows: b.rows.map((row) => ({
            cells: [row.label, int(row.sampled), `${int(row.completed)} of ${int(row.sampled)}`, pBoth(row.referred), pInterval(row.referred), pBoth(row.understanding_gap), pInterval(row.understanding_gap)],
          })),
        }),
      ),
    ),
    section(
      "policy-h",
      "For policy review",
      h("p", null, `Under ${para} this report is used to review policies and product features. The understanding gaps are listed in the order the report ranks them.`),
      r.policy_review.length
        ? h(
            "ol",
            { class: "policy" },
            r.policy_review.map((p) =>
              h(
                "li",
                null,
                h("p", { class: "sentence" }, p.sentence),
                h("p", { class: "detail" }, `${pCount(p.value)}, ${pShare(p.value)}; 95% interval ${pInterval(p.value)}`, p.highest ? `; ${p.highest}` : "", "."),
              ),
            ),
          )
        : h("p", { class: "muted" }, "No understanding gap was counted in this batch."),
    ),
  );
}

// ---------------------------------------------------------------- start

const PAGES = { queue: pageQueue, case: pageCase, attempts: pageAttempts, report: pageReport };

async function start() {
  const page = document.body.dataset.page;
  const main = document.getElementById("main");
  let batch = null;
  try {
    batch = await api("/batch");
  } catch (err) {
    renderHeader(null, page);
    showError(main, err);
    return;
  }
  renderHeader(batch, page);
  try {
    await PAGES[page](main, batch);
  } catch (err) {
    if (!(err instanceof ApiError)) console.error(err);
    showError(main, err);
  }
}

start();
