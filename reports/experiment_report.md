# Experiment Report

## 설정
- Model: `tfidf_logistic_regression_public`
- Saved checkpoint: `models\tfidf_logistic_regression_public.joblib`
- Detector: TF-IDF char n-gram + Logistic Regression
- Train dataset: `data/processed/public_prompt_injection_train.csv`
- Evaluation dataset: `data/processed/public_prompt_injection_test.csv`
- Train rows: 3513
- Eval rows: 439

## 성능
- Accuracy: 0.9567
- Precision: 0.9667
- Recall: 0.9631
- F1: 0.9649
- FPR: 0.0536
- FNR: 0.0369

## 보안 관점 해석
Recall과 FNR을 핵심 위험 지표로 본다. 공개 데이터셋 holdout을 사용할 때는 `eval_path`를 기준으로 성능을 해석하고, sample dataset 결과는 smoke/regression 확인으로만 사용한다.

## 한계점
- 현재 공개 데이터셋은 영어 중심이므로 한국어 운영 성능을 직접 대표하지 않는다.
- Public dataset에는 prompt injection, jailbreak, harmful-content safety 요청이 섞여 있어 attack taxonomy 정제가 필요하다.
- Transformer 문맥 탐지 계층과 한국어 번역/우회형 holdout 평가는 별도로 수행해야 한다.

## 개선 방향
- 한국어 번역/우회형 데이터 증강
- threshold sweep으로 FNR 우선 운영점 선택
- attack-type별 recall/FNR 리포트 추가
