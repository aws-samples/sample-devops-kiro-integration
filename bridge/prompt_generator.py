"""Prompt file generator for the Kiro Bridge poller service.

Converts a parsed MitigationMessage dict into a markdown prompt suitable for
kiro-cli chat --no-interactive mode. The prompt tells kiro-cli exactly what
to change in the codebase based on the DevOps Agent mitigation plan.
"""

from __future__ import annotations

from typing import List

INFRA_KEYWORDS: List[str] = [
    "cloudformation", "template", "stack", "resource",
    "infrastructure", "cdk", "terraform", "sam",
    "instance-type", "instance-id", "db-instance",
    "security-group", "modify-instance", "update-stack",
    "rds", "ec2",
]


def _detect_target(message: dict) -> str:
    """Return 'infrastructure' or 'application' based on plan content."""
    text = ""
    for step in message.get("execution_plan", []):
        for instr in step.get("instructions", []):
            content = instr.get("instruction", {}).get("content", "")
            text += " " + content
    summary = message.get("mitigation_summary", {})
    text += " " + summary.get("action", "")
    text += " " + summary.get("reasoning", "")

    if any(kw in text.lower() for kw in INFRA_KEYWORDS):
        return "infrastructure"
    return "application"


def _build_infra_prompt(message: dict) -> str:
    """Build a prompt for infrastructure changes (CloudFormation updates)."""
    summary = message.get("mitigation_summary", {})
    plan = message.get("execution_plan", [])

    lines = [
        "# Remediation: Update Infrastructure",
        "",
        "The AWS DevOps Agent has identified infrastructure issues and produced a mitigation plan.",
        "Your job is to update the CloudFormation template in this repository to implement the fix.",
        "",
        "## What needs to change",
        "",
        f"**Action**: {summary.get('action', '')}",
        "",
        f"**Why**: {summary.get('reasoning', '')}",
        "",
        "## Specific changes from the mitigation plan",
        "",
    ]

    # Extract the apply steps — these are the actual changes
    for step in plan:
        step_name = step.get("step", "")
        instructions = step.get("instructions", [])
        if not instructions:
            continue

        lines.append(f"### {step_name.replace('_', ' ').title()}")
        for instr in instructions:
            inst = instr.get("instruction", {})
            reasoning = instr.get("reasoning", {})
            number = instr.get("number", "")
            prefix = f"{number}. " if number else "- "
            lines.append(f"{prefix}**{reasoning.get('purpose', '')}**")
            if inst.get("content"):
                lines.append(f"  - Command reference: `{inst['content']}`")
            advisory = reasoning.get("advisory", [])
            if advisory:
                adv_text = ", ".join(advisory) if isinstance(advisory, list) else str(advisory)
                if adv_text:
                    lines.append(f"  - Note: {adv_text}")
            lines.append("")

    lines.extend([
        "## Instructions",
        "",
        "1. Find the CloudFormation template in this repository (likely `infra/app-template.yaml`)",
        "2. Update the template parameters and resource definitions to match the changes above",
        "3. Do NOT run AWS CLI commands — only modify the template file",
        "4. Ensure the changes are backwards-compatible with the existing stack",
        "",
    ])

    return "\n".join(lines)


def _build_app_prompt(message: dict) -> str:
    """Build a prompt for application code changes."""
    summary = message.get("mitigation_summary", {})
    plan = message.get("execution_plan", [])

    lines = [
        "# Remediation: Fix Application Code",
        "",
        "The AWS DevOps Agent has identified application issues and produced a mitigation plan.",
        "Your job is to update the application code in this repository to implement the fix.",
        "",
        f"**Action**: {summary.get('action', '')}",
        "",
        f"**Why**: {summary.get('reasoning', '')}",
        "",
        "## Mitigation steps",
        "",
    ]

    for step in plan:
        instructions = step.get("instructions", [])
        if not instructions:
            continue
        step_name = step.get("step", "")
        lines.append(f"### {step_name.replace('_', ' ').title()}")
        for instr in instructions:
            reasoning = instr.get("reasoning", {})
            lines.append(f"- {reasoning.get('purpose', '')}")
        lines.append("")

    return "\n".join(lines)


def generate_prompt(message: dict) -> str:
    """Build a kiro-cli prompt from a MitigationMessage dict."""
    target = _detect_target(message)
    if target == "infrastructure":
        return _build_infra_prompt(message)
    return _build_app_prompt(message)
