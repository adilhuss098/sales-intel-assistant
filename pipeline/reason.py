"""
Step 4 — Deep reasoning pass.
Claude Sonnet: given the fact sheet + enriched data, produce grounded commercial intelligence.
This is the highest-value step. The prompt is strict about specificity and bans generic language.
"""
import json
import re
from utils.client import call_model, load_prompt, SONNET


def _build_user_prompt(facts: dict, enriched_text: str, seller_context: str) -> str:
    facts_str = json.dumps(facts, indent=2)

    seller_section = ""
    if seller_context.strip():
        seller_section = f"""
SELLER CONTEXT (what the person using this tool is selling / their company):
{seller_context}

Use this to make the "seller_relevance" field specific — how does what this seller offers map to the specific situation of this prospect?
"""

    return f"""You have the following prospect data. Produce specific, grounded commercial intelligence.

═══ EXTRACTED FACT SHEET ═══
{facts_str}

═══ WEB ENRICHMENT DATA ═══
{enriched_text}
{seller_section}
Remember: cite your basis for every insight. Do not use the banned words. Be specific about this person, not a generic archetype of their role.
"""


def reason(facts: dict, enriched_text: str, seller_context: str) -> dict:
    system = load_prompt("reason")
    user = _build_user_prompt(facts, enriched_text, seller_context)

    raw = call_model(SONNET, system, user, max_tokens=3000)

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        analysis = json.loads(cleaned)
    except json.JSONDecodeError:
        # Return raw text wrapped so the pipeline can continue and show the error
        analysis = {
            "role_context": {"what_they_own": raw, "how_they_are_measured": [],
                             "what_this_quarter_probably_looks_like": "", "what_makes_this_situation_specific": ""},
            "company_context": {"current_phase_narrative": "", "competitive_landscape": "",
                                "organizational_dynamics": "", "likely_internal_pressures": []},
            "commercial_priorities": [],
            "pain_points": [],
            "conversation_hooks": [],
            "seller_relevance": "",
            "things_to_avoid": [],
            "timing_signals": [],
            "what_we_dont_know": ["JSON parsing failed — see raw output above"],
        }

    return analysis
