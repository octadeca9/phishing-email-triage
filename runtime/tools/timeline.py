#!/usr/bin/env python3
"""Build a chronological timeline across gateway, mailbox, and proxy logs.

Usage: timeline.py
"""
from _common import all_events


def main():
    events = sorted(all_events(), key=lambda e: e["timestamp"])
    print(f"{'event_id':<9}  {'timestamp':<21}  {'event_type':<20}  who")
    print("-" * 78)
    for e in events:
        who = e.get("recipient") or e.get("user") or "-"
        print(f"{e['event_id']:<9}  {e['timestamp']:<21}  {e['event_type']:<20}  {who}")

    order = [e["event_id"] for e in events]
    print("-" * 78)
    print("Chronological order: " + " -> ".join(order))


if __name__ == "__main__":
    main()
