#!/usr/bin/env python3
"""Trusted scoring validator for the Phishing Email Triage lab.

Deterministic, server-side scoring. The private answer key is loaded at startup
from a secret path and never leaves this process: responses expose only
correctness and points, never the accepted values.

Stdlib only (http.server) so the participant-facing attack surface and the
dependency footprint stay minimal. Not a production HTTP server — see README.

Conceptual API (not the hack.redlimit.id contract):
    GET  /health
    GET  /v1/challenges/{challenge_id}/tasks
    POST /v1/sessions/{session_id}/tasks/{task_id}/submit   {"answer": ..., "hints_used": N}
    POST /v1/sessions/{session_id}/report                   {"report": {...}}
    POST /v1/sessions/{session_id}/reset
"""
from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Configuration -----------------------------------------------------------

TASK_DEFS_PATH = os.environ.get("TASK_DEFS_PATH", "task_definitions.public.json")
# In Compose the answer key is a secret mounted at /run/secrets/answer_key.
# Fall back to the local development file so tests can run without Docker.
ANSWER_KEY_PATH = os.environ.get("ANSWER_KEY_PATH", "/run/secrets/answer_key")
if not os.path.exists(ANSWER_KEY_PATH):
    ANSWER_KEY_PATH = os.environ.get(
        "ANSWER_KEY_FALLBACK", "answer_key.private.json"
    )

