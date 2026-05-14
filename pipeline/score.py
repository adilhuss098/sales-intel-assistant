"""
Step 6 — Confidence scoring and slop filter.
Claude Haiku: reviews the brief for generic content and scores specificity.
"""
import json
import re
from utils.client import call_model, load_prompt, HAIKU

BANNED_WORDS = [
    "leverage", "synergy", "synergise", "innovative", "cutting-edge",
    "dynamic", "robust", "comprehensive", "holistic", "best-in-class",
    "world-class", "game-changing", "disruptive", "paradigm", "journey",
    "empower", "drive growth", "deliver value", "streamline",
]


def _count_banned_words(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for word in BANNED_WORDS:
        if word in text_lower:
            found.append(word)
    return found


def score_brief(brief: dict) -> dict:
    """
    Returns:
      - slop_report: per-section quality analysis
      - overall_specificity_score: float 1-5
      - banned_words_found: list of flagged words
      - passed: bool
    """
    sections_to_check = {
        "snapshot": brief.get("snapshot", ""),
        "role_context_summary": brief.get("role_context_summary", ""),
        "company_signals": brief.get("company_signals", ""),
        "priorities": " ".join(p.get("priority", "") for p in brief.get("commercial_priorities", [])),
        "pain_points": " ".join(p.get("pain", "") for p in brief.get("pain_points", [])),
        "hooks": " ".join(h.get("hook", "") for h in brief.get("conversation_hooks", [])),
        "linkedin_dm": brief.get("linkedin_dm", ""),
        "cold_email": brief.get("cold_email", {}).get("body", ""),
    }

    # Quick banned-word scan across all content
    all_text = " ".join(sections_to_check.values())
    banned_found = _count_banned_words(all_text)

    sections_text = "\n\n".join(
        f"[{k}]\n{v}" for k, v in sections_to_check.items() if v.strip()
    )

    system = load_prompt("slop_filter")
    user = f"Review this sales intelligence brief for generic content:\n\n{sections_text}"

    raw = call_model(HAIKU, system, user, max_tokens=2000)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        slop_report = json.loads(cleaned)
    except json.JSONDecodeError:
        slop_report = []

    scores = [s.get("specificity_score", 3) for s in slop_report if isinstance(s, dict)]
    overall_score = round(sum(scores) / len(scores), 1) if scores else 3.0

    return {
        "slop_report": slop_report,
        "overall_specificity_score": overall_score,
        "banned_words_found": banned_found,
        "passed": overall_score >= 3.0 and len(banned_found) == 0,
    }
