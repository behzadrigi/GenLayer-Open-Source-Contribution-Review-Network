# Contracts

## 1. ContributionRegistry

**Pattern:** fully deterministic — no LLM, no consensus needed.

**Purpose:** the entry gate for every contribution. Binds it to the real
transaction sender and validates that both URLs are well-formed.

**Public methods**
- `submit_contribution(repo_url, pr_url, description) -> u256` — stores a
  contribution; returns its `contribution_id`.
- `get_contribution_status/details/data(contribution_id) -> str`
- `list_contributions() -> str`
- `get_agent_contributions(agent) -> str`

**Safety properties**
- `agent` is always `gl.message.sender_address`; never a caller-supplied
  parameter.
- An unparseable `repo_url` or `pr_url` always reverts before any state is
  written. An empty `description` always reverts.

---

## 2. CodeQualityAssessor

**Pattern:** non-deterministic, Equivalence-Principle consensus
(`gl.vm.run_nondet_unsafe`), **comparative, multi-field**.

**Purpose:** fetches the pull request live and independently answers three
fixed yes/no questions (tests added, documented, follows style).

**Public methods**
- `assess_quality(contribution_id) -> bool` — reads the contribution from
  `ContributionRegistry` on-chain; can only be called once per contribution.
- `get_quality_data(contribution_id) -> str` (JSON, includes `agent`)
- `list_assessments() -> str`

**Safety properties**
- `pr_url` and `agent` are read directly from `ContributionRegistry`'s own
  on-chain state, never supplied by the caller of `assess_quality`.
- `assess_quality` cannot be called twice on the same contribution; the
  record is only written after consensus succeeds, so a reverted attempt
  never consumes the contribution.
- Every validator independently re-fetches the PR and re-answers all three
  questions; a validator that computes even one different boolean rejects the
  leader's result outright — nothing is accepted on the leader's label alone.

---

## 3. ImpactScorer

**Pattern:** non-deterministic, Equivalence-Principle consensus,
**strict equality on a discrete bucket**.

**Purpose:** fetches the pull request live and estimates its impact as
exactly one of five fixed levels: 10, 30, 50, 70, 90.

**Public methods**
- `score_impact(contribution_id) -> bool` — reads the contribution on-chain;
  can only be called once per contribution.
- `get_impact_data(contribution_id) -> str` (JSON)
- `list_scores() -> str`

**Safety properties**
- An earlier version of this contract used a continuous 0-100 score with a
  ±15 tolerance band between leader and validator. A reviewer correctly
  rejected that design: because the approval threshold sits at exactly 50,
  two different in-tolerance values for the *same real contribution* could
  land on opposite sides of that threshold, so the same underlying quality
  could validly produce either APPROVED or REJECTED depending on which
  number a leader happened to report. This version removes that ambiguity
  entirely — the score must be the exact same one of five fixed values
  `{10, 30, 50, 70, 90}` across every independent validator, so the
  downstream APPROVED/REJECTED outcome is fully determined by the accepted
  score with no window of disagreement.
- `estimate_impact` fetches the actual pull request content via
  `gl.nondet.web.render(pr_url)` and grounds its judgment in that fetched
  content, not in the caller-written `description` alone. (An earlier
  version used only the description, which the same reviewer also flagged.)
- `score_impact` cannot be called twice on the same contribution.
- `agent` is read from `ContributionRegistry`'s record, never from the
  caller.

---

## 4. ReviewerConsensusBoard

**Pattern:** non-deterministic, Equivalence-Principle consensus,
**strict equality** on a single fixed-vocabulary field.

**Purpose:** classifies the contribution into one of five fixed categories
(`BUGFIX`, `FEATURE`, `DOCS`, `REFACTOR`, `OTHER`).

**Public methods**
- `classify(contribution_id) -> bool`
- `get_classification_data(contribution_id) -> str` (JSON)
- `list_classifications() -> str`

**Safety properties**
- The `category` field must match exactly across independent leader/validator
  runs; a single fixed-vocabulary word is far more likely to be reproducible
  than a free-form or multi-field output.
- `classify` cannot be called twice on the same contribution.
- `agent` is read from `ContributionRegistry`'s record, never from the
  caller.

---

## 5. ContributorReputation

**Pattern:** fully deterministic — combining three already-finalized,
authenticated results into a score and a reputation change is bookkeeping,
not judgment.

**Purpose:** reads all three upstream assessments, computes a weighted final
score, and applies an `INCREASE`/`DECREASE` to the contributor's on-chain
reputation.

**Public methods**
- `finalize_contribution(contribution_id) -> u256` — reads `CodeQualityAssessor`,
  `ImpactScorer`, and `ReviewerConsensusBoard` on-chain; can only be called
  once per contribution.
- `get_reputation(agent) -> str`
- `is_finalized(contribution_id) -> str`
- `get_finalization_details(contribution_id) -> str` (JSON)
- `list_finalizations() -> str`
- `get_agent_finalizations(agent) -> str`

**Safety properties**
- All three upstream records must exist, and their `agent` fields must all
  match each other — nobody can pair a legitimate assessment for one
  contribution with a classification or impact score meant for another.
- `final_score = 0.5 * quality_score + 0.5 * impact_score`, where
  `quality_score` is the fraction of the three quality flags that are `true`,
  scaled to 0-100. `status` is `APPROVED` only if `final_score >= 50`.
- A reputation change is only applied if it crosses a 10-point threshold from
  the agent's current reputation; otherwise it is recorded as `NEUTRAL` and
  reputation is left unchanged (confirmed by the test run, where a
  `final_score` of exactly 50 against a starting reputation of 50 correctly
  produced `NEUTRAL`, not a change).
- `finalize_contribution` cannot be called twice on the same
  `contribution_id`.
- There is no `initialize_reputation` method: `self.reputation.get(agent,
  u256(50))` supplies a lazy default of 50 the first time an agent is
  touched, removing any race to claim an agent's starting reputation.
