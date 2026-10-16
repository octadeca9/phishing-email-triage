# Analyst Field Guide — Phishing Email Triage

A quick reference for interpreting the evidence in this lab. All data is synthetic.

## Email identity fields

| Field | Where | What it tells you |
|---|---|---|
| `From` | `email_headers.json#/from_address` | The address the sender *claims*. Easily spoofed. |
| `Return-Path` | `email_headers.json#/return_path` | Bounce address (envelope sender / `MAIL FROM`). |
| `Reply-To` | `email_headers.json#/reply_to` | Where replies actually go. A `Reply-To` on a different domain than `From` is a classic redirection red flag. |
| Display name | `email_headers.json#/from_display_name` | Free text. A trusted-looking name (e.g. "Finance Operations") proves nothing. |

## SPF / DKIM / DMARC

- **SPF** checks whether the sending IP is authorized for the envelope (`Return-Path`) domain. `pass` only covers that envelope domain — **not** the visible `From`.
- **DKIM** verifies a cryptographic signature tied to a domain. `none` means the message was not signed.
- **DMARC** ties SPF/DKIM results back to the visible `From` domain via *alignment*. A DMARC `fail` means neither SPF nor DKIM aligned with the `From` domain.
- Key lesson: **SPF pass + DKIM none + DMARC fail** is consistent with a spoofed/impersonating `From`. Evaluate the results together, never one in isolation.

## Lookalike domains

Compare the sender domain against `reference/trusted_domains.json`. Watch for:
- Digit-for-letter swaps (`0` for `o`, `1` for `l`).
- Extra words or hyphens around a trusted brand.
- A different TLD than the legitimate domain.

## URLs

URLs in this lab are **defanged** (`hxxps://`, `[.]`). Never re-fang or visit them. Assess them statically: is the host a trusted domain? Does the path look like a generic credential/document lure?

## Attachments

Judged from metadata only — no payload exists. Compare the declared `content_type`/extension against the observed container type. A `.pdf` that is actually a `application/zip` is a mismatch worth flagging.

## Events and exposure

Three synthetic logs tell the delivery story:
- `gateway_events.jsonl` — received / delivered per recipient.
- `mailbox_events.jsonl` — opens.
- `proxy_events.jsonl` — simulated clicks and whether they were blocked, plus any credential-submission indicator.

Order events by `timestamp` to build the timeline, then derive **user exposure**: was the message delivered, opened, clicked, and was the click blocked or did credentials get submitted?
