# Participant Guide — Phishing Email Triage

You are an L1/L2 SOC analyst. A secure email gateway raised an alert on a
suspicious message, and it's your job to triage it: work the evidence, reach a
defensible verdict, and recommend a proportionate response.

This guide explains **how to work the case and use the tools**. It does not give
you answers — every task is answerable from the evidence in `/data`.

> ⚠️ Everything here is a **synthetic training artifact**. Domains use
> `.test`/`.invalid`, IPs are RFC 5737 documentation addresses, and URLs are
> **defanged** (`hxxps://`, `[.]`). Never re-fang, visit, resolve, or "open"
> anything. There are no live payloads.

## Scoring at a glance

- **3 sections · 18 tasks · 54 points** (3 points per task).
- Scoring is deterministic and exact-match after normalization (leading/trailing
  whitespace trimmed, inner whitespace collapsed, case-folded unless a task is
  case-sensitive). Type your answer in the exact form the evidence shows.
- Using a hint reduces the points available on that task (down to a floor), so
  try the evidence first.
- Many tasks declare `dependencies` — resolve earlier tasks first; later tasks
  build on them.

## Where the evidence lives

Under `/data/case/`:

| File | What it holds |
|---|---|
| `case_manifest.json` | Case id, title, difficulty, timezone. |
| `alert.json` | The gateway alert: id, rule, severity, recipient count. |
| `email_headers.json` | From / Return-Path / Reply-To / To, subject, date, SPF-DKIM-DMARC, received chain. |
| `email_body.txt` | The message body, including the (defanged) URL. |
| `email.eml.txt` | The raw-style assembled message, for cross-reference. |
| `attachment_manifest.json` | Attachment metadata only (declared vs observed type, size, SHA-256). No payload. |
| `gateway_events.jsonl` | Per-recipient received / delivered events. |
| `mailbox_events.jsonl` | Message open events. |
| `proxy_events.jsonl` | Simulated URL clicks, block status, credential-submission indicator. |
| `analyst_notes.txt` | Working notes to orient you. |

Under `/data/reference/`:

- `trusted_domains.json` — the organization and trusted-partner domains. Anything
  outside this list is untrusted; watch for lookalikes of entries on it.
- `field_guide.md` — a concise primer on headers, SPF/DKIM/DMARC alignment,
  lookalike domains, URLs, attachments, and exposure. **Read this first.**

## Tools in the workspace

Three read-only CLI tools are on your `PATH` (they only read `/data`):

```bash
email_summary.py     # one-screen overview: alert, sender, auth, URL, attachment
parse_headers.py     # identity fields, Reply-To alignment, trusted/lookalike + auth
timeline.py          # every event across all three logs, sorted by timestamp
```

You can also read any evidence file directly (`cat`, `less`, `python3 -c …`).

## Working the three sections

### Section 1 — Email Header & Sender Analysis (S1-T1 … S1-T6)

Start with `email_summary.py` and `parse_headers.py`.

- Identify the gateway **alert id**, then the sender's actual **From address**
  (the address, not the display name — they disagree on purpose).
- Compare the **Reply-To** domain against the **From** domain: where would a
  reply actually go?
- Read the authentication results together, not in isolation. Remember: SPF
  covers the envelope (Return-Path) domain, not the visible From — so an SPF pass
  does not make the message safe. The **DMARC** result is what ties back to the
  visible From via alignment.
- Compare the From domain against `trusted_domains.json`. Look for a **lookalike**
  (a digit swapped for a letter, extra words/hyphens, or a different TLD).
- The final S1 task asks you to select *every* header red flag the evidence
  supports — and only those. A passing SPF is not itself a red flag.

### Section 2 — URL, Attachment & Correlation (S2-T1 … S2-T6)

- Pull the **primary URL** from the body **in its defanged form, exactly as
  written** — do not re-fang `hxxps` or `[.]`. (This task is case-sensitive.)
- Decide which URL red flags apply: is the host a trusted domain? What is the
  path luring the user to do? (TLS/HTTPS alone is not a safety signal.)
- Inspect the attachment metadata: does the **declared** content type match the
  **observed** one? Record the **SHA-256** exactly (64 hex characters).
- Correlate the gateway log: to **how many recipients** was the message
  *delivered* (count distinct `message_delivered` recipients for this message)?
- Determine the **furthest user exposure** reached across all recipients by
  correlating gateway → mailbox → proxy: delivered, opened, clicked — and if
  clicked, was it blocked or did credentials get submitted?

### Section 3 — Incident Assessment & Response (S3-T1 … S3-T6)

- Build the **timeline**: order every `event_id` across all three logs strictly
  by ISO 8601 timestamp (`timeline.py` does the sort for you — verify it).
- Assess the **credential-harvesting outcome** from the proxy event's action and
  its credential-submission indicator.
- Choose a **proportionate severity** and an **incident verdict**, weighing the
  combined header + URL + attachment + exposure evidence against the fact of
  whether the click was blocked and whether credentials were submitted. Don't
  over- or under-call it.
- Recommend **proportionate containment / escalation actions** — match them to a
  blocked click with no credential submission; avoid org-wide disruptive actions
  that the evidence doesn't justify.
- Finally, submit the **structured triage report** (`S3-T6`). Required fields:
  `case_id`, `verdict`, `severity`, `confidence`, `user_exposure`,
  `key_evidence` (list), `recommended_actions` (list), `rationale`. Reuse your
  verdict / severity / exposure answers, and name the concrete indicators you
  relied on in `key_evidence`. This report is graded by rubric with partial
  per-field credit, so fill in every field you can support.

## Method, in one line

Read the field guide → run the tools → cross-check every claim against the
evidence files → keep your verdict, severity, and response **proportionate to
what the evidence actually shows**.
