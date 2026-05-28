# Contributing

## Branch Rules

- Work starts from `develop`.
- Create one `feature/*` branch per phase or issue.
- Open PRs from `feature/*` into `develop`.
- Open release PRs from `develop` into `main`.
- Do not push directly to `main` or `develop`.

## Commit Rules

Use Conventional Commits:

- `chore: initialize repository metadata`
- `feat: add input normalizer`
- `test: cover Korean normalization cases`
- `docs: update experiment report`

Keep commits small and reviewable. Separate unrelated implementation, documentation, formatting, and experiment-result changes.

## PR Requirements

Every PR should include:

- Scope of changes
- Key commits
- Commands run
- Test results
- Generated reports, if any
- Recall/FNR/FPR impact, if detection behavior changed
- Known limitations
