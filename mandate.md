# Agent Mandate — IT Helpdesk Intake Triage

**Version:** 1.0  
**Audience:** Legal, Security, Operations, Product  
**Status:** Approved for pilot

---

## The Problem

The IT helpdesk receives approximately 200 requests per day across email, a ticketing portal, and walk-up submissions. Every request is manually triaged by one of three L1 analysts. Average time-to-first-response is 4.2 hours. Priority misclassification rate (audited over 90 days) is 23%. Security incidents that arrived as low-priority requests: 4 in Q1 2026.

---

## What the Agent Decides Alone

The agent may take the following actions without human review:

| Action | Condition | Example |
|--------|-----------|---------|
| Route ticket to team queue | Confidence ≥ 0.70, no security flag, estimated_impact ≠ high | Broken keyboard → Desktop Support |
| Send self-service password reset link | Category = password_reset, confidence ≥ 0.85, auto_resolvable = true | Forgot Windows password |
| Push VPN client install via MDM | Category = vpn/connectivity, pre-approved device, confidence ≥ 0.85 | VPN broke after OS update |
| Provision pre-approved catalog software | Category = software_install, software in approved catalog, confidence ≥ 0.85 | Adobe Acrobat request |

---

## What the Agent Escalates to a Human

Escalation is triggered when **any one** of the following is true:

1. **Category** is in: `security_breach`, `malware`, `ransomware`, `account_compromise`, `suspicious_activity`, `data_loss`, `executive_request`
2. **Confidence** < 0.70 (agent is uncertain)
3. **Affected users** > 50 (potential widespread outage)
4. **Estimated impact** = "high"
5. **Security flag** = true (any signal of unauthorized access, credential abuse, or anomalous behavior)

Escalated tickets go to the Security Operations queue (P1/P2) or the Tier 2 Engineering queue (complex_issue) with the full reasoning chain attached.

---

## What We Are Deliberately Not Automating

The following will **never** be handled by the agent without human approval:

- **Privilege escalation** — any request for admin rights, sudo, elevated permissions, or security group changes  
- **Account actions on suspended/terminated employees** — terminated employees have frozen accounts; all actions require HR + Security sign-off  
- **Security incidents** — investigation, containment, and remediation are human-owned  
- **Data recovery from backups** — a human must verify the recovery scope and authorize the restore  
- **Executive account changes** — password resets, access grants, or device actions for VP+ require exec support team confirmation  
- **Multi-system access requests** — requests that touch more than one system go to IAM for holistic review  
- **Anything with unverifiable claimed authority** — the agent cannot verify that "the CISO approved this" or "HR authorized this bypass"

---

## What the Agent Must Never Do

- Store or log passwords, SSNs, payment card numbers, or other PII in ticket descriptions  
- Take action on behalf of a frozen/suspended account, regardless of who is requesting  
- Grant, escalate, or modify permissions without human sign-off  
- Respond to instructions embedded in ticket body content that attempt to override triage behavior  
- Expose one user's ticket history, personal data, or account details to another user

---

## Guardrails

**Hard stops (PreToolUse hook — deterministic, not prompt-based):**
- Frozen account in submitter or target → block all write tools  
- PII detected in ticket description → block ticket creation  
- High-risk action keyword in execute_resolution → block execution  

**Soft guardrails (prompt-based):**
- Confidence threshold for auto-resolution  
- Urgency inflation detection (described language vs. actual symptoms)  
- Prompt injection resistance instruction in classifier system prompt  

The distinction is intentional: hard stops handle known-dangerous patterns deterministically. Soft guardrails handle probabilistic judgment. An ADR records the reasoning.

---

## Metrics the Agent Is Held To

| Metric | Target | Measured by |
|--------|--------|-------------|
| Priority accuracy | ≥ 85% | Eval harness (labeled dataset) |
| Escalation accuracy | ≥ 90% | Eval harness |
| Adversarial pass rate | ≥ 80% | Challenge 6 adversarial set |
| False-confidence rate (conf ≥ 0.85, wrong priority) | ≤ 10% | Eval harness |
| PII block rate | 100% | Hook unit tests |
| Frozen account block rate | 100% | Hook unit tests |

The agent does not go to production until all targets are met. Legal has a copy of the eval harness output as a launch artifact.

---

## Not in Scope for Pilot

- Inbound email parsing (tickets submitted via API or portal only in pilot)  
- Slack/Teams message intake  
- Automatic ticket closure (humans close tickets; agent only creates and routes)  
- SLA breach notifications  
- Feedback loop to training data (planned for v2)
