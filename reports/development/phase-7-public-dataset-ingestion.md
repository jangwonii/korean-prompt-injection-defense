# Phase 7 Public Dataset Ingestion And Holdout Split

## Goal

Add a reproducible public dataset ingestion path and evaluate the classical ML and full defense pipeline on a separate holdout split.

## Branch

- Source branch: `feature/phase-6-data-policy-calibration`
- Target branch: `develop`

## Dataset

Primary public dataset:

- Source: `neuralchemy/Prompt-injection-dataset`
- Config: `core`
- Loaded split: `train`
- Raw normalized output: `data/raw/neuralchemy_core.csv`
- Processed split outputs:
  - `data/processed/public_prompt_injection_train.csv`
  - `data/processed/public_prompt_injection_dev.csv`
  - `data/processed/public_prompt_injection_test.csv`

Split summary:

```text
all:   rows=4391, positive=2650, negative=1741
train: rows=3513, positive=2113, negative=1400
dev:   rows=439,  positive=266,  negative=173
test:  rows=439,  positive=271,  negative=168
```

## Implementation

- Added `src.data.ingest_public`.
- Added Hugging Face ingestion for public prompt-injection datasets.
- Added local `--input-csv` remapping mode so raw data can be reprocessed without network access.
- Added group-aware train/dev/test splitting using `group_id`.
- Added public ML config: `configs/ml_public.yaml`.
- Updated ML training to support explicit `eval_path`.
- Aligned ML training/evaluation with the same normalized text that `DefensePipeline` sends to `MLDetector`.
- Added tests for public row normalization, label parsing, attack type mapping, local CSV remapping, and group-aware split integrity.

## Problems Found

### 1. Language and attack coverage mismatch

The Korean curated sample mostly covers Korean prompt-injection and security-education hard negatives. The public dataset is English-heavy and contains broader jailbreak/harmful-content safety examples.

Impact:

- Classical ML can learn these examples from public data.
- Rule/semantic layers do not fully cover English harmful-content jailbreak patterns.
- Some public labels are not pure prompt-injection labels, so expanding rules too aggressively can increase false positives.

Decision:

- Add only prompt-injection-specific English rules, such as system prompt repetition, training-example extraction, and no-policy role-play.
- Do not turn the prompt-injection guard into a general harmful-content classifier in this phase.

### 2. ML input mismatch

Before this change, standalone ML training/evaluation used raw text, while the full pipeline sent normalized text into `MLDetector`.

Impact:

- ML standalone metrics and full-pipeline metrics were not directly comparable.
- Public holdout recall could appear lower in the full pipeline even when the same model was loaded.

Fix:

- Normalize text in `train_ml`.
- Normalize text in `evaluate_pipeline --mode ml`.
- Keep `DefensePipeline` behavior unchanged.

### 3. Attack type mapping loss

When remapping from an existing raw CSV, the script initially preferred the already-normalized `attack_type` over `original_category`, preserving too many `UNKNOWN_SUSPICIOUS` rows.

Fix:

- `normalize_public_row` now prefers `category`, then `original_category`, then `attack_type`.
- Added explicit mappings for public categories such as `direct_injection`, `crescendo`, `training_extraction`, `system_manipulation`, `encoding`, `payload_injection`, and `rag_poisoning`.

## Results

Classical ML public holdout:

```text
accuracy=0.9567
precision=0.9667
recall=0.9631
f1=0.9649
fpr=0.0536
fnr=0.0369
true_negative=159
false_positive=9
false_negative=10
true_positive=261
```

Full pipeline public holdout after prompt-injection-specific rule additions:

```text
accuracy=0.9613
precision=0.9669
recall=0.9705
f1=0.9687
fpr=0.0536
fnr=0.0295
true_negative=159
false_positive=9
false_negative=8
true_positive=263
```

## Remaining Issues

- Public holdout still has false positives where dataset labels mark potentially harmful or suspicious requests as benign.
- Public holdout still has false negatives for harmful-content jailbreak examples that are not phrased as prompt-injection or hierarchy attacks.
- `UNKNOWN_SUSPICIOUS` remains useful for unclassified public categories but should be reduced further through attack taxonomy review.
- Korean translation and Korean obfuscation holdout are still not implemented.

## Next Steps

- Add attack-type-level metrics.
- Add Korean translation and Korean obfuscation expansion from the public dataset.
- Decide whether harmful-content jailbreak detection is in scope or should remain separate from prompt-injection defense.
- Add threshold sweep report for `configs/ml_public.yaml`.
