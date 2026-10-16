"""Verify the synthetic truth set is internally consistent and safe."""
import os
import re

from _util import CASE, REF, load_json, load_jsonl, run_module_tests

MESSAGE_ID = "<msg-0042@payr0ll-notice.invalid>"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _all_events():
    ev = []
    for f in ("gateway_events.jsonl", "mailbox_events.jsonl", "proxy_events.jsonl"):
        ev += load_jsonl(os.path.join(CASE, f))
    return ev


def test_message_id_consistent_across_files():
    alert = load_json(os.path.join(CASE, "alert.json"))
    headers = load_json(os.path.join(CASE, "email_headers.json"))
    assert alert["message_id"] == MESSAGE_ID
    assert headers["message_id"] == MESSAGE_ID
    for e in load_jsonl(os.path.join(CASE, "gateway_events.jsonl")):
        assert e["message_id"] == MESSAGE_ID


def test_case_and_alert_ids_match():
    manifest = load_json(os.path.join(CASE, "case_manifest.json"))
    alert = load_json(os.path.join(CASE, "alert.json"))
    assert manifest["case_id"] == alert["alert_id"] == "PHISH-2026-0042"


def test_recipient_count_matches_delivery_events():
    alert = load_json(os.path.join(CASE, "alert.json"))
    gw = load_jsonl(os.path.join(CASE, "gateway_events.jsonl"))
    delivered = {e["recipient"] for e in gw if e["event_type"] == "message_delivered"}
    assert len(delivered) == alert["recipient_count"] == 2


def test_all_timestamps_are_iso_utc():
    for e in _all_events():
        assert ISO.match(e["timestamp"]), e


def test_timeline_is_unambiguous():
    ts = [e["timestamp"] for e in _all_events()]
    assert len(ts) == len(set(ts)), "duplicate timestamps make ordering ambiguous"


def test_all_urls_are_defanged():
    body = open(os.path.join(CASE, "email_body.txt"), encoding="utf-8").read()
    assert "hxxps://" in body
    assert "https://" not in body.replace("hxxps://", "")
    assert "[.]" in body


def test_only_synthetic_domains_and_doc_ips():
    text = ""
    for root in (CASE, REF):
        for name in os.listdir(root):
            text += open(os.path.join(root, name), encoding="utf-8").read()
    # No real TLDs in addresses — only .test / .invalid are allowed.
    for addr in re.findall(r"[\w.-]+@[\w.-]+", text):
        dom = addr.split("@")[-1].rstrip(".")  # trim sentence punctuation
        assert dom.endswith(".test") or dom.endswith(".invalid"), addr
    # Any IPv4 literal must sit in the RFC 5737 documentation ranges.
    for ip in re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text):
        assert ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.")), ip


def test_attachment_hash_is_64_hex():
    att = load_json(os.path.join(CASE, "attachment_manifest.json"))["attachments"][0]
    assert re.fullmatch(r"[0-9a-f]{64}", att["sha256"]), att["sha256"]
    assert att["payload_included"] is False


def test_exposure_story_supported_by_events():
    px = load_jsonl(os.path.join(CASE, "proxy_events.jsonl"))
    assert any(e["event_type"] == "url_click_simulated" for e in px)
    assert all(e["action"] == "blocked_by_simulator" for e in px)
    assert all(e.get("credential_submission") is False for e in px)


if __name__ == "__main__":
    run_module_tests(dict(globals()))
