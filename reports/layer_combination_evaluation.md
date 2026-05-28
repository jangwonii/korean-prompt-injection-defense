# Layer Combination Evaluation

## 목적

기존 평가가 실제로 Rule-based, Classical ML, Transformer 3계층만을 사용한 평가인지 확인하고, detector 계층을 2개씩 조합했을 때 어떤 조합이 가장 적절한지 비교했다.

## 평가 기준

- 평가 데이터: `data/processed/synthetic_500_eval.csv`
- 샘플 수: 1,751
- 결합 방식: 보안 Recall 우선 기준으로 두 계층 중 하나라도 공격으로 판단하면 최종 공격으로 판단하는 OR policy
- Rule 입력: normalized text
- ML 입력: normalized text
- Transformer 입력: normalized text
- ML checkpoint: `models/tfidf_logistic_regression.joblib`
- Transformer checkpoint: `models/distilbert-multilingual-prompt-injection-korean-20ep`

## 기존 테스트 해석

기존 `evaluate_pipeline --mode full --config configs/synthetic_500_ml_eval.yaml` 평가는 정확히 Rule + ML + Transformer 3계층만의 평가는 아니다.

현재 `DefensePipeline`의 full mode는 다음 계층을 함께 실행한다.

- Normalizer
- Rule-based detector
- Risk signals
- Intent analyzer
- Hierarchy guard
- Canary guard
- ML detector, config에 `model.output_path`가 있고 checkpoint가 존재할 때만 사용
- Transformer detector, config에 `model.output_dir`가 있고 checkpoint가 존재할 때만 사용
- Risk policy

따라서 기존 synthetic full 평가는 다층 방어 파이프라인 평가이며, strict한 3 detector layer 조합 평가는 별도로 분리해서 봐야 한다.

## 계층별 및 조합별 결과

| combination | accuracy | precision | recall | f1 | FPR | FNR | TN | FP | FN | TP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rule_only | 0.6334 | 0.9782 | 0.5339 | 0.6908 | 0.0392 | 0.4661 | 392 | 16 | 626 | 717 |
| ml_only | 0.7784 | 0.7759 | 1.0000 | 0.8738 | 0.9510 | 0.0000 | 20 | 388 | 0 | 1343 |
| transformer_only | 0.9006 | 1.0000 | 0.8704 | 0.9307 | 0.0000 | 0.1296 | 408 | 0 | 174 | 1169 |
| rule+ml | 0.7784 | 0.7759 | 1.0000 | 0.8738 | 0.9510 | 0.0000 | 20 | 388 | 0 | 1343 |
| rule+transformer | 0.9121 | 0.9869 | 0.8972 | 0.9399 | 0.0392 | 0.1028 | 392 | 16 | 138 | 1205 |
| ml+transformer | 0.7784 | 0.7759 | 1.0000 | 0.8738 | 0.9510 | 0.0000 | 20 | 388 | 0 | 1343 |
| rule+ml+transformer | 0.7784 | 0.7759 | 1.0000 | 0.8738 | 0.9510 | 0.0000 | 20 | 388 | 0 | 1343 |

## 2계층 조합 결론

FNR만 최우선으로 보면 `rule+ml`과 `ml+transformer`가 모두 FN 0건, Recall 1.0000, FNR 0.0000이다. 하지만 현재 ML checkpoint는 synthetic 평가셋에서 정상 408건 중 388건을 공격으로 분류하여 FPR 0.9510을 보인다. 이 조합은 차단 정책으로 쓰기 어렵고, 최대한 보수적인 WARN/REVIEW 보조 신호로만 쓰는 것이 적절하다.

실사용 균형 기준의 최적 2계층 조합은 `rule+transformer`다.

- FPR: 0.0392
- FNR: 0.1028
- Precision: 0.9869
- F1: 0.9399
- Transformer 단독 대비 FN 174건에서 138건으로 감소
- Rule 단독 대비 Recall 0.5339에서 0.8972로 증가

## `rule+transformer` 잔여 미탐 유형

| attack_type | positive_samples | false_negative | FNR |
| --- | ---: | ---: | ---: |
| DATA_EXFILTRATION | 93 | 18 | 0.1935 |
| MIXED_LANGUAGE_ATTACK | 248 | 2 | 0.0081 |
| OBFUSCATED_KOREAN_ATTACK | 542 | 84 | 0.1550 |
| ROLE_PLAY_ATTACK | 93 | 18 | 0.1935 |
| TOOL_MISUSE | 93 | 16 | 0.1720 |

## 권장 운영 조합

현재 상태에서는 다음 구성이 가장 현실적이다.

1. `rule+transformer`를 차단 또는 고위험 판단의 핵심 조합으로 사용한다.
2. ML은 현 checkpoint 기준 FPR이 너무 높으므로 즉시 차단 신호로 쓰지 않고 WARN/REVIEW 보조 신호로 둔다.
3. 다음 작업은 ML threshold calibration 또는 ML 재학습이다. 목표는 Recall을 유지하면서 FPR을 낮추는 것이다.
4. `OBFUSCATED_KOREAN_ATTACK`, `DATA_EXFILTRATION`, `ROLE_PLAY_ATTACK`, `TOOL_MISUSE` 미탐 샘플을 hard positive로 보강해 Transformer 재학습 데이터에 추가한다.

## 반영된 정책 변경

- `configs/runtime/transformer.yaml`은 실제 학습 완료 checkpoint인 `models/distilbert-multilingual-prompt-injection-korean-20ep`를 기본값으로 사용한다.
- `configs/runtime/ml.yaml`은 threshold sweep을 활성화해 ML 운영점을 리포트로 남긴다.
- Risk policy는 config의 `ml_policy.positive_max_score_when_alone` 값을 통해 ML 단독 positive가 과도한 차단 점수로 승격되지 않게 제한할 수 있다.
- Hard-case local evaluation set에는 한국어 난독화, 데이터 유출, 역할극, 도구 악용 positive와 보안 교육 hard negative를 추가한다.
