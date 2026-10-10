@AGENTS.md

## Claude Code notes

- The import above loads `AGENTS.md`; it is the source of truth. Put shared instructions there, not here.
- Path-scoped rules in `.claude/rules/` load when you read or edit files in a directory. Follow the rule for the
  directory you are working in, and stop if it says the directory is not yours.
- Project skills: `/verify` (pre-commit check), `/eval-report`, `/tune-thresholds`, `/add-rule`, `/add-anomaly`,
  `/demo-check`. `/contract-change` and `/integrate` are manual-only: run them only when a human types them.
- Commit and PR attribution is disabled in `.claude/settings.json` (`attribution`). The commit-msg hook rejects
  AI trailers anyway, so never add them and never use `--no-verify`.
- Teammates are on Windows and macOS/Linux. Prefer `python -m ...` commands, which work in Bash and PowerShell alike.
  If `make` is missing, run the plain command from the table in `AGENTS.md`.
- Personal permissions belong in `.claude/settings.local.json` (gitignored), not in the shared settings.
