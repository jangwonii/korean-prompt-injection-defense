# Experiment Report

## 설정
- Model: `tfidf_logistic_regression_public_verified`
- Saved checkpoint: `models\tfidf_logistic_regression_public_verified.joblib`
- Detector: TF-IDF char n-gram + Logistic Regression
- Train dataset: `data/processed/ml_public_verified/train.csv`
- Threshold calibration dataset: `data/processed/ml_public_verified/dev.csv`
- Evaluation dataset: `data/processed/ml_public_verified/test.csv`
- Train rows: 37176
- Calibration rows: 9458
- Eval rows: 9437

## 성능
- Accuracy: 0.9720
- Precision: 0.9588
- Recall: 0.9741
- F1: 0.9664
- FPR: 0.0294
- FNR: 0.0259

## 보안 관점 해석
Recall과 FNR을 핵심 위험 지표로 본다. Threshold는 calibration split에서 선택하고, 최종 성능은 evaluation split 기준으로 해석한다.
ML 계층은 단독 차단 판단자가 아니라 rule/transformer/risk policy를 보조하는 경량 신호로 사용한다. Threshold sweep 결과는 `ml_threshold_sweep.csv`에서 FPR 통제 조건과 Recall 유지 여부를 함께 확인한다.
Attack type별 성능은 `ml_attack_type_metrics.csv`에서 확인한다.

## 한계점
- 공개 데이터셋과 한국어 보강 데이터가 섞여 있으므로 실제 운영 분포를 직접 대표하지 않는다.
- Public dataset에는 prompt injection, jailbreak, harmful-content safety 요청이 섞여 있어 attack taxonomy 정제가 계속 필요하다.
- Hard negative 보안 교육 문장은 별도 오탐 분석 대상으로 유지해야 한다.
- Transformer 문맥 탐지 계층과 한국어 번역/우회형 holdout 평가는 별도로 수행해야 한다.

## 개선 방향
- 한국어 hard negative 추가 보강
- JAILBREAK, TOOL_MISUSE 계열 미탐 사례 보강
- ML positive를 단독 BLOCK이 아닌 WARN/REVIEW 보조 신호로 운영
