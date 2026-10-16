"""Shared test helpers: locate repo paths and load the validator module."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CASE = os.path.join(DATA, "case")
REF = os.path.join(DATA, "reference")
VALIDATOR = os.path.join(ROOT, "validator")


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_validator_module():
    """Import validator/app.py with env pointed at the repo files."""
    os.environ["TASK_DEFS_PATH"] = os.path.join(VALIDATOR, "task_definitions.public.json")
    os.environ["ANSWER_KEY_PATH"] = "/nonexistent-secret"
    os.environ["ANSWER_KEY_FALLBACK"] = os.path.join(VALIDATOR, "answer_key.private.json")
    spec = importlib.util.spec_from_file_location("validator_app", os.path.join(VALIDATOR, "app.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_module_tests(namespace):
    """Fallback runner so a test file works without pytest installed."""
    failures = 0
    for name, fn in sorted(namespace.items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    print("\nall tests passed")
