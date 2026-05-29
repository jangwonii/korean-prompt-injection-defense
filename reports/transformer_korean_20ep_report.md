# Korean Transformer 20 Epoch Training Report

## 목적

한국어 우회 공격과 공개 prompt injection 데이터를 함께 반영한 Transformer 기반 문맥 탐지 계층을 재학습하고, validation split 기준 성능을 기록했다.

이 결과는 다층 방어 파이프라인에서 Transformer 계층이 rule/ML 계층이 놓칠 수 있는 문맥형, 역할극형, 우회형 공격을 보완할 수 있는지 확인하기 위한 것이다.

## 학습 설정

- Model: `distilbert-base-multilingual-cased`
- Checkpoint path: `models/distilbert-multilingual-prompt-injection-korean-20ep`
- Epochs: 20
- Max length: 128
- Batch size: train 32 / eval 64
- FP16: true
- Base model freeze: false
- CUDA required: true
- Threshold: 0.5

## 데이터 구성

학습 데이터는 다음 출처를 결합한 multi-source Korean 확장 데이터셋이다.

- `neuralchemy/Prompt-injection-dataset`
- `deepset/prompt-injections`
- `wambosec/prompt-injections`
- `prismdata/guardrail-ko-11class-dataset`
- `leo-bjpark/AdvBench-Korean`
- local Korean curated samples

로컬 경로:

- Train: `data/processed/transformer_multi_source_korean_20ep/train.csv`
- Validation: `data/processed/transformer_multi_source_korean_20ep/validation.csv`
- Test: `data/processed/transformer_multi_source_korean_20ep/test.csv`

주의: 위 processed dataset과 model checkpoint는 `.gitignore` 대상이다. 본 PR에는 재현용 config와 결과 리포트만 포함한다. 516MB 규모의 `model.safetensors`는 일반 Git 커밋 대상이 아니며, 필요 시 Git LFS 또는 Hugging Face Hub 같은 별도 모델 저장소로 관리해야 한다.

## Validation 결과

| metric | value |
|---|---:|
| Accuracy | 0.9965 |
| Precision | 0.9959 |
| Recall | 0.9964 |
| F1 | 0.9962 |
| FPR | 0.0034 |
| FNR | 0.0036 |
| True Negative | 9,036 |
| False Positive | 31 |
| False Negative | 27 |
| True Positive | 7,575 |

## Attack Type별 관찰

강점:

- `KOREAN_PROMPT_INJECTION`: Recall 0.9994
- `DIRECT_INJECTION`: Recall 0.9863
- `PROMPT_INJECTION`: Recall 0.9259
- `ENCODING`, `AUTHORITY SPOOFING`, `CONTEXT MANIPULATION`, `RAG_POISONING`, `SYSTEM_EXTRACTION` 등 다수 소분류에서 Recall 1.0

취약하거나 표본이 작은 영역:

- `JAILBREAK`: Recall 0.7292, FNR 0.2708
- `CONTROL`: Recall 0.8000
- `MODEL_FINGERPRINTING`: Recall 0.5000
- `ASCII-ART-BRAILLE`, `BRAILLE-UNICODE`: 표본 1개 기준 미탐

## 오탐/미탐 해석

False negatives는 일부 harmful-content jailbreak 성격의 영어 요청에서 발생했다. 이 프로젝트의 핵심 범위는 prompt injection 방어지만, 공개 데이터셋에는 content safety, harmful instruction, jailbreak가 섞여 있으므로 taxonomy 정제가 필요하다.

False positives는 benign으로 라벨링된 데이터 중 실제로는 공격적 문구나 위험한 역할극 문구가 포함된 사례가 많았다. 이는 데이터 라벨 품질 문제와 모델의 보수적 판단이 함께 작용한 것으로 보인다.

## 발표용 해석

이 결과는 Transformer 계층이 한국어 확장 데이터와 multi-source 공개 데이터를 학습했을 때, 문맥 기반 탐지 성능을 크게 끌어올릴 수 있음을 보여준다. 특히 validation 기준 FNR 0.0036은 보안 관점에서 중요한 성과다.

다만 현업 적용에서는 다음을 그대로 주장하면 안 된다.

- 데이터셋 라벨이 완전히 정제됐다고 볼 수 없다.
- 일부 attack type은 표본 수가 매우 작다.
- model checkpoint는 repo에 포함되지 않아 배포 재현성은 별도 artifact 관리가 필요하다.
- test split 평가와 synthetic hard-negative 평가를 함께 제시해야 한다.

## 개선 방향

1. Test split 평가를 별도 실행하고 validation/test 간 성능 차이를 보고한다.
2. `JAILBREAK`, `MODEL_FINGERPRINTING`, braille/unicode 계열 미탐 샘플을 보강한다.
3. 공개 데이터셋 category를 내부 taxonomy로 정규화한다.
4. hard negative 보안 교육 문장을 늘려 Transformer 오탐을 줄인다.
5. checkpoint는 Git LFS 또는 Hugging Face Hub로 관리하고 README에 다운로드 절차를 추가한다.
6. pipeline config에서 Transformer checkpoint가 없을 때 명확한 warning을 남긴다.
