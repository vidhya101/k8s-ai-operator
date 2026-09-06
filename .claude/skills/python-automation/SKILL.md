---
name: python-automation
description: Python for DevOps/infrastructure automation scripts — CLI tooling, dependency isolation, and cloud SDK usage patterns. Use when writing or reviewing a Python automation/tooling script, distinct from application code review.
---

# Python for Automation

Reference for infrastructure/automation scripts specifically (a deploy helper, a data-migration script, a
CLI tool) — see `code-review` and `testing` skills for general-purpose code review/test discipline that
applies equally here.

## Dependency Isolation

- Every script/tool gets a `requirements.txt`/`pyproject.toml` and a virtual environment — never rely on
  whatever happens to be installed in the system Python, which drifts between machines/CI runners.
- Pin dependency versions for anything run in CI/production (`==` or a lockfile) — floating ranges
  (`>=1.0`) are fine for a library meant to be broadly compatible, not for a deploy script whose behavior
  needs to be reproducible.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## CLI Tooling

- `argparse` (stdlib, no dependency) or `click`/`typer` (better ergonomics, adds a dependency) for
  anything with more than one flag — hand-rolled `sys.argv` parsing gets unwieldy and error-prone fast.
- Exit with a non-zero code on failure (`sys.exit(1)`) so the script composes correctly in a shell
  pipeline or CI step that checks `$?` — a script that always exits 0 breaks its callers' error handling.

## Cloud SDK Patterns

- `boto3` (AWS), `azure-sdk-for-python`, `google-cloud-python` — prefer the official SDK over shelling out
  to the CLI (`aws`/`az`/`gcloud`) from within a script when the SDK covers what's needed; shelling out
  works but loses structured error handling and typed responses.
- Credential resolution: let the SDK use its default credential chain (environment, instance metadata,
  Workload Identity) rather than hardcoding keys — same least-privilege/no-static-credentials principle
  as `aws`/`azure`/`gcp` skills.
- Handle the SDK's specific exception types for expected failure modes (e.g. `ClientError` with a
  `ResourceNotFoundException` code) rather than a bare `except Exception` that masks what actually failed.

## Logging & Output

- Use the `logging` module (not bare `print`) for anything that runs unattended (cron, CI) — gives you
  levels, timestamps, and the ability to redirect without code changes.
- Structured output (JSON) when a script's output is meant to be consumed by another tool/script; plain
  human-readable output when it's meant to be read directly — don't force one mode to serve both.

## Common Pitfalls

- Mutable default arguments (`def f(x=[]):`) — the classic Python gotcha where the default is shared and
  mutated across calls instead of being fresh each time.
- Bare `except:` (or `except Exception:`) swallowing errors that should have stopped the script, masking
  a real failure as a quiet no-op.
- A script that mutates cloud resources with no dry-run mode and no confirmation prompt, making every
  invocation as risky as a hand-typed `terraform apply -auto-approve`.
- Secrets read into a variable and then accidentally logged (`logging.info(f"config: {config}")` where
  `config` includes a credential) — audit what's actually in an object before logging it wholesale.
