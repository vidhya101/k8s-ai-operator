---
description: Add inline documentation (docstrings/comments) to code, following each language's standard convention.
argument-hint: "<file or function to document>"
---

Document: $ARGUMENTS

- Match the target language's standard convention: docstrings for Python (PEP 257 style), JSDoc for
  JS/TS, godoc-style comments for Go, standard Ansible task `name:`/module documentation for playbooks,
  Terraform variable/output `description` fields (not comments) for `.tf` files.
- Document the WHY, not the WHAT — well-named code already shows what it does. A docstring on a public
  function/module's purpose and non-obvious parameters is still valuable; a comment restating an obvious
  line is not.
- Don't add documentation nobody asked for across the whole file if the request was scoped to one
  function — match the requested scope (Section 1.3, surgical changes).
- For Terraform: `description` on every variable/output, not a floating comment above it — that's what
  tools like `terraform-docs` read to auto-generate module documentation.
