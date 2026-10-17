# Phishing Email Triage — SOC Analyst Lab (Medium)

A **Medium-level SOC Analyst training lab** for the hack.redlimit.id platform. A
participant acts as an L1/L2 analyst triaging a single simulated phishing email
across **3 sections / 18 tasks / 54 points** (3 points per task): analyzing
synthetic headers, SPF/DKIM/DMARC results, a defanged URL, attachment metadata,
and gateway/mailbox/proxy events, then submitting a structured verdict.

All data is **synthetic and inert**. No real domains, no email is ever sent, no
URL is clickable, and no attachment payload exists. Domains use `.test`/
`.invalid`, IPs come from the RFC 5737 documentation range (`192.0.2.0/24`), and
every URL is defanged (`hxxps://…[.]invalid/…`).

> This repository is a **development / reference** build. `compose.yaml` is NOT
> the multi-tenant production controller — production isolation, per-session
> runtimes, egress policy, and image pinning are the platform's Docker Spawn
> controller's job.

## Architecture

Two containers with a hard trust boundary between them:

| Container | Role | Participant can touch? |
|---|---|---|
| **`lab`** (runtime) | Browser-terminal workspace (`ttyd`, port 7681) with read-only analysis tools; mounts the dataset read-only at `/data`; non-root, read-only FS, caps dropped. Reachable by the platform's web proxy; egress restriction is enforced by the platform network policy in production. | Yes |
| **`validator`** | Trusted, internal-only scoring service holding the private answer key and rubric. Exposes a conceptual HTTP API; never reachable from the `lab` container or the host. | **No** |

The answer key (`validator/answer_key.private.json`) is **development only**. It
is supplied to the validator via a secret mount at runtime
(`/run/secrets/answer_key`) and is **never** `COPY`'d into any image, never
placed in `/data`, and never on the participant filesystem.

## Repository layout

```text
phishing-email-triage/
├── README.md                 # this file
├── compose.yaml              # dev/reference two-container environment
├── .env.example              # optional validator scoring knobs
├── .dockerignore             # keeps docs/tests/answer key out of build contexts
├── runtime/                  # participant-facing container
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── tools/                # read-only CLI analysis tools
│       ├── _common.py
│       ├── email_summary.py
│       ├── parse_headers.py
│       └── timeline.py
├── validator/                # trusted scoring container
│   ├── Dockerfile
│   ├── app.py                # stdlib-only HTTP validator
│   ├── requirements.txt
│   ├── task_definitions.public.json   # no answers
│   └── answer_key.private.json         # dev only; secret-mounted in prod
├── data/
│   ├── case/                 # the synthetic evidence truth set
│   └── reference/            # trusted_domains.json + field_guide.md
├── tests/                    # pytest: consistency, validation, scoring, security
└── docs/                     # PRD / BLUEPRINT pointers + PARTICIPANT_GUIDE
```

## Quick start (Compose)

The participant lab and the scoring validator are deliberately split: in
production, **scoring and the private answer key live in the platform
(hack.redlimit.id), not in this Compose stack**. So a plain `docker compose up`
starts only the participant `lab`, and the `validator` service is kept behind the
`dev` profile for local development.

```bash
docker compose config            # validate the compose file
docker compose build             # build the lab image
docker compose up -d             # deploy: start ONLY the participant lab
docker compose run --rm lab sh   # drop into a direct CLI workspace (local)
docker compose down
```

The `lab` service runs a **browser terminal** (`ttyd`) and exposes it on port
`7681`, so the deploy platform's web proxy can route participants straight into
the locked-down workspace. The container honors a `PORT` environment variable if
the platform injects one. Access is unauthenticated by design; the container is
still non-root, read-only, and capability-dropped.

The validator needs the private answer-key file and is therefore **local dev
only** — never required on the deploy host:

```bash
docker compose --profile dev up -d validator   # start validator (internal-only)
docker compose --profile dev logs -f validator
```

> The deploy host only clones the repo, where `validator/answer_key.private.json`
> is intentionally absent (git-ignored). Because the validator sits behind the
> `dev` profile, a default `docker compose up` never references that secret, so
> the deploy does not fail on the missing file.

Inside the `lab` workspace, the dataset is at `/data/case` and `/data/reference`.
Three tools are on `PATH`:

```bash
email_summary.py     # one-screen case overview: alert, sender, auth, URL, attachment
parse_headers.py     # identity fields + Reply-To alignment + lookalike / auth checks
timeline.py          # chronological event order across all three logs
```

## Running the tests

The suite runs without Docker (the validator falls back to the local answer-key
file when no secret is mounted):

```bash
pip install pytest
pytest tests/ -q
```

- `test_dataset_consistency.py` — the truth set agrees across all files.
- `test_task_validation.py` — public tasks and the private key stay aligned.
- `test_scoring.py` — deterministic grading per `input_type` + hint penalty.
- `test_security_config.py` — the runtime lockdown invariants in `compose.yaml`.

## Scoring model

Scoring is **deterministic and server-side**: exact-match / enum validation
after explicit normalization (trim, collapse whitespace, case-fold unless a task
is marked case-sensitive). No substring matching, no AI judging. The final report
(`S3-T6`) is graded by a fixed rubric with partial per-field credit. Submissions
expose only correctness and points — never the accepted values.

## Non-negotiable invariants

1. The answer key never touches the participant side.
2. All data is synthetic and inert.
3. All URLs are defanged.
4. Scoring is deterministic and server-side.
5. Truth-set consistency is mandatory (every `message_id`, recipient, timestamp,
   and event agrees across files; every task is answerable from the evidence).
6. The runtime is locked down: non-root, `read_only`, `cap_drop: [ALL]`,
   `no-new-privileges`, resource limits, internal-only network, no Docker socket.

## Platform integration

The hack.redlimit.id API contract does not exist yet. The HTTP endpoints in
`validator/app.py` are **conceptual**. Build against an adapter/mock; do not wire
real external integration until the official contract is provided.

## Documentation

- [`docs/PARTICIPANT_GUIDE.md`](docs/PARTICIPANT_GUIDE.md) — how to work the case.

The authoritative PRD and Blueprint source documents are kept **internal** and
are intentionally excluded from the published repository (see `.gitignore`).
