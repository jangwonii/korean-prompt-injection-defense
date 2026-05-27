# Dataset Selection

## 목적

이 문서는 한국어 LLM 프롬프트 인젝션 방어 파이프라인에서 사용할 데이터셋을 확정하고, 공개 데이터셋 후보의 출처, 특성, 사용 범위를 기록한다.

본 프로젝트의 최종 목표는 단순 영어 jailbreak 분류기가 아니라 한국어 입력 단계에서 다음 보안 판단을 수행하는 것이다.

- Direct prompt injection 탐지
- System/developer prompt extraction 탐지
- Instruction hierarchy violation 탐지
- Tool/file/API misuse 탐지
- Korean obfuscation 탐지
- Security education hard negative 오탐 감소

따라서 최종 데이터 구성은 공개 prompt injection 데이터셋을 그대로 쓰는 방식이 아니라, 공개 영어 데이터셋을 기반으로 한국어 번역, 한국어 우회형 증강, 한국어 hard negative를 결합하는 방식으로 간다.

## 현재 확정 데이터셋

현재 개발, 테스트, baseline 평가에 사용하는 확정 데이터셋은 다음 파일이다.

```text
data/samples/prompt_injection_samples.csv
```

이 파일은 외부 공개 데이터셋이 아니라 프로젝트 내부에서 직접 작성한 curated sample dataset이다. 목적은 최종 모델 성능 주장이 아니라 파이프라인 기능 검증, 정책 튜닝, smoke training, 회귀 테스트 고정이다.

현재 workspace 기준:

- Total rows: 101
- Positive: 59
- Negative: 42
- Format: CSV
- Columns: `text`, `label`, `attack_type`
- Label `0`: benign input
- Label `1`: prompt injection or security-risk input

이 수치는 Transformer smoke training과 회귀 테스트의 현재 기준선이다. 최종 연구 성능은 이 샘플 수치가 아니라 공개 데이터셋 수집, 한국어 번역/우회형 증강, group-aware split 이후 별도로 산출한다.

## 최종 데이터셋 구성 방침

최종 연구/평가에는 다음 4개 층을 사용한다.

1. Internal Korean curated sample
2. Public prompt injection classification dataset
3. Human or in-the-wild jailbreak/prompt hacking dataset
4. Korean translation, obfuscation, and hard-negative expansion

권장 저장 구조:

```text
data/raw/        # 원본 공개 데이터셋
data/interim/    # 정제, 번역, 매핑, 증강 중간 산출물
data/processed/  # train/dev/test 최종 분할
data/samples/    # 테스트와 smoke run용 작은 curated sample
```

## 채택 데이터셋

### 1. Internal Korean Curated Sample

- Local path: `data/samples/prompt_injection_samples.csv`
- Source: 직접 작성
- License: repository license follows project policy
- Language: Korean, mixed Korean-English, English
- Current role: unit test, regression test, baseline policy evaluation, smoke training
- Limitation: small curated sample, final benchmark로 사용하지 않음

이 데이터셋은 한국어 프로젝트 특화 케이스를 고정한다. 특히 공개 영어 데이터셋에서 부족한 다음 항목을 보완한다.

- 한국어 보안 교육 hard negative
- 시스템 프롬프트/개발자 메시지 개념 설명
- 한국어 자모 분리 우회
- 과도한 띄어쓰기
- 특수문자 삽입
- 한영 혼합 우회

### 2. NeurAlchemy Prompt Injection & Jailbreak Detection Dataset

- Source: [neuralchemy/Prompt-injection-dataset](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset)
- License: Apache 2.0
- Size: Hugging Face card 기준 22,193 rows
- Schema: `text`, `label`, `category`, `source`, `severity`, `group_id`, `augmented`, `tags`
- Configs:
  - `core`: classical ML용 original samples
  - `full`: transformer fine-tuning용 augmented train set
- Notable characteristics:
  - binary classification용 prompt injection/jailbreak dataset
  - malicious 약 60%, benign 약 40%
  - 29 attack categories
  - hard negative 포함
  - source tracking과 severity label 포함
  - group-aware splitting과 leakage prevention 설명 포함

이 프로젝트의 1차 공개 데이터셋으로 채택한다. 이유는 attack category, severity, source, augmented flag가 있어 현재 `attack_type` 중심 구조로 매핑하기 쉽고, classical ML과 transformer 실험을 분리하기 좋기 때문이다.

사용 계획:

- `core` config: TF-IDF/Logistic Regression, Linear SVM 실험
- `full` config: XLM-RoBERTa 또는 KLUE 계열 transformer 실험
- category를 내부 `attack_type`으로 매핑
- 영어 원문은 `data/raw/`에 보관
- 한국어 번역/우회형은 `data/interim/` 또는 `data/processed/`에 별도 생성

