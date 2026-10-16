"""Verify public task definitions and the private answer key stay aligned,
and that every task answer is derivable from the provided evidence."""
import os

from _util import CASE, VALIDATOR, load_json, load_jsonl, run_module_tests

PUBLIC = load_json(os.path.join(VALIDATOR, "task_definitions.public.json"))
KEY = load_json(os.path.join(VALIDATOR, "answer_key.private.json"))


def test_eighteen_tasks_three_sections():
    assert len(PUBLIC["tasks"]) == 18
    assert len(PUBLIC["sections"]) == 3


def test_every_task_has_a_key_and_matching_type():
    for t in PUBLIC["tasks"]:
        k = KEY["keys"][t["task_id"]]
        assert k["input_type"] == t["input_type"], t["task_id"]
        assert k["points"] == t["points"] == 3


def test_total_points_is_54():
    assert sum(t["points"] for t in PUBLIC["tasks"]) == 54


def test_public_tasks_contain_no_answers():
    banned = ("accepted_values", "accepted_set", "accepted_order", "rubric", "validator_key")
    for t in PUBLIC["tasks"]:
        for b in banned:
            assert b not in t, f"{t['task_id']} leaks {b}"


def test_multi_and_single_answers_are_valid_options():
    for t in PUBLIC["tasks"]:
        k = KEY["keys"][t["task_id"]]
        opts = t.get("options")
        if t["input_type"] == "single_choice":
            assert all(v in opts for v in k["accepted_values"]), t["task_id"]
        if t["input_type"] == "multi_select":
            assert set(k["accepted_set"]).issubset(set(opts)), t["task_id"]
        if t["input_type"] == "ordering":
            assert set(k["accepted_order"]) == set(opts), t["task_id"]


def test_dependencies_reference_real_tasks():
    ids = {t["task_id"] for t in PUBLIC["tasks"]}
    for t in PUBLIC["tasks"]:
        for dep in t.get("dependencies", []):
            assert dep in ids, f"{t['task_id']} -> {dep}"


def test_key_answers_match_evidence():
    headers = load_json(os.path.join(CASE, "email_headers.json"))
    alert = load_json(os.path.join(CASE, "alert.json"))
    att = load_json(os.path.join(CASE, "attachment_manifest.json"))["attachments"][0]
    gw = load_jsonl(os.path.join(CASE, "gateway_events.jsonl"))

    k = KEY["keys"]
    assert k["S1-T1"]["accepted_values"][0] == alert["alert_id"]
    assert k["S1-T2"]["accepted_values"][0] == headers["from_address"]
    assert k["S1-T4"]["accepted_values"][0] == headers["authentication_results"]["dmarc"]
    assert k["S1-T5"]["accepted_values"][0] == headers["from_address"].split("@")[-1]
    assert k["S2-T4"]["accepted_values"][0] == att["sha256"]
    delivered = {e["recipient"] for e in gw if e["event_type"] == "message_delivered"}
    assert k["S2-T5"]["accepted_values"][0] == len(delivered)


def test_report_rubric_sums_to_task_points():
    rubric = KEY["keys"]["S3-T6"]["rubric"]
    assert round(sum(f["points"] for f in rubric.values()), 2) == 3.0


if __name__ == "__main__":
    run_module_tests(dict(globals()))
