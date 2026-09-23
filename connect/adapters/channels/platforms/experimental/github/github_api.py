"""
GitHub webhook utilities — parse issue comment events, post comments.
Uses only stdlib (urllib + json) — no PyGitHub SDK required.
"""
import hashlib
import hmac
import json
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class GitHubConfig:
    github_token: str      # Personal Access Token or GitHub App token
    webhook_secret: str    # HMAC secret set in GitHub webhook settings


@dataclass
class GitHubEvent:
    username: str          # sender.login — used as user_id
    repo_full_name: str    # "owner/repo"
    issue_number: int      # issue or PR number
    body: str              # comment body text
    is_pull_request: bool  # True if the comment is on a PR


def verify_github_signature(secret: str, payload: bytes, signature: str) -> bool:
    """Validate X-Hub-Signature-256 header."""
    if not secret:
        return True   # no secret configured → skip verification
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def parse_issue_comment(payload: dict) -> Optional[GitHubEvent]:
    """Extract a GitHubEvent from an issue_comment webhook payload.
    Returns None if the action is not 'created' or the sender is a bot.
    """
    if payload.get("action") != "created":
        return None
    sender = payload.get("sender", {})
    if sender.get("type") == "Bot":
        return None
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    repo = payload.get("repository", {})
    return GitHubEvent(
        username=sender.get("login", "unknown"),
        repo_full_name=repo.get("full_name", ""),
        issue_number=issue.get("number", 0),
        body=comment.get("body", "").strip(),
        is_pull_request="pull_request" in issue,
    )


def extract_command(body: str) -> Optional[str]:
    """Return the first slash-command line from a comment body, or None."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("/"):
            return line[1:].strip()   # strip the leading slash
    return None


def post_comment(config: GitHubConfig, repo_full_name: str, issue_number: int, body: str) -> None:
    """Post a comment on a GitHub issue or PR via the REST API."""
    url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}/comments"
    data = json.dumps({"body": body}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {config.github_token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "OpenJiuwen-Bot/1.0")
    with urllib.request.urlopen(req, timeout=10):
        pass
