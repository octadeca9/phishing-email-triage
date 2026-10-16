#!/bin/sh
set -eu
printf '%s\n' 'Phishing Email Triage — Medium'
printf '%s\n' 'Synthetic dataset only. Do not visit URLs or execute attachments.'
printf '%s\n' 'Evidence path: /data/case    Reference: /data/reference'
printf '%s\n' 'Tools: email_summary.py | parse_headers.py | timeline.py'
exec "$@"
