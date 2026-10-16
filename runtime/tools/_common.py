"""Shared read-only helpers for the participant CLI tools.

These tools only read the synthetic evidence under DATA_DIR. They never make
network calls, never execute attachments, and never re-fang URLs.
"""
import json
import os

DATA_DIR = os.environ.get("DATA_DIR", "/data")
CASE_DIR = os.path.join(DATA_DIR, "case")
REF_DIR = os.path.join(DATA_DIR, "reference")


def load_json(name, base=CASE_DIR):
    with open(os.path.join(base, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(name, base=CASE_DIR):
    rows = []
    with open(os.path.join(base, name), "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_text(name, base=CASE_DIR):
    with open(os.path.join(base, name), "r", encoding="utf-8") as fh:
        return fh.read()


def all_events():
    """Return events from every log, tagged with their source log."""
    events = []
    for fname in ("gateway_events.jsonl", "mailbox_events.jsonl", "proxy_events.jsonl"):
        for row in load_jsonl(fname):
            row["_log"] = fname
            events.append(row)
    return events
