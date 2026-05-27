# Transformer Experiment Report

## 설정
- Model: `distilbert-base-multilingual-cased`
- Saved checkpoint: `models\distilbert-multilingual-prompt-injection-public-core`
- Detector: Transformer sequence classification
- Dataset source: `Hugging Face neuralchemy/Prompt-injection-dataset core split + local Korean curated samples`
- Public dataset URL: `https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset`
- Public split rows: train 4,391 / validation 941 / test 942
- Local curated rows added to train: 119
- Train dataset: `data/processed/transformer_public_core/train.csv`
- Validation dataset: `data/processed/transformer_public_core/validation.csv`
- Test dataset: `data/processed/transformer_public_core/test.csv`
- Report split: `test`
- Train rows: 4510
- Validation rows: 941
- Test rows: 942
- Max length: 128
- Epochs: 1
- Batch size: 16
- Freeze base model: True

## 성능
- Accuracy: 0.9501
- Precision: 0.9583
- Recall: 0.9565
- F1: 0.9574
- FPR: 0.0590
- FNR: 0.0435

## 보안 관점 해석
Transformer 계층은 rule/ML이 놓칠 수 있는 문맥 기반 우회 표현을 보완하기 위한 정밀 탐지 계층이다. 운영 기준은 Accuracy보다 Recall과 FNR을 우선한다.

## 한계점
- 샘플 데이터만으로 학습하면 일반화 성능을 주장할 수 없다.
- 공개 데이터셋과 한국어 확장 데이터로 재학습해야 최종 연구 결과로 사용할 수 있다.

## 개선 방향
- XLM-RoBERTa와 KLUE-BERT 비교
- threshold sweep 기반 FNR 우선 운영점 선택
- hard negative와 한국어 우회형 test split 별도 평가
