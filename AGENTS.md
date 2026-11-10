# Project Rules

## Pull requests — never merge

- Open PRs normally and push commits so CI (`.github/workflows/ci.yml`) and
  Greptile review (`greptile.json`) can run.
- Fix CI failures and Greptile review comments by pushing additional commits
  to the PR branch.
- **Never merge a PR.** Do not run `gh pr merge`, do not enable auto-merge,
  and do not merge via the GitHub API. Merging is done manually by the repo
  maintainer.
- Once checks are green, report the PR URL and CI/Greptile status and stop.
