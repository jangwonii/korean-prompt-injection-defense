# Korean Transformer 20 Epoch Training Report

## Status

GPU 학습을 완료했다.

- PyTorch: `2.12.0+cu126`
- CUDA available: `true`
- GPU: `NVIDIA GeForce RTX 3060`
- Python environment: `C:\Users\이장원\.venv`

## Dataset

생성 명령:

```powershell
.venv\Scripts\python -m src.data.build_transformer_dataset --output-dir data/processed/transformer_multi_source_korean_20ep --max-korean-safe-per-split 50000
```

사용 데이터:

- `neuralchemy/Prompt-injection-dataset`, `core`
- `deepset/prompt-injections`
- `wambosec/prompt-injections`
- `prismdata/guardrail-ko-11class-dataset`
- `leo-bjpark/AdvBench-Korean`
- `data/samples/prompt_injection_samples.csv`
- `data/samples/local_eval_extension.csv`

생성된 split:

| split | rows | positive | negative |
| --- | ---: | ---: | ---: |
| train | 122275 | 68328 | 53947 |
| validation | 16669 | 7602 | 9067 |
| test | 84304 | 68620 | 15684 |

## Training Config

- Config: `configs/transformer_korean_gpu_20ep.yaml`
- Model: `distilbert-base-multilingual-cased`
- Epochs: `20`
- Max length: `128`
- Train batch size: `32`
- Eval batch size: `64`
- Base model frozen: `false`
- CUDA required: `true`

## GPU Command

```powershell
.venv\Scripts\python -m src.training.train_transformer --config configs/transformer_korean_gpu_20ep.yaml
```

Expected output:

- `models/distilbert-multilingual-prompt-injection-korean-20ep/`
- `reports/transformer_metrics_summary.csv`
- `reports/transformer_confusion_matrix.csv`
- `reports/transformer_false_positives.csv`
- `reports/transformer_false_negatives.csv`
- `reports/transformer_korean_obfuscation_results.csv`
- `reports/transformer_experiment_report.md`

## Test Results

Validation split 기준 결과:

| metric | value |
| --- | ---: |
| Accuracy | 0.9965 |
| Precision | 0.9959 |
| Recall | 0.9964 |
| F1 | 0.9962 |
| FPR | 0.0034 |
| FNR | 0.0036 |

Validation confusion matrix:

| item | count |
| --- | ---: |
| True Negative | 9036 |
| False Positive | 31 |
| False Negative | 27 |
| True Positive | 7575 |

Test split 기준 결과:

| metric | value |
| --- | ---: |
| Accuracy | 0.9992 |
| Precision | 0.9996 |
| Recall | 0.9994 |
| F1 | 0.9995 |
| FPR | 0.0018 |
| FNR | 0.0006 |

Confusion matrix:

| item | count |
| --- | ---: |
| True Negative | 15655 |
| False Positive | 29 |
| False Negative | 40 |
| True Positive | 68580 |

## Error Analysis

Test split 기준 취약 attack type:

| attack_type | samples | false_negative | recall | FNR |
| --- | ---: | ---: | ---: | ---: |
| CONTROL | 5 | 5 | 0.0000 | 1.0000 |
| JAILBREAK | 50 | 11 | 0.7800 | 0.2200 |
| PERSONA_REPLACEMENT | 3 | 1 | 0.6667 | 0.3333 |
| CONTEXT_CONFUSION | 6 | 1 | 0.8333 | 0.1667 |

False positive는 29건이다. 일부 false positive는 데이터셋 라벨상 `BENIGN`이지만 실제 내용은 ransomware, mail fraud, exploit, exam hacking 등 안전성 위험 요청을 포함해 라벨 노이즈 가능성이 있다.

## Notes

- `models/`와 `data/processed/`는 `.gitignore` 대상이므로 checkpoint와 processed CSV는 로컬 산출물이다.
- 데이터셋 규모가 커지고 한국어 `INJECTION` 라벨이 많이 포함되어 test split도 공격 비율이 높다.
- 최종 발표에서는 Recall/FNR 중심 결과와 함께 source별/attack_type별 오류 분석을 같이 제시해야 한다.
