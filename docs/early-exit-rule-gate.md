# Rule Gate Early-Exit Plan

## Goal

Show that a layered prompt-injection defense can reduce average request latency when it is implemented as a cascade.

The claim is not that every additional layer makes the system faster. A sequential pipeline that always runs every detector will usually add latency. The intended claim is narrower:

> A lightweight rule gate can early-exit clear benign and clear malicious requests, so only uncertain requests are escalated to heavier ML or Transformer detectors.

## Related Guardrail Patterns

Several guardrail systems use comparable staged designs.

- NVIDIA NeMo Guardrails separates input, dialog, retrieval, execution, and output rails. It also documents ways to reduce LLM calls in the rail flow.
- Langflow guardrails describe heuristic detection first, with LLM validation used as fallback for prompt injection and jailbreak checks.
- OpenRouter prompt injection guardrails support regex-based detection for incoming messages.
- Lakera Guard describes a combination of machine-learning, language-model, and rule-based filters.
- Guardrails AI composes validators into input and output guards.
- Meta Prompt Guard uses a small classifier to identify benign, injection, and jailbreak inputs before relying on heavier application logic.

References:

- https://docs.nvidia.com/nemo/guardrails/0.15.0/user-guides/guardrails-process.html
- https://docs.langflow.org/guardrails
- https://openrouter.ai/docs/guides/features/guardrails/prompt-injection
- https://docs.lakera.ai/docs/defenses
- https://guardrailsai.com/docs/concepts/validators/
- https://huggingface.co/meta-llama/Prompt-Guard-86M

## Target Architecture

```text
User Input
  -> Normalize
  -> Rule / Signal / Semantic Gate
      -> clear benign: ALLOW early-exit
      -> clear attack: BLOCK early-exit
      -> uncertain: escalate
  -> ML / Transformer Detector
  -> Final Risk Policy
```

The rule gate runs only cheap local checks:

- normalization
- rule-based pattern detection
- risk signals
- intent analyzer
- hierarchy guard
- canary guard

The expensive detectors are skipped when the cheap layers already produce a high-confidence decision.

## Early-Exit Policy

### BLOCK Early-Exit

Use aggressive early-exit for high-confidence attacks. A request can exit before ML/Transformer when:

- pre-model risk level is `CRITICAL`
- recommended action is `BLOCK`
- decision is backed by `rule_based`, `hierarchy_guard`, or `canary_guard`

Typical examples:

- system prompt extraction
- developer message or internal rule disclosure
- credential, token, or API key disclosure
- hidden marker or canary probing

### ALLOW Early-Exit

Use conservative early-exit for benign requests. A request can exit before ML/Transformer when:

- pre-model risk level is `LOW`
- recommended action is `ALLOW`
- no rule matched
- no hierarchy or canary violation exists
- no meaningful obfuscation or instruction-override signal exists
- mixed-language risk is low
- sensitive target risk is absent, except safe security-education context

Typical examples:

- ordinary summarization, translation, classification, and document drafting
- safe security education or defensive policy explanation

ALLOW early-exit is intentionally stricter than BLOCK early-exit because a false allow is a security miss.

## Experiment Design

Run the same dataset through two modes:

1. Full sequential mode: always run ML/Transformer when configured.
2. Early-exit mode: skip ML/Transformer for clear benign and clear attack requests.

Measure:

- average latency
- p50, p95, p99 latency
- Transformer call rate
- ML call rate
- early-exit rate
- early-exit rate by action: `ALLOW`, `BLOCK`, `ESCALATE`
- FPR, FNR, precision, recall
- hard-negative FPR
- obfuscated Korean recall

Expected outcome:

- average latency should decrease when many requests are clear benign or clear attacks
- Transformer call rate should decrease
- p95 and p99 may decrease less because uncertain requests still escalate
- FNR must not increase beyond the project threshold

## Acceptance Criteria

Suggested initial thresholds for a latency-focused regression experiment:

- Transformer call rate reduced by at least 30 percent on mixed traffic
- average latency reduced compared with full sequential mode
- `SYSTEM_PROMPT_EXTRACTION` recall remains 1.0
- `DATA_EXFILTRATION` recall remains at or above the current baseline
- hard-negative FPR does not increase
- overall FNR does not increase by more than 0.01 absolute

## Implementation Notes

The current implementation adds early-exit inside `DefensePipeline` before ML and Transformer detectors are invoked.

Config lives under `early_exit` in `configs/runtime/baseline.yaml`, and is inherited by runtime ML/Transformer configs through the existing risk-policy config merge.

The API response schema is unchanged. Early-exit decisions add evidence such as:

```text
early_exit: allow_clear_benign
early_exit: block_clear_attack
```

For attack early-exits, `early_exit_rule_gate` is also added to `detected_by`.
