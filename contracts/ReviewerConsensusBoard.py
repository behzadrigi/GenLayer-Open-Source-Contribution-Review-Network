# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass

ALLOWED_CATEGORIES = ("BUGFIX", "FEATURE", "DOCS", "REFACTOR", "OTHER")


def classify_contribution(description: str) -> str:
    prompt = f"""
    Pull request description: {description}

    Classify this contribution into exactly one category.
    Allowed categories: BUGFIX, FEATURE, DOCS, REFACTOR, OTHER

    Respond with ONLY the category word, nothing else. Example: BUGFIX
    """
    response = gl.nondet.exec_prompt(prompt)
    category = str(response).strip().upper()
    for allowed in ALLOWED_CATEGORIES:
        if allowed in category:
            return allowed
    return "OTHER"


@allow_storage
@dataclass
class ClassificationRecord:
    contribution_id: u256
    agent: str
    category: str
    status: str  # CLASSIFIED


class ReviewerConsensusBoard(gl.Contract):
    classifications: TreeMap[u256, ClassificationRecord]
    registry_contract: str

    def __init__(self, registry_address: str):
        self.registry_contract = registry_address

    @gl.public.write
    def classify(self, contribution_id: u256) -> bool:
        assert contribution_id not in self.classifications, "Already classified"

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

        # Equivalence Principle: STRICT EQUALITY on a single fixed-vocabulary
        # field — deliberately the narrowest, most reproducible pattern in
        # this suite.
        def leader_fn():
            return {"category": classify_contribution(description)}

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_category = leader_result.calldata.get("category")
            if leader_category not in ALLOWED_CATEGORIES:
                return False
            my_category = classify_contribution(description)
            return my_category == leader_category

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.classifications[contribution_id] = ClassificationRecord(
            contribution_id=contribution_id,
            agent=agent,
            category=result["category"],
            status="CLASSIFIED",
        )

        return True

    @gl.public.view
    def get_classification_data(self, contribution_id: u256) -> str:
        if contribution_id not in self.classifications:
            return "NOT_FOUND"
        c = self.classifications[contribution_id]
        return json.dumps({
            "contribution_id": int(c.contribution_id),
            "agent": c.agent,
            "category": c.category,
            "status": c.status,
        })

    @gl.public.view
    def list_classifications(self) -> str:
        items = []
        for key in self.classifications:
            c = self.classifications[key]
            items.append(f"{int(c.contribution_id)}:{c.category}")
        return ",".join(items)
