# Contributing to Geshtu

Thank you for considering a contribution. Geshtu is small,
opinionated, and intentionally narrow in scope — the simplicity is
the product. Reading this document end-to-end before opening a PR
will save us both time.

## Ground rules

- **Be kind.** This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
- **Read the spec.** The full design lives in [.spec/geshtu-oss-spec.md](.spec/geshtu-oss-spec.md).
  If a change conflicts with the spec, surface the conflict in the
  issue rather than silently deviating.
- **Read [GOVERNANCE.md](GOVERNANCE.md).** It documents who decides
  what and the merge criteria for core changes.

## Ways to contribute

- **Issues** — bug reports and feature requests. Use the templates in
  the issue tracker.
- **Pull requests** — bug fixes, doc improvements, performance work,
  test coverage. Architectural changes go through an RFC first
  (see GOVERNANCE.md).
- **RFCs** — for anything that affects the MCP tool surface or the
  database schema.
- **Documentation** — typo fixes, clarifications, and translation
  improvements are always welcome.
- **Plugins and extensions** — features outside the four-layer memory
  model belong in separate repositories. We will happily link to
  high-quality ones from the README.

## Before you open a pull request

1. **Open an issue first** for anything non-trivial. A 50-line PR
   that nobody asked for is hard to merge; an issue thread that ends
   in "yes, please open a PR" is easy.
2. **Check the merge criteria** in GOVERNANCE.md. A PR is mergeable
   only if it:
   - Maps to one of the four memory layers (`messages`, `facts`,
     `decisions`, `session_summaries`).
   - Adds no new external runtime dependency without strong
     justification.
   - Includes tests.
   - Includes documentation updates for any user-visible change.
   - Does not break the existing API surface, or includes a migration.
3. **Run the tests locally** and make sure they pass before pushing.

## Development setup

> Until the codebase is bootstrapped (see spec §13 for build order),
> this section is a placeholder. It will be filled in once
> `docker-compose.yml`, `pyproject.toml`, and `package.json` land in
> the repository.

The intended workflow once that is in place:

```bash
git clone https://github.com/crowditory/geshtu.git
cd geshtu
cp .env.example .env       # then fill in the Anthropic key
docker compose up --build
```

See `/docs/dev/` for service-by-service development instructions.

## Coding conventions

- **Python** (api, worker): formatted with `ruff`, type-checked with
  `mypy --strict` on changed files. Tests via `pytest`.
- **Node.js** (mcp): formatted with `prettier`, linted with `eslint`.
  Tests via `vitest`.
- **SQL** migrations: Alembic for the Python side. One migration per
  PR; do not collapse migrations after merge.
- **Commits**: small, focused, with clear subject lines. Follow the
  [Conventional Commits](https://www.conventionalcommits.org)
  convention (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, ...).

## Testing expectations

- Bug fixes: include a regression test that fails before your fix and
  passes after.
- New features: unit tests plus, where applicable, an integration
  test against a real Postgres (no mocks for the database).
- Worker pipeline changes: include at least one end-to-end test that
  exercises extract → embed → dedup.

## Documentation expectations

- Any change to the REST API or MCP tool surface updates `/docs/api/`
  or `/docs/mcp/` in the same PR.
- Any schema change updates `/docs/schema/` and includes a migration.
- README updates are welcome but should not be the only contribution
  in a PR alongside code changes — keep doc-only PRs separate when
  reasonable.

## Pull request review

- A maintainer will review within a week. Pings are fine after that.
- For the first 24 months the BDFL has the final word on architecture
  and merges (see GOVERNANCE.md). Day-to-day fixes and docs may be
  merged by other maintainers once the contributor ladder produces
  them.
- Squash-merge is the default. Use a clear final commit message —
  what the PR does and why.

## Contributor License Agreement (CLA)

Non-trivial contributions require signing a CLA. This is standard for
projects that may offer commercial licensing alongside the AGPL OSS
release (the same pattern used by MongoDB, Elastic, Sentry, and
HashiCorp).

- The CLA is administered through [CLA Assistant](https://cla-assistant.io)
  and signed via GitHub OAuth on your first PR.
- Once signed, it is cached for all your future PRs.
- It is a standard Apache-style CLA: you grant Crowditory Ltd a
  copyright and patent license to your contribution, and you retain
  the right to use your own contribution however you like.
- Trivial PRs — typo fixes, doc tweaks under ~10 lines — are exempt.
  We will not block a one-line typo fix on paperwork.

The CLA exists so that the project can offer commercial license terms
to organizations that cannot use AGPL software, without having to
chase down every past contributor for permission. It does not change
your rights as an OSS user or contributor.

If you cannot sign the CLA for legal reasons (employer policy, etc.),
please reach out before doing significant work — we can usually find
a path that works.

## Reporting issues

- **Bugs** — use the bug report template. Include version, deployment
  topology, reproduction steps, and what you expected vs. what
  happened.
- **Security issues** — do **not** open a public issue. See
  [SECURITY.md](SECURITY.md) for the disclosure process.
- **Feature requests** — use the feature request template. Be
  specific about the use case.

## Communication

- GitHub Issues — bug reports, feature requests, RFCs.
- GitHub Discussions — open-ended questions, "is this the right
  approach?" threads.
- For private matters: **conduct@geshtu.io** for Code of
  Conduct, **security@geshtu.io** for security,
  **trademark@geshtu.io** for brand questions,
  **licensing@geshtu.io** for non-AGPL licensing inquiries.

## Recognition

Contributors are listed in the GitHub contributor graph. Substantive
contributors — those who land multiple non-trivial PRs or carry an
RFC through to acceptance — are credited in release notes.

Thanks again for considering a contribution.
