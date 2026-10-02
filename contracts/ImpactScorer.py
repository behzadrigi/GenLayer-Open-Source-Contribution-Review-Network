# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass

IMPACT_BUCKETS = (10, 30, 50, 70, 90)


def parse_bucket(text: str) -> int:
    found = re.findall(r"\b(10|30|50|70|90)\b", str(text))
    if found:
        return int(found[0])
    return 10


def estimate_impact(description: str, pr_url: str) -> int:
    try:
        content = gl.nondet.web.render(pr_url)
    except:
        content = ""

    prompt = f"""
    Pull request description: {description}

    Actual pull request content (truncated):
    {content[:2500] if content else "(could not be fetched)"}

    Based on the actual PR content above, how significant is this
    contribution's likely impact on the project?
    Choose exactly one level: 10, 30, 50, 70, or 90
    (10 = trivial/cosmetic, 90 = major change)

    Respond with ONLY one number: 10, 30, 50, 70, or 90.
    """
    response = gl.nondet.exec_prompt(prompt)
    return parse_bucket(response)


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
        pr_url = data.get("pr_url", "")
        assert agent != "", "Agent not found in contribution record"

        # Equivalence Principle: STRICT EQUALITY on a discrete impact bucket.
        # The previous tolerance-band design let the same real contribution
        # validly cross the 50-point approval threshold in either direction,
        # depending on which in-tolerance value a leader happened to report.
        # A small fixed set of levels, matched exactly, removes that
        # ambiguity entirely: every accepted score is the same value every
        # independent validator arrived at, so the downstream
        # APPROVED/REJECTED outcome is fully determined by it. The judgment
        # is also now grounded in the actual fetched PR content, not just
        # the caller-written description.
        def leader_fn():
            return {"impact_score": estimate_impact(description, pr_url)}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_score = leader_result.calldata.get("impact_score")
            if leader_score not in IMPACT_BUCKETS:
                return False
            return estimate_impact(description, pr_url) == leader_score

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
