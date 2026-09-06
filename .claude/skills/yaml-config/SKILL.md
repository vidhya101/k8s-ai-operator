---
name: yaml-config
description: YAML authoring gotchas that cause silent misconfiguration — indentation, type coercion, anchors/aliases, and multiline strings. Use when writing or debugging YAML for Kubernetes, Ansible, CI, or Helm, especially when something parses "successfully" but behaves wrong.
---

# YAML Configuration

YAML underlies nearly everything in this stack (Kubernetes manifests, Ansible playbooks, CI workflows,
Helm values) — most YAML bugs aren't syntax errors (which fail loudly), they're valid-YAML-that-means-
something-other-than-intended, which fails silently.

## Type Coercion Surprises

```yaml
enabled: yes        # parses as boolean `true` in YAML 1.1 (used by most parsers) — NOT the string "yes"
version: "1.20"      # quoted — stays the string "1.20"
version: 1.20         # unquoted — parses as the number 1.2 (trailing zero dropped!)
region: no            # parses as boolean `false`, not the string "no" — infamous "Norway problem"
port: 08080            # a leading zero can trigger octal interpretation in some parsers/contexts
```

Always quote a value that's meant to be a string but looks like a bool/number/date to a YAML parser —
version numbers, port numbers meant to stay exact, and words like `yes`/`no`/`on`/`off`/`null` used as
plain strings are the recurring offenders.

## Indentation

- YAML structure is defined by indentation — mixing tabs and spaces is invalid, and inconsistent space
  counts silently change nesting (a key indented one space too far becomes a child of the wrong parent
  instead of a sibling, with no error).
- Lists (`- item`) can be indented at the same level as their parent key or nested further — be
  consistent with the file's existing convention rather than mixing styles within one file.

## Multiline Strings

```yaml
literal: |
  This preserves
  line breaks exactly.
folded: >
  This folds
  lines into one
  space-separated string.
literal_strip: |-
  No trailing newline.
folded_keep: >+
  Keeps trailing newlines.
```

Picking the wrong block style (`|` vs `>`) is a common source of a script/config value having unexpected
embedded newlines or missing them — verify with the actual parsed value, not just visual inspection of
the YAML source.

## Anchors & Aliases (DRY within one file)

```yaml
defaults: &defaults
  timeout: 30
  retries: 3

service_a:
  <<: *defaults      # merge key: inherits defaults, can override specific fields below
  retries: 5
```

Useful for reducing duplication (e.g. shared resource limits across multiple Kubernetes manifests in one
file, or shared CI job settings) — but an anchor defined and never referenced, or a merge key overridden
in a way that isn't obvious at a glance, makes the file harder to reason about than plain duplication
would have. Use for genuine repetition, not as a default style.

## Common Pitfalls

- An unquoted `yes`/`no`/`on`/`off`/`true`/`false`-looking value intended as a string (a country code
  `NO` for Norway, a feature name `on`) silently becoming a boolean — validate with a linter/parser dry
  run, not just visual review.
- A YAML file that's valid syntax but semantically wrong feeding straight into `kubectl apply`/
  `terraform` /`ansible-playbook` with no schema validation step (`kubeconform`, `ansible-lint`,
  `terraform validate`) catching the mismatch before it reaches the target system.
- Duplicate keys in the same mapping — most parsers silently take the last one with no warning, which can
  hide a copy-paste mistake.
- Trailing whitespace or invisible characters copied from a rich-text source (Slack, a doc) breaking
  YAML parsing in a way that's hard to spot visually.
