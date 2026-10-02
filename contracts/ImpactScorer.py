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
