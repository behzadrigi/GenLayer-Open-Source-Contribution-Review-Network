# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass


def ask_yes_no(content: str, question: str) -> bool:
    prompt = f"""
    Pull request content (truncated):
    {content[:2500]}

    Question: {question}
    Respond with ONLY: YES or NO
    """
    response = gl.nondet.exec_prompt(prompt)
    return "YES" in response.upper()


def assess_pr(pr_url: str) -> dict:
    try:
        content = gl.nondet.web.render(pr_url)
    except:
        content = ""

    return {
        "tests_added": ask_yes_no(content, "Does this pull request appear to add or update automated tests?"),
        "documented": ask_yes_no(content, "Does this pull request include documentation or comments explaining the change?"),
        "follows_style": ask_yes_no(content, "Does this pull request appear to follow consistent, readable code style?"),
    }


@allow_storage
@dataclass
class QualityRecord:
    contribution_id: u256
    agent: str
    tests_added: bool
    documented: bool
    follows_style: bool
    status: str  # ASSESSED


class CodeQualityAssessor(gl.Contract):
    records: TreeMap[u256, QualityRecord]
    registry_contract: str

    def __init__(self, registry_address: str):
        self.registry_contract = registry_address

    @gl.public.write
    def assess_quality(self, contribution_id: u256) -> bool:
        assert contribution_id not in self.records, "Already assessed"

        raw = gl.get_contract_at(
            Address(self.registry_contract)
        ).view().get_contribution_data(contribution_id)

        assert raw != "NOT_FOUND", "Contribution not found in registry"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from registry")

        agent = data.get("agent", "")
        pr_url = data.get("pr_url", "")
        assert agent != "", "Agent not found in contribution record"

        # Equivalence Principle: COMPARATIVE, multi-field. Both leader and
        # validator independently fetch the PR and answer the same three
        # yes/no questions; every field must match exactly.
        def leader_fn():
            return assess_pr(pr_url)

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_data = leader_result.calldata
            for field in ("tests_added", "documented", "follows_style"):
                if not isinstance(leader_data.get(field), bool):
                    return False

            my_result = assess_pr(pr_url)
            return (
                my_result["tests_added"] == leader_data["tests_added"]
                and my_result["documented"] == leader_data["documented"]
                and my_result["follows_style"] == leader_data["follows_style"]
            )

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.records[contribution_id] = QualityRecord(
            contribution_id=contribution_id,
            agent=agent,
            tests_added=result["tests_added"],
            documented=result["documented"],
            follows_style=result["follows_style"],
            status="ASSESSED",
        )

        return True

    @gl.public.view
    def get_quality_data(self, contribution_id: u256) -> str:
        if contribution_id not in self.records:
            return "NOT_FOUND"
        r = self.records[contribution_id]
        return json.dumps({
            "contribution_id": int(r.contribution_id),
            "agent": r.agent,
            "tests_added": r.tests_added,
            "documented": r.documented,
            "follows_style": r.follows_style,
            "status": r.status,
        })

    @gl.public.view
    def list_assessments(self) -> str:
        items = []
        for key in self.records:
            r = self.records[key]
            items.append(f"{int(r.contribution_id)}:{r.status}")
        return ",".join(items)
