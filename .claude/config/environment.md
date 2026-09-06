# Environment & Credentials — Reference Manifest

**One file every agent consults to know WHERE to find credentials, tokens, and service endpoints.**
This file contains **only references** — paths, env var names, secret-manager keys, URLs — never
actual secret values. `.claude/rules/secrets.md` still applies absolutely: a real credential landing
in this file (or any committed file) is a security incident.

If you need a real value at runtime: read from the reference this file names (env var, keychain
entry, Vault path, cloud secret manager). Don't paste the value here to "make it easier."

---

## 1. Cloud provider credentials

### AWS

- **CLI credentials**: `~/.aws/credentials` + `~/.aws/config` (deny-listed for `Read` tool per
  `settings.json`; agents use the AWS CLI/SDK which reads them, they don't read the files
  themselves)
- **Active profile selector**: `AWS_PROFILE` env var (set in the shell). Check with
  `aws sts get-caller-identity` before any mutating command per
  `.claude/rules/environment-awareness.md`.
- **Preferred pattern**: OIDC federation via `aws-actions/configure-aws-credentials` in GitHub
  Actions; IRSA / Pod Identity on EKS; short-lived session tokens via `aws sso login`. Long-lived
  access keys only where truly unavoidable.
- **MFA**: `AWS_MFA_SERIAL` env var if profile requires MFA; `aws sts get-session-token` for
  MFA-required operations.

### Azure

- **CLI**: `~/.azure/` (deny-listed for `Read`). Agents authenticate via `az login` interactively
  or via `az login --service-principal --federated-token $TOKEN` for CI.
- **Active subscription**: `az account show`; select with `az account set --subscription <id>`.
- **Preferred pattern**: Workload Identity Federation over stored service principal secrets;
  Managed Identity for Azure-hosted workloads.

### GCP

- **CLI**: `~/.config/gcloud/` (deny-listed for `Read`). Agents authenticate via
  `gcloud auth login`, `gcloud auth application-default login`, or Workload Identity Federation.
- **Active project**: `gcloud config get-value project`; set with
  `gcloud config set project <id>`.
- **Preferred pattern**: Workload Identity Federation; no downloaded service-account JSON keys.

### OCI (Oracle Cloud)

- **CLI**: `~/.oci/config` (treat as deny-listed even if not explicitly in `settings.json` yet —
  add if you set it up). Agents use the OCI CLI/SDK which reads it.
- **Preferred pattern**: instance principals when running inside OCI; resource principals for
  Functions.

---

## 2. AI provider tokens

**All AI tokens are env-var based.** Never in a committed file. Reference names below —
values live in your personal `~/.config/devops-tokens.env` (see §2a below), which your shell
profile sources so every process sees the env vars.

### 2a. The `~/.config/devops-tokens.env` pattern (the "one file for all tokens")

**Bootstrap once:**

```bash
.claude/scripts/setup-tokens.sh
```

That script:

- Copies the template at `.claude/config/tokens.env.template` → `~/.config/devops-tokens.env`
- `chmod 600` on the personal file (owner-only read/write)
- Adds a `source ~/.config/devops-tokens.env` line to your shell profile (`.zshrc` /
  `.bash_profile` / `.bashrc` per your shell) if not already there
- Idempotent — safe to re-run

**Then edit the personal file with your real tokens:**

```bash
${EDITOR:-vim} ~/.config/devops-tokens.env
```

**Reload your shell** (or `source ~/.config/devops-tokens.env`) so env vars take effect. Every
process you launch — `claude`, `docker`, `gh`, `terraform`, the sandbox container (when
`--env-file` is passed) — sees them.

**Guardrails in place:**

- The file is at `~/.config/devops-tokens.env` — OUTSIDE `.claude/`, so it can never be
  committed even accidentally with a `.claude/` copy
- `chmod 600` restricts to owner-read-only
- `.claude/hooks/block-secret-reads.sh` (`PreToolUse` on `Bash`) blocks any agent from
  `cat`/`grep`/`sed`/etc. against the file — agents must read env var VALUES, not the file
- `settings.json` `deny` list catches `Read` tool attempts against `**/*.env`, `**/devops-tokens.env`
- The template at `.claude/config/tokens.env.template` has only empty-string placeholders — safe
  to commit, useful as documentation of which vars exist

### 2b. Full env var reference

