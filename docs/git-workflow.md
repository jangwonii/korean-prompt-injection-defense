# GitHub Workflow With Stepwise Commit History

## Branch Strategy

- `main`: stable releases only.
- `develop`: integration branch for completed phase PRs.
- `feature/*`: implementation branches for phase or issue work.

Planned feature branches:

- `feature/phase-0-repo-foundation`
- `feature/phase-1-baseline-pipeline`
- `feature/phase-2-data-strategy`
- `feature/phase-3-classical-ml`
- `feature/phase-4-transformer`
- `feature/phase-5-evaluation-report`

Existing compatibility branches:

- `feature/phase1-defense-pipeline`
- `feature/ml-training-evaluation`

## Merge Flow

```text
feature/* -> develop -> main
```

- Use PRs for every merge.
- Preserve commit history; avoid squash merges when the research history matters.
- Tag milestone releases from `main`.

## Milestone Tags

- `v0.1-baseline`
- `v0.2-data-ml`
- `v0.3-transformer`
- `v1.0-research-complete`

## Phase Commit Plan

### Phase 0: Repository Foundation

- `chore: initialize repository metadata`
- `chore: add project directory structure`
- `docs: add initial README and AGENTS guidance`
- `chore: add issue and PR templates`

### Phase 1: Baseline Pipeline

- `feat: add input normalization layer`
- `test: cover Korean normalization cases`
- `feat: add rule-based prompt injection detector`
- `test: cover attack and hard-negative rule cases`
- `feat: add risk scoring policy`
- `feat: compose baseline defense pipeline`
- `feat: add FastAPI detect endpoint`

### Phase 2: Data Strategy

- `feat: add dataset schema and loaders`
- `feat: add public dataset ingestion`
- `feat: add Korean expansion dataset builder`
- `feat: add Korean obfuscation generator`
- `test: cover dataset preprocessing edge cases`

### Phase 3: Classical ML

- `feat: add TF-IDF logistic regression training`
- `feat: add linear SVM training`
- `feat: add ML model save and load`
- `feat: add classical ML evaluation reports`
- `docs: summarize classical ML results`

### Phase 4: Transformer

- `feat: add transformer training configuration`
- `feat: add XLM-RoBERTa fine-tuning pipeline`
- `feat: add transformer inference layer`
- `feat: integrate transformer into defense pipeline`
- `docs: summarize transformer experiment results`

### Phase 5: Evaluation And Report

- `feat: add full pipeline evaluation command`
- `feat: add false positive and false negative reports`
- `feat: add Korean obfuscation evaluation report`
- `docs: write final research report`
- `docs: finalize reproducibility instructions`
