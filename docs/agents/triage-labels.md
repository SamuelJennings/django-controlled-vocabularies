# Triage labels

Five labels carry the triage state of every issue.

| Label | Meaning |
|---|---|
| `needs-triage` | Maintainer needs to evaluate this issue. The default for anything freshly filed. |
| `needs-info` | Waiting on the reporter for more information before it can proceed. |
| `ready-for-agent` | Fully specified and self-contained — an automated agent can implement it unattended. |
| `ready-for-human` | Requires human implementation (judgement, access, or a decision an agent should not make). |
| `wontfix` | Considered and will not be actioned. |

An issue moves `needs-triage` → (`needs-info` ↔) → `ready-for-agent` or `ready-for-human`, or is
closed `wontfix`. Only `ready-for-agent` issues are safe to hand to an unattended implementer.
