"""
Step 5 — Final brief synthesis.
Claude Sonnet: renders the fact sheet + analysis into the structured output brief.
"""
import json
import re
from utils.client import call_model, load_prompt, SONNET


def synthesize(facts: dict, analysis: dict) -> dict:
    system = load_prompt("synthesize")

    user = f"""Produce the final brief from these inputs.

═══ FACT SHEET ═══
{json.dumps(facts, indent=2)}

═══ ANALYSIS ═══
{json.dumps(analysis, indent=2)}

Write the final brief now. Remember: every element must be grounded in specific facts. No generic filler.
"""

    raw = call_model(SONNET, system, user, max_tokens=3000)

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        brief = json.loads(cleaned)
    except json.JSONDecodeError:
        brief = {
            "snapshot": "Brief generation encountered a parsing error.",
            "role_context_summary": raw,
            "company_signals": "",
            "commercial_priorities": [],
            "pain_points": [],
            "conversation_hooks": [],
            "linkedin_dm": "",
            "cold_email": {"subject": "", "body": ""},
            "call_questions": [],
            "things_to_avoid": [],
            "timing_signals": [],
            "seller_relevance": "",
            "confidence_level": "low",
            "confidence_note": "Output parsing failed.",
        }

    return brief
