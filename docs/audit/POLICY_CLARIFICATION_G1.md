# POLICY_CLARIFICATION_G1.md
## G1 Deterministic Safety Runtime — Operational Policy Clarification
**Version:** 1.0 — 4I-P3
**Date:** 2026-06-21
**Status:** Active
**Closes:** DT-4F-003 (TX-009 exact gate condition — see Section 1)
**Derived from:** Code audit 4I, SAFETY_MODEL_G1.md (4I-P1), TRACEABILITY_MATRIX_G1.md (4I-P2)
**Repository:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Roles:** PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla

---

## Purpose

This document converts the operational policies of the G1 Deterministic Safety Runtime into explicit written contracts: what the runtime does, under what condition, what it does not promise, and what technical debt remains open.

Stage 4I does not introduce new runtime behavior. This document formalizes existing behavior as auditable policy.

---

## 1. TX-009 — POLICY_GATED Exact Condition

**Debt closed by this section:** DT-4F-003

### 1.1 Extracted from Code

The exact condition for TX-009 is extracted from `_eval_TX009()` in `safety_orchestrator_g1.py`:

```python
def _eval_TX009(self, event_type, state):
    if state.restriction_level != 'R4-halt':
        return None
    if event_type != 'POLICY_GATE_AUTHORIZED_EMERGENCY_SIT':
        return None
    ...
```

### 1.2 Policy Contract

TX-009 fires if and only if **both** conditions are satisfied simultaneously:

| Condition | Required value |
|---|---|
| Current `restriction_level` | `R4-halt` |
| Incoming `event_type` | `POLICY_GATE_AUTHORIZED_EMERGENCY_SIT` |

If either condition is not met, `_eval_TX009()` returns `None` and the transition does not fire.

### 1.3 Resulting Action

When TX-009 fires:

- **Action:** `emergency_sit`
- **Target restriction level:** `R4-sit`
- **Target risk level:** unchanged (same as current `state.risk_level`)
- **Execution authority:** `POLICY_GATED`
- **Execution confidence:** `VERIFIED` if current `risk_level == STABILITY_RISK`; otherwise `BEST_EFFORT`

### 1.4 What TX-009 Does Not Do

- TX-009 does not fire from any state other than `R4-halt`.
- TX-009 does not fire from a watchdog or observer event directly — it requires `POLICY_GATE_AUTHORIZED_EMERGENCY_SIT` as the explicit event type.
- TX-009 does not change the risk level.

### 1.5 Closure of DT-4F-003

The exact policy-gate condition has been extracted from code without ambiguity:

> TX-009 requires `restriction_level == 'R4-halt'` AND `event_type == 'POLICY_GATE_AUTHORIZED_EMERGENCY_SIT'`.

**DT-4F-003 is closed by this section.**

---

## 2. Single-Flight Recovery Policy

### 2.1 Mechanism

`recovery_g1` uses a single-flight mutex implemented via `_recovery_active: bool` protected by `_recovery_lock: threading.Lock()`.

Behavior:

```
Event arrives → _on_safety_event() or _on_safety_action()
  → acquire _recovery_lock
  → if _recovery_active == True:
      log debug "Recovery ya en curso — evento ignorado"
      return  ← second event discarded
  → set _recovery_active = True
  → release lock
  → execute recovery action
  → acquire _recovery_lock
  → set _recovery_active = False
  → release lock
```

### 2.2 Policy Contract

| Property | Contract |
|---|---|
| First accepted event | Executes to completion |
| Second event arriving during active recovery | Discarded with debug log |
| Internal priority queue | None — no priority scheduler inside `recovery_g1` |
| Preemption | Not supported — active recovery runs to completion |
| Applicability | Applies to both direct path (`_on_safety_event`) and governed path (`_on_safety_action`) |

### 2.3 What This Policy Does Not Claim

- This is a documented operational policy, not a certified priority scheduler.
- Higher-severity events arriving during active recovery are not guaranteed to preempt the current recovery action.
- No ordering guarantee is made between simultaneous events from different sources.

---

## 3. Governed Path vs Direct Path

### 3.1 Policy Contract

The runtime contains two active recovery input paths with different properties:

