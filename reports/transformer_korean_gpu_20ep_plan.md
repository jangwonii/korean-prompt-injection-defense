# Korean Transformer 20 Epoch Training Plan

## Status

GPU 학습은 현재 로컬 환경에서 실행되지 않았다.

- PyTorch: `2.11.0+cpu`
- CUDA available: `false`
- `nvidia-smi`: unavailable
- Blocker: `configs/transformer_korean_gpu_20ep.yaml` requires CUDA by design.

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
