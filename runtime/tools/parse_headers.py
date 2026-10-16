#!/usr/bin/env python3
"""Inspect header identity fields and flag alignment / lookalike indicators.

Usage: parse_headers.py
"""
from _common import REF_DIR, load_json


def domain_of(addr):
    return addr.split("@")[-1].strip().lower() if "@" in addr else addr.strip().lower()


def main():
    headers = load_json("email_headers.json")
    trusted = load_json("trusted_domains.json", base=REF_DIR)

    from_dom = domain_of(headers["from_address"])
    reply_dom = domain_of(headers["reply_to"])
    trusted_all = set(trusted.get("organization_domains", [])) | set(
        trusted.get("trusted_partner_domains", [])
    )

    print("Identity")
    print(f"  From domain     : {from_dom}")
    print(f"  Reply-To domain : {reply_dom}")
    print(f"  Return-Path     : {headers['return_path']}")
    print()
    print("Checks")
    print(f"  Reply-To alignment : {'ALIGNED' if from_dom == reply_dom else 'MISMATCH'}")
    print(f"  From in trusted?   : {'yes' if from_dom in trusted_all else 'NO (untrusted)'}")
    auth = headers["authentication_results"]
    print(f"  SPF / DKIM / DMARC : {auth['spf']} / {auth['dkim']} / {auth['dmarc']}")
    print()
    print(f"  Trusted domains    : {', '.join(sorted(trusted_all)) or '(none)'}")
    print("  Note: SPF pass covers the envelope domain, not the visible From.")
    print("        Judge impersonation via DMARC alignment + lookalike comparison.")


if __name__ == "__main__":
    main()