| Provider | Env var | Notes |
|---|---|---|
| Anthropic (Claude API) | `ANTHROPIC_API_KEY` | Also read by `claude` CLI |
| OpenAI | `OPENAI_API_KEY` | |
| Google Gemini | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Depends on SDK version |
| Cohere | `COHERE_API_KEY` | |
| Groq | `GROQ_API_KEY` | |
| Hugging Face | `HUGGINGFACE_API_TOKEN` or `HF_TOKEN` | |
| Together AI | `TOGETHER_API_KEY` | |
| Mistral | `MISTRAL_API_KEY` | |
| DeepSeek | `DEEPSEEK_API_KEY` | |
| Perplexity | `PERPLEXITY_API_KEY` | |
| Replicate | `REPLICATE_API_TOKEN` | |
| OpenRouter | `OPENROUTER_API_KEY` | Multi-provider gateway |

**Storage recommendation** (macOS): keep values in Keychain, expose via a small shell function
that populates env vars per session. Do NOT store in `~/.zshenv` unencrypted.

**Rotation**: any AI token that appears in a code commit, log line, or agent context is
compromised — rotate immediately, don't try to "clean it up." See `.claude/rules/secrets.md`.

---

## 3. Ollama (local LLM)

- **Default URL**: `http://localhost:11434` (Ollama's built-in server)
- **Override**: `OLLAMA_HOST` env var — e.g. `OLLAMA_HOST=http://192.168.56.60:11434` if running
  Ollama on the `monitor` VM instead of localhost
- **This URL is NOT a secret** — it's a localhost/LAN endpoint, safe to reference by value
- **Auth**: Ollama has no built-in auth. Do NOT expose `OLLAMA_HOST` beyond the LAN. If you need
  Ollama accessible over untrusted networks, put it behind an authenticating reverse proxy.
- **Model registry**: `ollama list` on the host running Ollama. Pull with `ollama pull <model>`.
- **Health check**: `curl $OLLAMA_HOST/api/tags` should return JSON with the installed models.
- **How agents call it**: HTTP POST to `$OLLAMA_HOST/api/generate` or `/api/chat`; or via LangChain
  / LlamaIndex adapters; or via the `ollama` Python/Go/JS clients.

---

## 4. Internal service credentials

### Postgres (fleet ledger / audit sink on `tools` and `monitor` VMs)

- **Connection strings**: env vars, NOT in code. Convention:
  `FLEET_LEDGER_URL=postgres://fleet@192.168.56.50:5432/fleet` (password via `PGPASSWORD` env or
  `~/.pgpass` file — the latter is deny-listed for `Read`, agents use `psql` which reads it)
- **Audit sink**: `FLEET_AUDIT_URL` — separate creds, append-only role only
- **`~/.pgpass`** format: `hostname:port:database:username:password` with file mode `600`
- Never `psql -c "$sql"` with a variable expanded from a prior tool call — see the block-secret-
  reads hook and code-quality rule's SQL discipline

### Vault (if in use)

- **Address**: `VAULT_ADDR` env var (e.g. `https://vault.internal:8200`)
- **Auth token**: `VAULT_TOKEN` env var (short-lived — obtain via `vault login` with a real auth
  method: OIDC, K8s SA, cloud IAM). NEVER hardcode a root token in a file.
- **Paths**: `secret/data/<team>/<service>` KV v2, or engine-specific paths (`aws/`, `database/`,
  `pki/`). See `vault` skill.

### GitHub

- **CLI**: `gh auth login` — token stored in macOS keychain by default; env var
  `GH_TOKEN` overrides for CI/scripts
- **Preferred for automation**: OIDC federation over long-lived PATs where the target platform
  supports it (see `github-actions` skill)

### Docker registries

- **GHCR**: `~/.docker/config.json` after `docker login ghcr.io` — token from `GH_TOKEN` or a PAT
  with `write:packages`; prefer `GITHUB_TOKEN` from GitHub Actions over a long-lived PAT
- **ECR / ACR / GCR**: use the cloud CLI for temporary credentials (`aws ecr get-login-password |
  docker login`, `az acr login`, `gcloud auth configure-docker`) — no static creds
- **Nexus / JFrog**: env vars per project, referenced from CI, not stored in
  `~/.docker/config.json` for machines other than the CI runner

### Kubernetes

- **Kubeconfig**: `~/.kube/config` (deny-listed for `Read`). Populated per-cluster via
  `aws eks update-kubeconfig`, `az aks get-credentials`, `gcloud container clusters get-credentials`,
  or Vagrant-provisioned kubeadm cluster files
- **Active context**: `kubectl config current-context` — always confirm before mutating,
  per `.claude/rules/environment-awareness.md`
- **In-cluster**: pods use `ServiceAccount` tokens auto-mounted at
  `/var/run/secrets/kubernetes.io/serviceaccount/`; don't attempt to read from outside a pod

---

## 5. Secret manager reference paths

Where a secret's authoritative copy actually lives (so agents know where to point Terraform data
sources / External Secrets Operator / Vault agent injector at — not the value):

