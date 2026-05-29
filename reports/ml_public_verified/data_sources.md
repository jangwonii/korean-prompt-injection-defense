# ML Public Verified Dataset Sources

## Included

- `neuralchemy/Prompt-injection-dataset`: core prompt injection and jailbreak classification data with categories.
- `deepset/prompt-injections`: small binary prompt-injection compatibility dataset.
- `wambosec/prompt-injections`: malicious/benign prompt injection data with attack categories.
- `xTRam1/safe-guard-prompt-injection`: additional binary safe/prompt-injection data, capped by split.
- `reshabhs/SPML_Chatbot_Prompt_Injection`: user-prompt injection examples, capped and stratified.
- `prismdata/guardrail-ko-11class-dataset`: Korean `SAFE` and `INJECTION` rows, capped per label and split.
- `Bingsu/ko_alpaca_data`: Korean benign instruction-following prompts.
- `beomi/KoAlpaca-v1.1a`: Korean benign instruction prompts.
- `DILAB-HYU/KoQuality`: Korean instruction quality dataset used as benign instruction data.
- `databricks/databricks-dolly-15k`: English benign instruction prompts.
- Local curated Korean samples, hard negatives, and capped Korean obfuscation variants.

## Deferred

- `Bordair/bordair-multimodal`: documented as a future robustness candidate because the dataset is large and broader than classical text-only ML retraining.
- `Lakera/gandalf_ignore_instructions`: better suited as a positive stress evaluation set than as balanced ML training data.

## Current Run

- Output splits: `data/processed/ml_public_verified/{train,dev,test}.csv`
- Current split sizes: train 37,176 rows, dev 9,458 rows, test 9,437 rows.
- Model: `models/tfidf_logistic_regression_public_verified.joblib`
- Report directory: `reports/ml_public_verified/`
- Threshold policy: calibrate on dev with Recall/FNR priority under `max_fpr <= 0.035`.
