# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass

TOLERANCE = 15  # points a validator's independent score may differ from the leader's


def estimate_impact(description: str) -> int:
    prompt = f"""
    Pull request description: {description}

    On a scale of 0 to 100, how significant is this contribution's likely
    impact on the project (bug severity fixed, feature value, or scope of
    improvement)? Consider 0 as trivial/cosmetic and 100 as a major change.

    Respond with ONLY a single integer from 0 to 100, nothing else.
    """
    response = gl.nondet.exec_prompt(prompt)
    digits = "".join(ch for ch in str(response) if ch.isdigit())
    if digits == "":
        return 0
    value = int(digits[:3])
    return max(0, min(100, value))


@allow_storage
@dataclass
class ImpactRecord:
    contribution_id: u256
    agent: str
    impact_score: u256
    status: str  # SCORED


class ImpactScorer(gl.Contract):
    records: TreeMap[u256, ImpactRecord]
    registry_contract: str

    def __init__(self, registry_address: str):
        self.registry_contract = registry_address

    @gl.public.write
    def score_impact(self, contribution_id: u256) -> bool:
        assert contribution_id not in self.records, "Already scored"

        raw = gl.get_contract_at(
            Address(self.registry_contract)
        ).view().get_contribution_data(contribution_id)

        assert raw != "NOT_FOUND", "Contribution not found in registry"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from registry")

        agent = data.get("agent", "")
        description = data.get("description", "")
        assert agent != "", "Agent not found in contribution record"

        # Equivalence Principle: CUSTOM, tolerance-band. A continuous 0-100
        # magnitude judgment is unlikely to be bit-for-bit reproducible across
        # independent LLM calls even in good faith, so the validator
        # independently recomputes its own score and accepts the leader's
        # value only if it falls within a fixed, pre-declared tolerance band
        # rather than requiring exact equality.
        def leader_fn():
            return {"impact_score": estimate_impact(description)}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_score = leader_result.calldata.get("impact_score")
            if not isinstance(leader_score, int) or not (0 <= leader_score <= 100):
                return False

            my_score = estimate_impact(description)
            return abs(my_score - leader_score) <= TOLERANCE

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.records[contribution_id] = ImpactRecord(
            contribution_id=contribution_id,
            agent=agent,
            impact_score=u256(result["impact_score"]),
            status="SCORED",
        )

        return True

    @gl.public.view
    def get_impact_data(self, contribution_id: u256) -> str:
        if contribution_id not in self.records:
            return "NOT_FOUND"
        r = self.records[contribution_id]
        return json.dumps({
            "contribution_id": int(r.contribution_id),
            "agent": r.agent,
            "impact_score": int(r.impact_score),
            "status": r.status,
        })

    @gl.public.view
    def list_scores(self) -> str:
        items = []
        for key in self.records:
            r = self.records[key]
            items.append(f"{int(r.contribution_id)}:{int(r.impact_score)}")
        return ",".join(items)
