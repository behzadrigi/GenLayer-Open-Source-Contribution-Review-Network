# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class FinalizationRecord:
    contribution_id: u256
    agent: str
    quality_score: u256
    impact_score: u256
    final_score: u256
    category: str
    change_type: str  # INCREASE, DECREASE, NEUTRAL(never stored, reverts instead)
    status: str  # APPROVED, REJECTED


class ContributorReputation(gl.Contract):
    finalizations: TreeMap[u256, FinalizationRecord]
    finalized: TreeMap[u256, bool]
    reputation: TreeMap[str, u256]
    quality_contract: str
    impact_contract: str
    board_contract: str

    def __init__(self, quality_address: str, impact_address: str, board_address: str):
        self.quality_contract = quality_address
        self.impact_contract = impact_address
        self.board_contract = board_address
        # No initialize_reputation: self.reputation.get(agent, u256(50)) below
        # provides a lazy default of 50 on first encounter with an agent.

    @gl.public.write
    def finalize_contribution(self, contribution_id: u256) -> u256:
        assert contribution_id not in self.finalized, "Contribution already finalized"

        quality_raw = gl.get_contract_at(
            Address(self.quality_contract)
        ).view().get_quality_data(contribution_id)
        assert quality_raw != "NOT_FOUND", "Quality assessment not found"

        impact_raw = gl.get_contract_at(
            Address(self.impact_contract)
        ).view().get_impact_data(contribution_id)
        assert impact_raw != "NOT_FOUND", "Impact score not found"

        board_raw = gl.get_contract_at(
            Address(self.board_contract)
        ).view().get_classification_data(contribution_id)
        assert board_raw != "NOT_FOUND", "Classification not found"

        try:
            quality_data = json.loads(quality_raw)
            impact_data = json.loads(impact_raw)
            board_data = json.loads(board_raw)
        except:
            raise gl.vm.UserError("Invalid data from an upstream contract")

        agent = quality_data.get("agent", "")
        assert agent != "", "Agent not found in quality record"
        assert impact_data.get("agent", "") == agent, "Agent mismatch: impact record"
        assert board_data.get("agent", "") == agent, "Agent mismatch: classification record"

        tests_added = quality_data.get("tests_added", False)
        documented = quality_data.get("documented", False)
        follows_style = quality_data.get("follows_style", False)
        quality_points = sum([tests_added, documented, follows_style])
        quality_score = int((quality_points / 3) * 100)

        impact_score = int(impact_data.get("impact_score", 0))
        category = board_data.get("category", "OTHER")

        final_score = int(0.5 * quality_score + 0.5 * impact_score)
        final_score = min(100, max(0, final_score))
        score_status = "APPROVED" if final_score >= 50 else "REJECTED"

        current_reputation = self.reputation.get(agent, u256(50))
        new_score = u256(final_score)

        if score_status == "APPROVED":
            if new_score > current_reputation + u256(10):
                change_type = "INCREASE"
            elif new_score < current_reputation - u256(10):
                change_type = "DECREASE"
            else:
                change_type = "NEUTRAL"
        else:
            change_type = "NEUTRAL"

        if change_type != "NEUTRAL":
            self.reputation[agent] = new_score

        self.finalized[contribution_id] = True

        fid = contribution_id  # one finalization per contribution, same key space
        self.finalizations[fid] = FinalizationRecord(
            contribution_id=contribution_id,
            agent=agent,
            quality_score=u256(quality_score),
            impact_score=u256(impact_score),
            final_score=u256(final_score),
            category=category,
            change_type=change_type,
            status=score_status,
        )

        return fid

    @gl.public.view
    def get_reputation(self, agent: str) -> str:
        score = self.reputation.get(agent, u256(50))
        return f"REPUTATION:{int(score)}"

    @gl.public.view
    def is_finalized(self, contribution_id: u256) -> str:
        return "FINALIZED" if contribution_id in self.finalized else "NOT_FINALIZED"

    @gl.public.view
    def get_finalization_details(self, contribution_id: u256) -> str:
        if contribution_id not in self.finalizations:
            return "NOT_FOUND"
        f = self.finalizations[contribution_id]
        return json.dumps({
            "contribution_id": int(f.contribution_id),
            "agent": f.agent,
            "quality_score": int(f.quality_score),
            "impact_score": int(f.impact_score),
            "final_score": int(f.final_score),
            "category": f.category,
            "change_type": f.change_type,
            "status": f.status,
        })

    @gl.public.view
    def list_finalizations(self) -> str:
        items = []
        for key in self.finalizations:
            f = self.finalizations[key]
            items.append(f"{int(f.contribution_id)}:{f.status}")
        return ",".join(items)

    @gl.public.view
    def get_agent_finalizations(self, agent: str) -> str:
        items = []
        for key in self.finalizations:
            f = self.finalizations[key]
            if f.agent == agent:
                items.append(str(int(f.contribution_id)))
        return ",".join(items)
