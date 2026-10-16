"""Exercise the validator Scorer: correctness, normalization, hint penalty,
and the deterministic report rubric."""
from _util import load_validator_module, run_module_tests

APP = load_validator_module()
SCORER = APP.SCORER


def test_correct_string_full_points():
    correct, awarded, mx = SCORER.score("S1-T1", "PHISH-2026-0042", 0)
    assert correct and awarded == 3 and mx == 3


def test_string_normalization_is_case_and_space_insensitive():
    correct, awarded, _ = SCORER.score("S1-T2", "  Notice@Payr0ll-Notice.Invalid ", 0)
    assert correct and awarded == 3


def test_url_task_is_case_sensitive():
    good, _, _ = SCORER.score("S2-T1", "hxxps://secure-document[.]invalid/review/CASE-0042", 0)
    bad, _, _ = SCORER.score("S2-T1", "hxxps://secure-document[.]invalid/review/case-0042", 0)
    assert good and not bad


def test_wrong_answer_scores_zero():
    correct, awarded, _ = SCORER.score("S1-T3", "aligned", 0)
    assert not correct and awarded == 0


def test_number_task_accepts_numeric_forms():
    for val in (2, "2", "2.0"):
        correct, awarded, _ = SCORER.score("S2-T5", val, 0)
        assert correct and awarded == 3, val


def test_multi_select_requires_exact_set_order_independent():
    good, _, _ = SCORER.score(
        "S1-T6", ["reply_to_mismatch", "lookalike_from_domain", "dmarc_fail", "spf_pass"], 0)
    missing, _, _ = SCORER.score("S1-T6", ["reply_to_mismatch", "dmarc_fail"], 0)
    extra, _, _ = SCORER.score(
        "S1-T6", ["spf_pass", "dmarc_fail", "reply_to_mismatch", "lookalike_from_domain", "dkim_signed"], 0)
    assert good and not missing and not extra


def test_ordering_exact_sequence():
    good, _, _ = SCORER.score("S3-T1", ["gw-0001", "gw-0002", "gw-0003", "mb-0001", "px-0001"], 0)
    bad, _, _ = SCORER.score("S3-T1", ["gw-0001", "gw-0003", "gw-0002", "mb-0001", "px-0001"], 0)
    assert good and not bad


def test_hint_penalty_caps_points():
    _, zero, _ = SCORER.score("S1-T1", "PHISH-2026-0042", 0)
    _, one, _ = SCORER.score("S1-T1", "PHISH-2026-0042", 1)
    _, two, _ = SCORER.score("S1-T1", "PHISH-2026-0042", 2)
    _, three, _ = SCORER.score("S1-T1", "PHISH-2026-0042", 5)
    assert (zero, one, two, three) == (3, 2, 1, 1)  # floor at 1


def test_report_full_rubric():
    report = {
        "case_id": "PHISH-2026-0042",
        "verdict": "phishing",
        "severity": "medium",
        "confidence": "high",
        "user_exposure": "clicked_blocked",
        "key_evidence": ["reply_to_domain_mismatch", "dmarc_alignment_failure",
                          "lookalike_sender_domain", "suspicious_defanged_url"],
        "recommended_actions": ["quarantine_related_messages", "block_ioc_at_email_gateway",
                                "notify_affected_users"],
        "rationale": "Impersonating sender, DMARC fail, blocked click.",
    }
    correct, awarded, _ = SCORER.score("S3-T6", report, 0)
    assert correct and awarded == 3.0


def test_report_partial_credit_is_deterministic():
    report = {"verdict": "phishing", "severity": "low", "confidence": "high",
              "user_exposure": "clicked_blocked", "key_evidence": [], "recommended_actions": []}
    c1, a1, _ = SCORER.score("S3-T6", report, 0)
    c2, a2, _ = SCORER.score("S3-T6", report, 0)
    assert a1 == a2 == 1.25 and not c1 and not c2  # verdict .5 + confidence .25 + exposure .5


def test_perfect_run_totals_54():
    perfect = {
        "S1-T1": "PHISH-2026-0042", "S1-T2": "notice@payr0ll-notice.invalid",
        "S1-T3": "mismatch", "S1-T4": "fail", "S1-T5": "payr0ll-notice.invalid",
        "S1-T6": ["spf_pass", "dmarc_fail", "reply_to_mismatch", "lookalike_from_domain"],
        "S2-T1": "hxxps://secure-document[.]invalid/review/CASE-0042",
        "S2-T2": ["untrusted_host_domain", "credential_or_document_lure_path"],
        "S2-T3": "mismatch",
        "S2-T4": "a1b2c3d4e5f60718293a4b5c6d7e8f901122334455667788990011223344abcd",
        "S2-T5": 2, "S2-T6": "clicked_blocked",
        "S3-T1": ["gw-0001", "gw-0002", "gw-0003", "mb-0001", "px-0001"],
        "S3-T2": "attempted_blocked", "S3-T3": "medium", "S3-T4": "phishing",
        "S3-T5": ["quarantine_related_messages", "block_ioc_at_email_gateway", "notify_affected_users"],
        "S3-T6": {"verdict": "phishing", "severity": "medium", "confidence": "high",
                  "user_exposure": "clicked_blocked",
                  "key_evidence": ["reply_to_domain_mismatch", "dmarc_alignment_failure",
                                   "lookalike_sender_domain"],
                  "recommended_actions": ["quarantine_related_messages",
                                          "block_ioc_at_email_gateway", "notify_affected_users"]},
    }
    total = 0.0
    for tid, ans in perfect.items():
        correct, awarded, _ = SCORER.score(tid, ans, 0)
        assert correct, tid
        total += awarded
    assert round(total, 2) == 54.0


if __name__ == "__main__":
    run_module_tests(dict(globals()))