| Property | Governed Path | Direct Path |
|---|---|---|
| Input | `SafetyAction` from `/safety_actions` | `SafetyEvent` from `/safety_events` |
| Causal detail preserved | No — `SafetyAction` does not carry `rule_id` or watchdog cause | Yes — `SafetyEvent.notes` carries `rule_id=4F-P2-*` |
| Orchestrator governance | Yes — transition evaluated and governed by TX matrix | No — bypasses orchestrator |
| Used for | TX-011 physical-instability path | Watchdog faults (STALE, FREEZE, NANINF, TIMESTAMP) and direct fallen fallback |
| Downstream recovery dispatch | Based on `action_name` received in `SafetyAction`; DT-4I-001 open | Based on `rule_id` extracted from `SafetyEvent.notes` |

### 3.2 Governed Path Detail

```
cross_consistency_observer
  → SafetyEvent (CONDITION_DETECTED + SECONDARY + EFFECTIVE)
    → safety_orchestrator_g1
      → TX-011 evaluated and fired
        → SafetyAction.action_name = stabilization_mode
          → recovery_g1._on_safety_action()
            → _dispatch_recovery(source='orchestrator', notes='')
```

**Known limitation:** `SafetyAction` does not carry the original `rule_id` or causal detail from the `SafetyEvent`. Inside `_dispatch_recovery()`, `source='orchestrator'` and `notes=''` — no explicit branch exists for this combination in the current implementation. This results in the discrepancy tracked as DT-4I-001.

The validated claim for the governed path is limited to:

> `safety_orchestrator_g1` emits `SafetyAction.action_name=stabilization_mode` when TX-011 fires.

Downstream execution of `stabilization_mode` inside `recovery_g1` is not claimed until DT-4I-001 is resolved.

### 3.3 Direct Path Detail

```
watchdog_g1 or cross_consistency_observer
  → SafetyEvent (notes contains rule_id=4F-P2-*)
    → recovery_g1._on_safety_event()
      → _dispatch_recovery(source=..., notes=..., rule_id extracted)
```

The direct path allows cause-based dispatch via `_extract_rule_id(notes)`. This is the basis for the validated STALE, FREEZE, NANINF, and TIMESTAMP recovery policies.

The direct path bypasses orchestrator state-transition governance. It is not equivalent to the governed path and must not be treated as such.

---

## 4. Terminal Manual Causes Policy

### 4.1 Definition

Terminal manual causes are signal-health faults that require immediate operator intervention from the first occurrence and must not be delayed by cooldown or retry logic.

Current set, defined as a constant in `recovery_g1.py`:

```python
TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}
```

### 4.2 Policy Contract

When `rule_id` extracted from `SafetyEvent.notes` is in `TERMINAL_MANUAL_RULE_IDS`:

| Property | Contract |
|---|---|
| Action | `operator_intervention` — immediate |
| Cooldown | Bypassed — not applied |
| Retry counter | Not consumed — `_retry_counters[target]` not modified |
| `_last_attempt_time` | Not modified |
| `attempt` value used | Fixed at `1` — denotes first terminal manual notification, not an auto-retry count |
| Recovery type | `REC-MANUAL` |
| Return behavior | Returns immediately after `operator_intervention`; does not fall through to cooldown/escalation block |

### 4.3 Implementation Path

```python
rule_id = self._extract_rule_id(notes)
if rule_id in TERMINAL_MANUAL_RULE_IDS:
    cause = rule_id.split('-')[-1]
    self.get_logger().warn(
        f'[4H-P2] cause={cause} target={target} terminal=True '
        f'action=operator_intervention (bypass cooldown/retry)'
    )
    result = self._action_request_operator_intervention(target, 1)
    self._publish_recovery_event(result, event_type, source, 'REC-MANUAL')
    return
```

### 4.4 Validation Evidence

| Validation | Evidence |
|---|---|
| FREEZE bypass — two consecutive events <5 s without cooldown | 4H-P2 focal harness |
| STALE post-FREEZE without counter contamination | 4H-P2 focal harness |
| NANINF → operator_intervention | 4H-P1 harness + structural equivalence via `TERMINAL_MANUAL_RULE_IDS` |
| TIMESTAMP → operator_intervention | 4H-P1 harness + structural equivalence via `TERMINAL_MANUAL_RULE_IDS` |