HINT_PENALTY = float(os.environ.get("HINT_PENALTY", "1"))   # points lost per hint
HINT_MIN_POINTS = float(os.environ.get("HINT_MIN_POINTS", "1"))  # floor per task
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(64 * 1024)))
HOST = os.environ.get("BIND_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))


# --- Normalization and scoring ------------------------------------------------

def _norm_scalar(value, case_sensitive=False):
    """Normalize a scalar answer: stringify, trim, collapse inner whitespace."""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s if case_sensitive else s.lower()


def _norm_set(values, case_sensitive=False):
    return {_norm_scalar(v, case_sensitive) for v in values}


class Scorer:
    """Holds task definitions + private answer key and grades submissions."""

    def __init__(self, task_defs: dict, answer_key: dict):
        self.challenge_id = task_defs.get("challenge_id")
        self.tasks = {t["task_id"]: t for t in task_defs.get("tasks", [])}
        self.keys = answer_key.get("keys", {})
        self._validate_alignment()

    def _validate_alignment(self):
        """Fail fast if public tasks and the private key disagree."""
        missing = [tid for tid in self.tasks if tid not in self.keys]
        if missing:
            raise ValueError(f"answer key missing entries for tasks: {missing}")
        for tid, task in self.tasks.items():
            if self.keys[tid].get("input_type") != task.get("input_type"):
                raise ValueError(f"input_type mismatch for {tid}")

    # -- per-type grading; returns (is_correct, earned_points) -----------------
    # earned_points is 0 for an incorrect binary task and the full task points
    # for a correct one; the report type may return partial rubric credit.

    def _grade(self, key: dict, answer) -> tuple[bool, float]:
        itype = key["input_type"]
        pts = float(key.get("points", 0))
        cs = bool(key.get("case_sensitive", False))

        if itype in ("string", "single_choice"):
            ok = _norm_scalar(answer, cs) in _norm_set(key["accepted_values"], cs)
            return ok, (pts if ok else 0.0)

        if itype == "number":
            try:
                got = float(str(answer).strip())
            except (TypeError, ValueError):
                return False, 0.0
            ok = any(got == float(v) for v in key["accepted_values"])
            return ok, (pts if ok else 0.0)

        if itype == "multi_select":
            ok = isinstance(answer, list) and _norm_set(answer) == _norm_set(key["accepted_set"])
            return ok, (pts if ok else 0.0)

        if itype == "ordering":
            ok = (
                isinstance(answer, list)
                and [_norm_scalar(x) for x in answer]
                == [_norm_scalar(x) for x in key["accepted_order"]]
            )
            return ok, (pts if ok else 0.0)

        if itype == "report":
            return self._grade_report(key["rubric"], answer)

        raise ValueError(f"unknown input_type: {itype}")

    def _grade_report(self, rubric: dict, report) -> tuple[bool, float]:
        """Deterministic rubric scoring; partial credit per field."""
        if not isinstance(report, dict):
            return False, 0.0
        awarded = 0.0
        total = 0.0
        for field, spec in rubric.items():
            fpts = float(spec["points"])
            total += fpts
            val = report.get(field)
            if "required_set" in spec:
                if isinstance(val, list) and _norm_set(spec["required_set"]).issubset(_norm_set(val)):
                    awarded += fpts
            else:
                if val is not None and _norm_scalar(val) in _norm_set(spec["accepted"]):
                    awarded += fpts
        awarded = round(awarded, 2)
        return (awarded >= total - 1e-9), awarded

    def score(self, task_id: str, answer, hints_used: int):
        """Grade a submission and apply the hint penalty cap.

        The cap only bites on earned points, so a wrong answer (0 earned)
        stays 0 regardless of hints, while partial report credit is preserved.
        """
        key = self.keys[task_id]
        correct, earned = self._grade(key, answer)
        pts = float(key.get("points", 0))
        cap = max(pts - HINT_PENALTY * max(hints_used, 0), HINT_MIN_POINTS)
        awarded = round(min(earned, cap), 2)
        return correct, awarded, pts


# --- Session state ------------------------------------------------------------

class SessionStore:
    """In-memory per-session scoring state. Production persists via the platform."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict[str, dict] = {}

    def _session(self, sid: str) -> dict:
        return self._sessions.setdefault(sid, {"submissions": {}})

    def record(self, sid, task_id, answer, correct, awarded, hints_used):
        with self._lock:
            self._session(sid)["submissions"][task_id] = {
                "answer": answer,
                "correct": correct,
                "points_awarded": awarded,
                "hints_used": hints_used,
            }

    def get(self, sid, task_id):
        with self._lock:
            return self._sessions.get(sid, {}).get("submissions", {}).get(task_id)

    def total(self, sid):
        with self._lock:
            subs = self._sessions.get(sid, {}).get("submissions", {})
            return round(sum(s["points_awarded"] for s in subs.values()), 2)

    def reset(self, sid):
        with self._lock:
            self._sessions.pop(sid, None)


# --- HTTP layer ---------------------------------------------------------------

def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


SCORER = Scorer(_load_json(TASK_DEFS_PATH), _load_json(ANSWER_KEY_PATH))
STORE = SessionStore()

# Public task view: definitions with every answer-bearing field stripped.
PUBLIC_TASKS = _load_json(TASK_DEFS_PATH)

ROUTE_SUBMIT = re.compile(r"^/v1/sessions/([^/]+)/tasks/([^/]+)/submit$")
ROUTE_REPORT = re.compile(r"^/v1/sessions/([^/]+)/report$")
ROUTE_RESET = re.compile(r"^/v1/sessions/([^/]+)/reset$")
ROUTE_TASKS = re.compile(r"^/v1/challenges/([^/]+)/tasks$")


class Handler(BaseHTTPRequestHandler):
    server_version = "triage-validator/1.0"

    def log_message(self, fmt, *args):  # audit without leaking payloads/answers
        print(f"[validator] {self.command} {self.path} -> {args[-1] if args else ''}")

    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > MAX_BODY_BYTES:
            return None, (413, {"error": "payload too large"})
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}"), None
        except json.JSONDecodeError:
            return None, (400, {"error": "invalid JSON payload"})

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "challenge_id": SCORER.challenge_id})
        m = ROUTE_TASKS.match(self.path)
        if m:
            if m.group(1) != SCORER.challenge_id:
                return self._send(404, {"error": "unknown challenge"})
            return self._send(200, PUBLIC_TASKS)
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        m = ROUTE_SUBMIT.match(self.path)
        if m:
            return self._submit(m.group(1), m.group(2))
        m = ROUTE_REPORT.match(self.path)
        if m:
            return self._report(m.group(1))
        m = ROUTE_RESET.match(self.path)
        if m:
            STORE.reset(m.group(1))
            return self._send(200, {"status": "reset", "session_id": m.group(1)})
        return self._send(404, {"error": "not found"})

    def _submit(self, session_id, task_id):
        if task_id not in SCORER.tasks:
            return self._send(404, {"error": "unknown task"})
        payload, err = self._read_json()
        if err:
            return self._send(*err)
        if "answer" not in payload:
            return self._send(400, {"error": "missing 'answer'"})

        # Idempotency: a repeated submit for an already-graded task returns the
        # stored result rather than re-scoring.
        existing = STORE.get(session_id, task_id)
        if existing is not None:
            return self._send(200, {
                "task_id": task_id, "correct": existing["correct"],
                "points_awarded": existing["points_awarded"],
                "total_score": STORE.total(session_id), "idempotent_replay": True,
            })

        hints_used = int(payload.get("hints_used", 0) or 0)
        try:
            correct, awarded, max_pts = SCORER.score(task_id, payload["answer"], hints_used)
        except (ValueError, TypeError):
            return self._send(400, {"error": "answer failed validation"})

        STORE.record(session_id, task_id, payload["answer"], correct, awarded, hints_used)
        return self._send(200, {
            "task_id": task_id, "correct": correct, "points_awarded": awarded,
            "max_points": max_pts, "hints_used": hints_used,
            "total_score": STORE.total(session_id), "idempotent_replay": False,
        })

    def _report(self, session_id):
        payload, err = self._read_json()
        if err:
            return self._send(*err)
        report = payload.get("report")
        if not isinstance(report, dict):
            return self._send(400, {"error": "missing 'report' object"})
        existing = STORE.get(session_id, "S3-T6")
        if existing is not None:
            return self._send(200, {
                "task_id": "S3-T6", "accepted": existing["correct"],
                "points_awarded": existing["points_awarded"],
                "total_score": STORE.total(session_id), "idempotent_replay": True,
            })
        hints_used = int(payload.get("hints_used", 0) or 0)
        correct, awarded, max_pts = SCORER.score("S3-T6", report, hints_used)
        STORE.record(session_id, "S3-T6", report, correct, awarded, hints_used)
        return self._send(200, {
            "task_id": "S3-T6", "accepted": correct, "points_awarded": awarded,
            "max_points": max_pts, "total_score": STORE.total(session_id),
            "idempotent_replay": False,
        })


def main():
    print(f"[validator] challenge={SCORER.challenge_id} tasks={len(SCORER.tasks)}")
    print(f"[validator] answer key: {ANSWER_KEY_PATH}")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[validator] listening on {HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
