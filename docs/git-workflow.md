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

## Always-On Working Rule

All implementation work must follow this loop unless a maintainer explicitly documents an exception in the PR:

1. Start from the latest `develop`.
2. Create one focused `feature/*` branch for the phase, issue, or experiment.
3. Commit small, reviewable changes with Conventional Commit messages.
4. Document the development process under `reports/development/`.
5. Run the relevant tests and evaluation commands before opening a PR.
6. Open the PR from `feature/*` into `develop`.
7. Merge `develop` into `main` only through a release PR.

Do not commit directly to `main` or `develop`. Generated artifacts such as `reports/*`, `models/*`, and `data/processed/*` stay out of Git unless a PR explicitly needs a small, reproducible sample.

## Local Work Checklist

Before starting work:

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c feature/<phase-or-issue-name>
```

Before opening a PR:

```powershell
python -m pytest
python -m src.data.preprocess --config configs/baseline.yaml
python -m src.evaluation.evaluate_pipeline --mode full --config configs/baseline.yaml
```

If detection behavior changed, include the before/after recall, FNR, FPR, and any new false positives or false negatives in the PR body.

## Development Process Reports

Every feature PR must include a short process report in `reports/development/`.

Use one Markdown file per feature branch:

```text
reports/development/<feature-name>.md
```

Each document should record:

- Goal and scope
- Branch name and target branch
- Key implementation decisions
- Data or policy changes
- Commands run
- Test and evaluation results
- Known limitations and next steps

Keep this report factual. It should help a reviewer understand why the change exists and how to reproduce the checks.

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

### Phase 6: Data And Policy Calibration

- `data: expand Korean hard-negative and attack samples`
- `feat: calibrate hard-negative policy handling`
- `test: cover education-context false positives`
- `docs: document calibration results`
