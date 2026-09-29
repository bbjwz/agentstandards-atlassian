# Implementation and acceptance plan — Agentstandards Atlassian

## Deliverable

An independent companion for council visibility and human decisions on the existing project
board and feature page. No per-persona Jira ticket jungle, no separate board, and no replacement
gate implementation. The Spec Kit Atlassian integration is optional.

## Milestones

1. Pinned core adapter, versioned CouncilSnapshot, full reviewer/pass matrix, safe renderers,
   and offline readiness verification.
2. Shared feature containers, run cards, phase/outcome mapping, human requests, pipeline image,
   and previous-run history on the same page.
3. Authorized Jira approval to versioned manifest/audit draft PR, with stale-input and edit
   detection. Explicit core resume remains a separate action.
4. Package, extension commands, trusted Actions worker, runbook, fixture compatibility, and
   clean installation checks.
5. Live sandbox review and approval round trip before production or community release.

## Acceptance evidence

Test every registered persona/provider/pass, missing artifacts, failures, stale inputs, forged
READY reports, unauthorized approvers, post-approval edits, missing selections, exception coverage,
partial publication, duplicate prevention, cross-owner page preservation, and installation order.

Before release, publish a real awaiting-human run into the same feature page as Spec Kit,
inspect all accordion sections and links, approve it in Jira, review the generated manifest PR,
explicitly resume the council, and verify the final outcome. Also exercise a blocked run and an
explicit exception. Paid council runs require their normal separate user authorization.

## Publication

Run lint, types, tests, builds, and clean Spec Kit installs. Review artifacts for credentials,
private source data, generated/unrelated files. Use a codex/* branch and draft PR. Release tags
and community submission wait for recorded live acceptance.
