# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass


def clean_url(url: str):
    if not url:
        return None
    cleaned = url.strip().rstrip('/')
    if cleaned.startswith('http://'):
        cleaned = cleaned.replace('http://', 'https://', 1)
    cleaned = cleaned.replace(' ', '')
    if '?' in cleaned:
        cleaned = cleaned.split('?')[0]
    return cleaned if cleaned else None


def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?://)'
        r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
        r'(/[\w\-./?%&=]*)?$'
    )
    return bool(pattern.match(url.strip()))


@allow_storage
@dataclass
class ContributionRecord:
    contribution_id: u256
    agent: str
    repo_url: str
    pr_url: str
    description: str
    status: str  # PENDING


class ContributionRegistry(gl.Contract):
    contributions: TreeMap[u256, ContributionRecord]
    next_id: u256

    def __init__(self):
        self.next_id = u256(0)

    @gl.public.write
    def submit_contribution(self, repo_url: str, pr_url: str, description: str) -> u256:
        agent = str(gl.message.sender_address)

        assert description.strip() != "", "Description cannot be empty"

        cleaned_repo = clean_url(repo_url)
        assert cleaned_repo is not None, f"Invalid repo URL: {repo_url}"
        assert is_valid_url(cleaned_repo), f"Invalid repo URL: {cleaned_repo}"

        cleaned_pr = clean_url(pr_url)
        assert cleaned_pr is not None, f"Invalid PR URL: {pr_url}"
        assert is_valid_url(cleaned_pr), f"Invalid PR URL: {cleaned_pr}"

        cid = self.next_id
        self.next_id += u256(1)

        self.contributions[cid] = ContributionRecord(
            contribution_id=cid,
            agent=agent,
            repo_url=cleaned_repo,
            pr_url=cleaned_pr,
            description=description,
            status="PENDING",
        )

        return cid

    @gl.public.view
    def get_contribution_status(self, contribution_id: u256) -> str:
        if contribution_id not in self.contributions:
            return "NOT_FOUND"
        return self.contributions[contribution_id].status

    @gl.public.view
    def get_contribution_details(self, contribution_id: u256) -> str:
        if contribution_id not in self.contributions:
            return "NOT_FOUND"
        c = self.contributions[contribution_id]
        return json.dumps({
            "contribution_id": int(c.contribution_id),
            "agent": c.agent,
            "repo_url": c.repo_url,
            "pr_url": c.pr_url,
            "description": c.description,
            "status": c.status,
        })

    @gl.public.view
    def get_contribution_data(self, contribution_id: u256) -> str:
        if contribution_id not in self.contributions:
            return "NOT_FOUND"
        c = self.contributions[contribution_id]
        return json.dumps({
            "contribution_id": int(c.contribution_id),
            "agent": c.agent,
            "repo_url": c.repo_url,
            "pr_url": c.pr_url,
            "description": c.description,
        })

    @gl.public.view
    def list_contributions(self) -> str:
        items = []
        for key in self.contributions:
            c = self.contributions[key]
            items.append(f"{int(c.contribution_id)}:{c.status}")
        return ",".join(items)

    @gl.public.view
    def get_agent_contributions(self, agent: str) -> str:
        items = []
        for key in self.contributions:
            c = self.contributions[key]
            if c.agent == agent:
                items.append(str(int(c.contribution_id)))
        return ",".join(items)
