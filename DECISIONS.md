# Design Decisions

## Why ImpactScorer was redesigned from a tolerance-band to a discrete bucket

The first version of this suite gave `ImpactScorer` a tolerance-band pattern:
a continuous 0-100 score where a validator's independently-computed value
was accepted if it fell within ±15 of the leader's. A reviewer rejected this
specific design, for a precise reason: because the downstream approval
threshold sits at exactly 50, two different in-tolerance values for the
*same real contribution* could land on opposite sides of that threshold —
e.g. a leader reporting 49 versus 51, both validated by the same honest
tolerance window, but producing opposite APPROVED/REJECTED outcomes. A
tolerance band is a legitimate pattern in general (it was used successfully
in an earlier accepted suite on this account, for a value with no hard
threshold riding on it), but it is the wrong tool whenever the accepted
value itself crosses a decision boundary downstream. `ImpactScorer` was
rewritten to require strict equality on one of five fixed levels
(`10, 30, 50, 70, 90`) instead — removing the window entirely, so every
accepted score produces one, fully determined downstream outcome.

## Why ImpactScorer now fetches the pull request itself

The same rejection also noted that the impact judgment was derived only
from the caller-written `description` field, never from the actual pull
request. This is the same class of issue as an much earlier rejection on
this account (an LLM judging a claim of fact without the contract fetching
the underlying material itself). `ImpactScorer` now calls
`gl.nondet.web.render(pr_url)` and grounds its judgment in the fetched
content — proven by a dedicated test that pairs a deliberately inflated
description with a genuinely trivial real pull request and confirms the
contract still returns the lowest impact bucket.

## Why no contract holds or transfers real funds

Every earlier submission on this account that involved a `payable` method
went through multiple Action Needed / Rejected cycles before it was correct,
and none of those failure modes (funds locked forever, an untested
value-transfer API on a mobile-constrained testing setup) have anything to do
with reviewing a code contribution. This suite holds no funds, removing that
entire class of risk.

## Why downstream contracts read on-chain state instead of accepting JSON

An earlier submission was rejected specifically because downstream contracts
trusted a JSON string supplied by the caller instead of the upstream
contract's own authenticated output. Every read here goes directly to the
upstream contract's state via `gl.get_contract_at(Address(...)).view().method(...)`.
No contract in this suite ever accepts a JSON blob describing another
contract's result from a caller.

## Why `ContributorReputation` cross-checks the agent across all three upstream reads

A related earlier gap: even after contracts started reading real on-chain
data, an `agent` field was still accepted as a caller-supplied parameter
alongside it, so a legitimate result could in principle be paired with an
unrelated agent. Here, `agent` is captured exactly once — from
`gl.message.sender_address` in `ContributionRegistry.submit_contribution` —
and `finalize_contribution` explicitly asserts that the `agent` field
returned by `CodeQualityAssessor`, `ImpactScorer`, and `ReviewerConsensusBoard`
all match before combining their results.

## Why every non-deterministic contract's validator recomputes fully, never just range-checks

An earlier submission was rejected because a validator checked only that a
leader's status label was one of the allowed values, without independently
recomputing the count and set of fields that produced it. Every validator in
this suite — across both consensus patterns now in use — independently
re-fetches the PR and re-derives the judgment from scratch, and only accepts
the leader's result if its own independent computation matches it exactly.
Nothing is accepted on the strength of a label alone, and nothing is
accepted within a window of disagreement either, after the `ImpactScorer`
rejection above.

## Why the LLM is never asked for open-ended free text as a load-bearing value

`CodeQualityAssessor` only ever asks fixed yes/no questions.
`ReviewerConsensusBoard` only ever asks for one word from a five-item fixed
vocabulary. `ImpactScorer` asks for a number, but constrains the model to
one of five fixed levels and requires exact agreement on it — the same
discipline as the other two contracts, applied to a magnitude judgment.

## Why there is no `initialize_reputation` method

An earlier submission let any caller initialize any agent's starting
reputation, creating a race to claim an agent's identity before its real
owner did. `self.reputation.get(agent, u256(50))` supplies the same default
lazily, removing the race entirely.

## Why every write path guards against double-application

`assess_quality`, `score_impact`, `classify`, and `finalize_contribution`
each check a membership map before doing any consensus or state work, and
only mark that map after a fully successful run — so a `contribution_id` can
be processed by each stage exactly once, and a reverted attempt never
"consumes" the record it was trying to process.

## Why helper logic lives in module-level functions, not undecorated instance methods

GenLayer Studio fails to load a contract's schema if a `gl.Contract` subclass
has any plain instance method without a `@gl.public.write` or
`@gl.public.view` decorator. All private helper logic (`clean_url`,
`is_valid_url`, `ask_yes_no`, `assess_pr`, `estimate_impact`,
`classify_contribution`) is implemented as a module-level function instead of
a method on `self`.

## Why no contract uses `gl.block.timestamp`

This attribute does not exist in the GenLayer SDK version used across every
contract on this account. No time-based logic is used anywhere in this suite.
