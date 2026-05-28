# Experiment Report

## 목적

이 리포트는 한국어 LLM 입력 단계에서 프롬프트 인젝션 위험을 판단하는 다층 방어 파이프라인의 현재 운영 기준을 정리한다. 핵심 비교 축은 단순 이진 분류 모델이 아니라 rule-only, rule+transformer, full calibrated pipeline이다.

## 현재 기준

- Runtime Transformer: `distilbert-base-multilingual-cased`
- Runtime checkpoint: `models/distilbert-multilingual-prompt-injection-korean-20ep`
- Classical ML: TF-IDF char n-gram + Logistic Regression
- ML policy: threshold sweep으로 FNR/Recall 우선 운영점을 찾되, FPR이 높은 checkpoint는 차단 신호가 아니라 WARN/REVIEW 보조 신호로 사용
- Primary blocking signal: Rule-based + Transformer + RiskPolicy

## 대표 성능

| evaluation | accuracy | precision | recall | FPR | FNR |
|---|---:|---:|---:|---:|---:|
| rule-only sample/local | 0.8151 | 0.9623 | 0.7183 | 0.0417 | 0.2817 |
| full sample/local calibrated | 0.9925 | 0.9877 | 1.0000 | 0.0189 | 0.0000 |
| transformer korean 20ep test | 0.9992 | 0.9996 | 0.9994 | 0.0018 | 0.0006 |
| synthetic rule+transformer | 0.9121 | 0.9869 | 0.8972 | 0.0392 | 0.1028 |
| synthetic full with uncalibrated ML | 0.9674 | 0.9593 | 1.0000 | 0.1397 | 0.0000 |

## 보안 관점 해석

Recall과 FNR을 핵심 위험 지표로 본다. 다만 ML checkpoint가 정상 입력까지 과도하게 공격으로 판단하는 경우 FPR이 커질 수 있으므로, ML positive는 단독 차단 근거가 아니라 risk policy의 보조 신호로 제한한다.

현 상태에서 균형 있는 운영 조합은 `rule+transformer`다. Rule 계층은 명확한 공격과 한국어 직접 표현을 빠르게 잡고, Transformer 계층은 문맥형/역할극형/우회형 공격을 보완한다. Full pipeline은 여기에 risk signals, intent analyzer, hierarchy guard, canary guard를 더해 최종 위험도와 대응 정책을 결정한다.

## 잔여 리스크

- `OBFUSCATED_KOREAN_ATTACK`, `DATA_EXFILTRATION`, `ROLE_PLAY_ATTACK`, `TOOL_MISUSE` 유형의 잔여 미탐 샘플을 계속 보강해야 한다.
- Public dataset에는 prompt injection, jailbreak, harmful-content safety 요청이 섞여 있어 taxonomy 정제가 필요하다.
- 대용량 model checkpoint는 일반 Git 커밋 대상이 아니므로 Git LFS 또는 Hugging Face Hub 같은 별도 artifact 관리가 필요하다.

## 다음 작업

- `ml_threshold_sweep.csv`를 기준으로 ML threshold 운영점을 주기적으로 재검토한다.
- hard negative 보안 교육 문장을 늘려 정상 보안 문서 작성 요청의 오탐을 줄인다.
- 최종 발표에서는 “정상/공격 이진 분류 모델”이 아니라 “한국어 LLM 입력 단계 다층 방어 파이프라인”으로 설명한다.
