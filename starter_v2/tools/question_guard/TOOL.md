---
name: question_guard
track: core
kind: local_security
requires_env: []
inputs: [text]
outputs: [allowed, action, risk_level, categories, reasons]
side_effect: false
---
# question_guard

Audits a user-supplied prompt for explicit instruction override, role spoofing,
secret-exfiltration, forged tool-call and jailbreak signals. The orchestration
layer applies the same check automatically before the model; the model should
call this tool only when the user explicitly asks for a prompt-security audit.

This heuristic is one defense layer, not a proof that arbitrary text is safe.
