# GenLayer Open-Source Contribution Review Network

A 5-contract GenLayer Intelligent Contract suite that reviews open-source pull
requests through independent on-chain consensus: code quality checks, impact
scoring, and category classification, then updates the contributor's on-chain
reputation. Every downstream contract reads authenticated on-chain state
instead of trusting caller-supplied data.

## Why this exists

Evaluating a code contribution genuinely requires judgment: does it add tests,
is it documented, how significant is its impact, what kind of change is it.
This suite has GenLayer's decentralized validators independently fetch the
actual pull request and reach consensus on each of these questions, using
three deliberately different Equivalence Principle patterns, rather than
trusting a single reviewer's unverified claim.

This design applies every lesson learned across four earlier GenLayer
submissions on this account: identity bound to the real transaction sender, no
caller-supplied JSON trusted anywhere in the chain, independent full
recomputation in every non-deterministic contract, no double-application of a
result, and no fund custody at all. See [DECISIONS.md](./DECISIONS.md) for the
full rationale, including why a third consensus pattern (tolerance-band) was
added here on top of the two used in this account's previous suite.

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
3. ImpactScorer               non-deterministic, CUSTOM TOLERANCE-BAND consensus
                             — estimates a 0-100 impact score; a validator's
                             independently-computed score is accepted if it
                             falls within ±15 of the leader's, since a
                             continuous magnitude judgment is not expected to
                             be bit-for-bit reproducible
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
| ContributionRegistry | `0x18D4d1E86eFBB0c6fE009c88fE9798975d13A9D3` |
| CodeQualityAssessor | `0x540401Ed6b31dE2Bdeec897De8ab0f36b4c9ea90` |
| ImpactScorer | `0x0714eAa835AC16911426f337a27DD7797d0904b5` |
| ReviewerConsensusBoard | `0xB2C5cd2Ce93506D6c6D591A368030e187AD63453` |
| ContributorReputation | `0xf0B0397fb85fc9a9A1dA6A018F676A1031879035` |

See [CONTRACTS.md](./CONTRACTS.md) for per-contract detail and safety
properties, and [tests/](./tests) for integration tests against the addresses
above.

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