### 4.5 What This Policy Does Not Claim

- Terminal causes do not guarantee physical resolution of the fault — they notify the operator.
- The policy applies only in the direct path. The governed path does not carry `rule_id` and therefore cannot apply terminal bypass via this mechanism.

---

## 5. Cooldown and Retry Policy

### 5.1 Policy Contract — Recoverable Causes

Recoverable causes (STALE, direct fallen fallback) are subject to the following retry/cooldown policy:

| Parameter | Value | Scope |
|---|---|---|
| `RETRY_COOLDOWN_S` | `5.0 s` | Standard cooldown between retry attempts |
| `EXTENDED_COOLDOWN_S` | `15.0 s` | Applied when target is in `RESTARTABLE_CRITICAL_NODES` |
| `MAX_AUTO_RETRIES` | `3` | Maximum automatic retry attempts before escalation |

### 5.2 Behavior

```
attempt = _retry_counters[target]
last_attempt = _last_attempt_time[target]
elapsed = monotonic() - last_attempt

if attempt > 0 and elapsed < cooldown:
    log "Cooldown activo"
    return  ← no action taken

if attempt >= MAX_AUTO_RETRIES:
    escalate → operator_intervention
    return

# execute recovery action
_retry_counters[target] = attempt + 1
_last_attempt_time[target] = monotonic()
```

### 5.3 Counter Reset

Retry counters are reset when compound state returns to `(SAFE, NONE)`:

```python
if msg.risk_level == 'SAFE' and msg.restriction_level == 'NONE':
    self._retry_counters.clear()
    self._last_attempt_time.clear()
```

### 5.4 Terminal Causes Exemption

Terminal manual causes (FREEZE, NANINF, TIMESTAMP) do not interact with this policy. They bypass the cooldown/retry block entirely via the `TERMINAL_MANUAL_RULE_IDS` check that executes before the cooldown evaluation.

### 5.5 What This Policy Does Not Claim

- Cooldown and retry values (`5 s`, `15 s`, `3`) are current implementation parameters, not experimentally calibrated safety limits. They remain pragmatic under DT-4F-001.
- The policy applies only in the direct path. The governed path does not reach the cooldown/retry block for TX-011.

---

## 6. Policy Summary

| Policy | Contract | Status |
|---|---|---|
| TX-009 gate condition | `restriction_level == 'R4-halt'` AND `event_type == 'POLICY_GATE_AUTHORIZED_EMERGENCY_SIT'` | DT-4F-003 closed |
| Single-flight recovery | First accepted event executes to completion; second discarded; no internal priority queue | Documented policy |
| Governed path | Preserves orchestrator governance; loses causal `rule_id` detail; TX-011 under DT-4I-001 | Caveated by DT-4I-001 |
| Direct path | Preserves `rule_id`; bypasses orchestrator; cause-based dispatch | Validated for STALE/FREEZE/NANINF/TIMESTAMP |
| Terminal manual causes | FREEZE/NANINF/TIMESTAMP bypass cooldown/retry; immediate `operator_intervention` | Validated (4H-P2) |
| Cooldown/retry | STALE/fallback: `RETRY_COOLDOWN_S=5s`, `MAX_AUTO_RETRIES=3`; reset on `(SAFE, NONE)` | Pragmatic parameters; DT-4F-001 |

---

## 7. Debt Status After 4I-P3

| Debt | Status after 4I-P3 |
|---|---|
| DT-4F-003 — TX-009 exact gate condition | **Closed by this document** |
| DT-4I-001 — Governed TX-011 recovery execution discrepancy | Open — post-4I fix phase |
| DT-4F-001 — Pragmatic thresholds / cooldown parameters | Open — 4J |
| DT-4F-002 — TX-006b/c explicit named subcase coverage | Open |

---

*G1 Deterministic Safety Runtime — POLICY_CLARIFICATION_G1.md*
*Version 1.0 — Stage 4I-P3 — 2026-06-21*
*Closes: DT-4F-003*
*PM: ChatGPT | Implementor/Auditor: Claude Sonnet 4.6 | Operator: Jorge Padilla*
*Repository: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
