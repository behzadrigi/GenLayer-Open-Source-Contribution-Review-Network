# GenLayer Open-Source Contribution Review Network

A 5-contract GenLayer Intelligent Contract suite that reviews open-source
pull requests through independent on-chain consensus: code quality checks,
impact scoring, and category classification, then updates the contributor's
on-chain reputation. Every downstream contract reads authenticated on-chain
state instead of trusting caller-supplied data.

## Why this exists

Evaluating a code contribution genuinely requires judgment: does it add
tests, is it documented, how significant is its impact, what kind of change
is it. This suite has GenLayer's decentralized validators independently
fetch the actual pull request and reach consensus on each of these
questions, rather than trusting a single reviewer's unverified claim.

This design applies every lesson learned across earlier GenLayer submissions
on this account, including one directly applied to this suite after a
rejection: identity bound to the real transaction sender, no caller-supplied
JSON trusted anywhere in the chain, independent full recomputation in every
non-deterministic contract, no double-application of a result, no fund
custody at all, and — specific to this suite's `ImpactScorer` — every
accepted non-deterministic score is restricted to a small fixed set of
exact values (never a tolerance window), and that score is grounded in the
contract's own fetch of the real pull request content, never the caller's
description alone. See [DECISIONS.md](./DECISIONS.md) for the full
rationale, including the rejection this suite was corrected against.

## Architecture

```
Caller
  │
  ▼
1. ContributionRegistry     deterministic — binds the contribution to
                             gl.message.sender_address, validates repo/PR URLs
  │
  ▼
2. CodeQualityAssessor       non-deterministic, COMPARATIVE consensus — fetches
                             the PR live, independently answers 3 yes/no
                             questions (tests added, documented, follows
                             style); every field must match exactly across
                             validators
  │
  ▼
3. ImpactScorer               non-deterministic, STRICT EQUALITY consensus on a
                             discrete bucket — fetches the PR live and
                             independently estimates impact as exactly one of
                             10 / 30 / 50 / 70 / 90; validators must reach the
                             identical value, so every accepted score produces
                             the same downstream outcome every time
  │
  ▼
4. ReviewerConsensusBoard     non-deterministic, STRICT EQUALITY consensus — a
                             single fixed-vocabulary category (BUGFIX /
                             FEATURE / DOCS / REFACTOR / OTHER) must match
                             exactly across validators
  │
  ▼
5. ContributorReputation      deterministic — reads all three upstream
                             contracts, requires the agent to match across all
                             of them, computes a weighted final score, and
                             applies a reputation change only if it crosses a
                             10-point threshold
```

Each contract is deployed independently and reads its upstream contracts'
state directly (`gl.get_contract_at(Address(...)).view().method(...)`); no
contract accepts a JSON blob describing another contract's result from a
caller.

## Contracts and addresses (GenLayer Studio)

| Contract | Address |
|---|---|
| ContributionRegistry | `0xb7Ca5e4b50302db495b721c6488b785c8b102112` |
| CodeQualityAssessor | `0xBE0Ef8d51a884782CcE53fCbD577A63c3DddAAD7` |
| ImpactScorer | `0x9D2EfcdD7089ba974d65373Ba1084690fcAFe8a2` |
| ReviewerConsensusBoard | `0x0c9792f09f9bED0D5774988F82Fb99D5C6BE6B1c` |
| ContributorReputation | `0x219Fda3D6B3335dBE68a171b5a316C82572C0e88` |

See [CONTRACTS.md](./CONTRACTS.md) for per-contract detail and safety
properties, and [tests/](./tests) for integration tests against the
addresses above. All 27 integration tests passed on GenLayer Studio,
including a dedicated test that deliberately pairs an inflated description
with a genuinely trivial pull request to prove the impact score is grounded
in the real PR content rather than the description.

## Repo structure

```
contracts/
  ContributionRegistry.py
  CodeQualityAssessor.py
  ImpactScorer.py
  ReviewerConsensusBoard.py
  ContributorReputation.py
tests/
  test_contribution_registry.py
  test_code_quality_assessor.py
  test_impact_scorer.py
  test_reviewer_consensus_board.py
  test_contributor_reputation.py
README.md
CONTRACTS.md
DECISIONS.md
LICENSE
```
