"""
Step 3 — Structured extraction.
Claude Haiku: parse raw input into a clean fact sheet. No inference.
"""
import json
import re
from utils.client import call_model, load_prompt, HAIKU


def extract_facts(raw_input: str) -> dict:
    system = load_prompt("extract")
    user = f"Extract structured facts from this input:\n\n{raw_input}"

    raw = call_model(HAIKU, system, user, max_tokens=1500)

    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        facts = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: return minimal structure so pipeline can continue
        facts = {
            "person": {"name": None, "title": None, "seniority": None, "function": None,
                       "tenure_months": None, "prior_roles": [], "education": [], "location": None,
                       "notable_achievements": []},
            "company": {"name": None, "website": None, "stage": None, "headcount": None,
                        "headcount_range": None, "sector": None, "icp": None, "business_model": None,
                        "last_funding": None, "recent_news": [], "tech_stack_mentioned": [],
                        "products_mentioned": []},
            "input_quality": "thin",
        }

    return facts
