# Transformer Experiment Report

## 설정
- Model: `distilbert-base-multilingual-cased`
- Saved checkpoint: `models\distilbert-multilingual-prompt-injection-korean-20ep`
- Detector: Transformer sequence classification
- Dataset source: `Hugging Face neuralchemy/Prompt-injection-dataset core + deepset/prompt-injections + wambosec/prompt-injections + prismdata/guardrail-ko-11class-dataset + leo-bjpark/AdvBench-Korean + local Korean curated samples`
- Train dataset: `data/processed/transformer_multi_source_korean_20ep/train.csv`
- Validation dataset: `data/processed/transformer_multi_source_korean_20ep/validation.csv`
- Test dataset: `data/processed/transformer_multi_source_korean_20ep/test.csv`
- Report split: `test`
- Train rows: 122275
- Validation rows: 16669
- Test rows: 84304
- Max length: 128
- Epochs: 20
- Batch size: 32
- Gradient accumulation steps: 1
- FP16: True
- Freeze base model: False
- GPU: `NVIDIA GeForce RTX 3060`
- PyTorch: `2.12.0+cu126`

## 성능
- Accuracy: 0.9992
- Precision: 0.9996
- Recall: 0.9994
- F1: 0.9995
- FPR: 0.0018
- FNR: 0.0006

## Confusion Matrix

- True Negative: 15655
- False Positive: 29
- False Negative: 40
- True Positive: 68580

## 보안 관점 해석
Transformer 계층은 rule/ML이 놓칠 수 있는 문맥 기반 우회 표현을 보완하기 위한 정밀 탐지 계층이다. 운영 기준은 Accuracy보다 Recall과 FNR을 우선한다.

## 한계점
- 여러 공개 데이터셋과 로컬 샘플을 결합했으므로 source별 라벨 정의가 완전히 동일하지 않을 수 있다.
- test split은 한국어 `INJECTION` 라벨 비중이 높아 실제 운영 분포를 그대로 대표하지 않는다.
- 최종 연구 결과에는 source별/attack_type별 오류 분석과 threshold sweep을 함께 제시해야 한다.

## 개선 방향
- XLM-RoBERTa와 KLUE-BERT 비교
- threshold sweep 기반 FNR 우선 운영점 선택
- hard negative와 한국어 우회형 test split 별도 평가
