#!/usr/bin/env python3
"""Print a one-screen summary of the case: alert, sender, auth, URL, attachment.

Usage: email_summary.py
"""
from _common import load_json, load_text


def main():
    manifest = load_json("case_manifest.json")
    alert = load_json("alert.json")
    headers = load_json("email_headers.json")
    attach = load_json("attachment_manifest.json")

    print(f"Case        : {manifest['case_id']} — {manifest['title']}")
    print(f"Difficulty  : {manifest['difficulty']}  (simulation_only={manifest['simulation_only']})")
    print("-" * 64)
    print(f"Alert ID    : {alert['alert_id']}")
    print(f"Alert source: {alert['source']}")
    print(f"Alert rule  : {alert['rule_name']}  (severity={alert['severity']})")
    print(f"Recipients  : {alert['recipient_count']}  initial_action={alert['initial_action']}")
    print("-" * 64)
    print(f"From        : {headers['from_display_name']} <{headers['from_address']}>")
    print(f"Return-Path : {headers['return_path']}")
    print(f"Reply-To    : {headers['reply_to']}")
    print(f"To          : {', '.join(headers['to'])}")
    print(f"Subject     : {headers['subject']}")
    auth = headers["authentication_results"]
    print(f"Auth        : spf={auth['spf']} dkim={auth['dkim']} dmarc={auth['dmarc']}")
    print("-" * 64)
    a = attach["attachments"][0]
    print(f"Attachment  : {a['filename']}")
    print(f"  declared  : {a['declared_content_type']}")
    print(f"  observed  : {a['observed_content_type']}")
    print(f"  sha256    : {a['sha256']}")
    print(f"  payload   : included={a['payload_included']}")
    print("-" * 64)
    print("Body:")
    print(load_text("email_body.txt").rstrip())


if __name__ == "__main__":
    main()
