# Contributing

## Branch Rules

- Work starts from `develop`.
- Create one `feature/*` branch per phase or issue.
- Open PRs from `feature/*` into `develop`.
- Open release PRs from `develop` into `main`.
- Do not push directly to `main` or `develop`.

This rule is permanent for normal development. If a hotfix or experiment needs a different path, record the exception and reason in the PR description.

Recommended start:

```powershell
git switch develop
git pull --ff-only origin develop
git switch -c feature/<phase-or-issue-name>
```

## Commit Rules

Use Conventional Commits:

- `chore: initialize repository metadata`
- `feat: add input normalizer`
- `test: cover Korean normalization cases`
- `docs: update experiment report`

Keep commits small and reviewable. Separate unrelated implementation, documentation, formatting, and experiment-result changes.

## Development Documentation

Every feature PR must add or update a process report in `reports/development/`.

The report should include:

- Goal and scope
- Branch name and target branch
- Key implementation decisions
- Data or policy changes
- Commands run
- Test and evaluation results
- Known limitations and next steps

## PR Requirements

Every PR should include:

- Scope of changes
- Key commits
- Commands run
- Test results
- Generated reports, if any
- Recall/FNR/FPR impact, if detection behavior changed
- Link to the related `reports/development/` process report
- Known limitations

See [docs/git-workflow.md](docs/git-workflow.md) for the full branch, commit, and PR workflow.