| Secret class | Source of truth | Reference format |
|---|---|---|
| Cloud IAM user access keys | AWS Secrets Manager | `arn:aws:secretsmanager:<region>:<account>:secret:<name>` |
| Database passwords | AWS Secrets Manager / Azure Key Vault / Vault | Provider-specific ARN / URI / path |
| API tokens for third-party SaaS | Vault `secret/data/<team>/<service>` | Provider path |
| TLS private keys | cert-manager (auto-managed) or Vault PKI | K8s Secret name / Vault path |
| SSH keys for automation | Vault `ssh/<role>` or 1Password | Path only |
| SOPS-encrypted files in git | Path in repo | Only encrypted form is committed |

---

## 6. What agents should DO with this file

1. Before running any command that needs a credential, consult this file to know which env var /
   path / secret-manager reference is authoritative.
2. If a credential env var isn't set that the task needs, STOP and ask the user rather than
   inventing a value or hardcoding one.
3. If you discover a real credential in code / config / logs during any task, that's a
   `.claude/rules/secrets.md` incident — flag it, don't silently continue.
4. Never write a real credential value into memory (`mcp__memory__*`), a log, a comment, an
   artifact, or this file — same rule.

## 7. Owner context (non-secret facts about this specific setup)

Public identifiers and environment facts that agents can reference safely. NOT credentials.

- **GitHub username**: `vidhya101`
- **LinkedIn**: https://www.linkedin.com/in/vidhyashankergoel/
- **Local Ollama models available** (query live with `curl $OLLAMA_HOST/api/tags`):
  - `codellama:7b` (3.8 GB) — code completion, small
  - `codellama:13b` (7.4 GB) — code completion, larger
  - `deepseek-coder:6.7b` (3.8 GB) — code, small
  - `llama3:latest` / `llama3:8b` (4.7 GB) — general
  - `mistral:latest` (4.4 GB, has tool-calling capability) — general + tool use
  - `mixtral:latest` (26 GB) — mixture-of-experts, larger context
- **Local Ansible lab** at `~/devops-lab/ansible/` — targets 11 hosts across two laptops (macOS + Windows-hosted VMs). Agents can use it via:
  ```bash
  cd ~/devops-lab/ansible
  make inventory                                # see the full 11-host graph
  make ping                                     # confirm reachability
  make push HOSTS=workers CMD="uptime"          # Linux workers (local + Windows-hosted)
  make push HOSTS=windows_hosts CMD="Get-Date"  # Windows laptop itself
  ```
  This is a legitimate execution surface for any manager whose plan involves multi-host config
  work (ansible-manager especially).

## 8. AWS guardrails — hard budget policy

This is a home-lab / consulting-solo AWS account. **HARD CEILING: 50 CAD/month.** Any agent
touching AWS respects these rules:

- **Free-tier first**: prefer `t3.micro` / `t4g.micro`, S3 free tier limits, DynamoDB free tier,
  Lambda free tier, CloudWatch free tier. If a workload doesn't fit free tier, flag it — don't
  silently provision paid capacity.
- **Budget alert must exist** — if a budget alert isn't already set at 40 CAD (warn) and 50 CAD
  (hard-stop), the FIRST thing any AWS-touching task does is create one:
  ```bash
  aws budgets create-budget --account-id <acct> --budget file://budget.json
  # with BudgetLimit: {Amount: "50", Unit: "CAD"} and per-service breakdown
  ```
- **No always-on paid resources** without explicit user approval — no NAT Gateways (~40 CAD/mo
  alone), no idle RDS instances, no unused Elastic IPs, no ALB/NLB left running past a test.
- **Every workload gets a shutdown plan** stated up front — a scheduled `aws ec2 stop-instances`
  cron for anything left running, or an explicit "this is designed to run 24/7 and here's why."
- **Region**: default to `us-east-1` (cheapest for most services); explicitly ok to override
  when data residency requires.

principal-finops-engineer + cloud-manager both enforce this. See also
`.claude/agents/principal-finops-engineer.md` for the general FinOps discipline.

## 9. What this file does NOT contain

- Actual API keys, passwords, tokens, private keys, connection strings with real credentials
- Anything that would compromise anything if this file were public
- Client-specific credential VALUES from any specific engagement

If you're tempted to paste a real value here "just for this project," don't. Add a reference
(env var name, path, secret-manager entry) and populate the real value out-of-band.