### 3. HackAPrompt Dataset

- Source: [hackaprompt/hackaprompt-dataset](https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset)
- Paper: [Ignore This Title and HackAPrompt](https://arxiv.org/abs/2311.16119)
- License: Hugging Face card 기준 MIT
- Language: English
- Size: Hugging Face card 기준 100K-1M range, paper abstract 기준 600K+ adversarial prompts
- Access: Hugging Face gated access, contact information sharing 조건 동의 필요
- Origin:
  - prompt hacking competition submissions
  - playground data
  - official submission platform data
- Targeted models in competition:
  - GPT-3 `text-davinci-003`
  - FlanT5-XXL
  - ChatGPT `gpt-3.5-turbo`

이 데이터셋은 대규모 human-generated adversarial prompt source로 사용한다. 단, 원본은 competition/game setting에 맞춰져 있어 바로 binary classifier benchmark로 쓰지 않고, 공격 문장 패턴 추출과 adversarial augmentation source로 사용한다.

사용 계획:

- access 승인 후 `data/raw/hackaprompt/`에 원본 저장
- PII/민감 문자열 여부 검사
- 중복 제거
- prompt hacking 유형을 내부 attack taxonomy로 재라벨링
- 한국어 번역과 한국어 obfuscation 변형 생성

### 4. In-The-Wild Jailbreak Prompts

- Source: [AiActivity/All-Prompt-Jailbreak README](https://huggingface.co/datasets/AiActivity/All-Prompt-Jailbreak/blob/main/jailbreak_llms/README.md)
- Related dataset loader: `TrustAIRLab/in-the-wild-jailbreak-prompts`
- Paper: "Do Anything Now": Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models
- License: README badge 기준 MIT
- Size:
  - total prompts: 15,140
  - jailbreak prompts: 1,405
- Collection period: 2022.12-2023.12
- Sources:
  - Reddit
  - Discord
  - websites
  - open-source datasets
- Limitation:
  - online collected data can contain harmful language
  - duplicate removal is recommended by the dataset README

이 데이터셋은 실제 커뮤니티 기반 jailbreak prompt 분포를 보완하기 위해 사용한다. 현재 프로젝트에서는 `JAILBREAK`, `ROLE_PLAY_ATTACK`, `POLICY_BYPASS`, `DIRECT_INJECTION` 계열 확장에 적합하다.

사용 계획:

- `jailbreak_*` split은 공격 샘플 후보로 사용
- `regular_*` split은 일반 prompt 또는 hard negative 후보로 검토
- 중복 제거와 한국어 번역 후 holdout에는 원문 계열 누수 방지 적용

### 5. deepset Prompt Injections

- Source: [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections/tree/main)
- License: Apache 2.0
- Size: Hugging Face card 기준 < 1K, 662 rows로 표시됨
- Format: parquet
- Language: English

작고 널리 참조되는 prompt injection binary dataset이다. 규모가 작아 최종 benchmark에는 부족하지만, 기존 연구/모델과의 호환성 확인 및 smoke baseline에 유용하다.

사용 계획:

- public baseline compatibility check
- loader/schema 변환 테스트
- 내부 curated sample과 함께 빠른 CI 평가용 후보

### 6. wambosec Prompt Injections

- Source: [wambosec/prompt-injections](https://huggingface.co/datasets/wambosec/prompt-injections)
- License: MIT
- Size:
  - total prompts: 5,766
  - benign: 2,340
  - malicious: 3,426
- Schema:
  - `prompt`
  - `label`
  - `is_malicious`
  - `category`
  - `goal`
  - `length_type`
- Generation: LLM-generated prompts across multiple attack techniques and sophistication levels
- Intended use:
  - prompt injection classifier training
  - LLM safety evaluation
  - security research and red-teaming

이 데이터셋은 category와 goal이 있어 risk signal과 attack type 확장에 유용하다. 다만 LLM-generated data이므로 final benchmark보다는 training augmentation과 robustness test에 사용한다.

## 보류 또는 참고 데이터셋

### Tensor Trust

- Source: [Tensor Trust paper](https://arxiv.org/abs/2311.01011)
- Size: paper abstract 기준 126,000+ prompt injection attacks, 46,000+ prompt-based defenses
- Characteristic: online game 기반 prompt extraction/hijacking attack-defense dataset

보류 이유:

- game-specific task framing이 강함
- 현재 프로젝트의 Korean service front-door classification과 직접 구조가 다름

향후 사용 가능성:

- prompt extraction/hijacking 방어 전략 분석
- hierarchy guard 평가용 adversarial case 추출

### Lakera Evaluation Dataset List

- Source: [Lakera evaluation datasets](https://docs.lakera.ai/docs/datasets)
- Listed examples:
  - Salad-Data: 21,318 prompt injection prompts
  - ChatGPT-Jailbreak-Prompts: 79 prompts
  - Vigil jailbreak embeddings: 104 prompts
  - ALERT Adversarial: 45,731 harmful instructions
  - SQuAD 2.0: 142,192 all-negative examples for false-positive evaluation

참고 이유:

- 외부 guardrail 제품의 평가 데이터셋 후보 목록으로 유용함
- SQuAD 같은 all-negative set은 false-positive stress test에 쓸 수 있음

보류 이유:

- 일부는 content moderation/harmful instruction 중심이라 prompt injection hierarchy 판단과 직접 일치하지 않음
- 한국어 특화성이 없음

## 내부 Attack Type 매핑

공개 데이터셋 category는 다음 내부 attack type으로 매핑한다.

| Internal attack_type | Public category examples |
|---|---|
| `DIRECT_INJECTION` | direct_injection, instruction hijacking, ignore previous instructions |
| `SYSTEM_PROMPT_EXTRACTION` | prompt_leaking, system_extraction, prompt extraction |
| `POLICY_BYPASS` | policy bypass, safety bypass, guardrail bypass |
| `JAILBREAK` | jailbreak, DAN, developer mode |
| `ROLE_PLAY_ATTACK` | persona_replacement, evil-twin personas, role-play jailbreak |
| `DATA_EXFILTRATION` | secret extraction, credential/token/API key reveal |
| `TOOL_MISUSE` | tool/action abuse, function call misuse, file/API access |
| `OBFUSCATED_KOREAN_ATTACK` | encoding_obfuscation plus Korean jamo/spacing/special-character variants |
| `MIXED_LANGUAGE_ATTACK` | multilingual/code-switching injection |
| `UNKNOWN_SUSPICIOUS` | suspicious unmatched attack patterns |
| `BENIGN` | benign, hard negatives, normal user requests |

## 한국어 확장 전략

공개 데이터셋 대부분은 영어 중심이다. 한국어 LLM 서비스 방어라는 프로젝트 목표에 맞추기 위해 다음 확장을 필수로 수행한다.

1. 번역
   - 영어 attack/benign prompt를 한국어로 번역
   - 원문과 번역문을 같은 `group_id`로 묶어 split leakage 방지

2. 한국어 우회형 생성
   - 자모 분리
   - 과도한 띄어쓰기
   - 특수문자 삽입
   - 한영 혼합
   - Unicode normalization edge case

3. Korean hard negative 작성
   - 보안 수업
   - 발표 자료
   - 탐지/방어 방법
   - API key 안전 관리
   - 시스템 프롬프트 개념 설명
   - canary/honey token 개념 설명

4. 평가 split 분리
   - train/dev/test split은 group-aware 방식 사용
   - 원문, 번역, 우회 변형이 서로 다른 split에 들어가지 않도록 함
   - final holdout에는 manually reviewed Korean examples 포함

## 최종 채택 결론

현재 확정:

- `data/samples/prompt_injection_samples.csv`
  - curated Korean sample
  - test, regression, smoke run 전용

Phase 7에서 추가할 1차 공개 데이터셋:

- `neuralchemy/Prompt-injection-dataset`
  - primary public train/eval source
  - category, severity, source, leakage-prevention 구조가 현재 프로젝트와 가장 잘 맞음
  - 현재 `core` config의 `train` split을 수집해 group-aware split으로 재분할함
  - local raw: `data/raw/neuralchemy_core.csv`
  - local processed:
    - `data/processed/public_prompt_injection_train.csv`
    - `data/processed/public_prompt_injection_dev.csv`
    - `data/processed/public_prompt_injection_test.csv`
  - split summary:
    - all: 4,391 rows, positive 2,650, negative 1,741
    - train: 3,513 rows, positive 2,113, negative 1,400
    - dev: 439 rows, positive 266, negative 173
    - test: 439 rows, positive 271, negative 168

Phase 7 또는 Phase 8에서 추가할 공격 확장 데이터셋:

- `hackaprompt/hackaprompt-dataset`
  - large-scale human adversarial source
  - gated access 필요
- `TrustAIRLab/in-the-wild-jailbreak-prompts`
  - real-world jailbreak distribution source

보조/호환성 데이터셋:

- `deepset/prompt-injections`
- `wambosec/prompt-injections`

현재 Phase 6의 `1.0` 평가 지표는 curated sample coverage를 의미한다. 최종 연구 성능은 위 공개 데이터셋을 수집, 정제, 한국어 확장, holdout 분리한 뒤 다시 산출해야 한다.
