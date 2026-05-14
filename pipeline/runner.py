"""
Pipeline orchestrator — runs all 6 steps in sequence and yields status updates.
Designed to be called from Streamlit with a generator pattern for live progress.
"""
from typing import Generator
from pipeline.parse import parse_inputs, ParsedInput
from pipeline.enrich import enrich, format_enriched_for_prompt
from pipeline.extract import extract_facts
from pipeline.reason import reason
from pipeline.synthesize import synthesize
from pipeline.score import score_brief
from storage.db import save_brief, init_db


def run_pipeline(
    linkedin: str,
    company: str,
    context: str,
    seller_context: str,
) -> Generator[dict, None, None]:
    """
    Yields step-update dicts: {"step": int, "label": str, "status": "running"|"done"|"error", "data": any}
    Final yield has step=7 and includes the complete result.
    """
    init_db()

    # ── Step 1: Parse ──────────────────────────────────────────────────────
    yield {"step": 1, "label": "Parsing inputs", "status": "running", "data": None}
    parsed: ParsedInput = parse_inputs(linkedin, company, context, seller_context)
    if not parsed.is_viable:
        yield {"step": 1, "label": "Parsing inputs", "status": "error",
               "data": {"warnings": parsed.warnings}}
        return
    yield {"step": 1, "label": "Parsing inputs", "status": "done", "data": parsed.warnings}

    # ── Step 2: Enrich ─────────────────────────────────────────────────────
    yield {"step": 2, "label": "Enriching from web", "status": "running", "data": None}
    # Do a quick name/company extract first to guide search
    # (lightweight — just grab first line heuristics)
    name_guess = _guess_name(parsed.linkedin_text)
    company_guess = _guess_company(parsed.company_text + " " + parsed.linkedin_text)

    enriched = enrich(name_guess, company_guess, parsed.company_url)
    enriched_text = format_enriched_for_prompt(enriched)
    yield {"step": 2, "label": "Enriching from web", "status": "done",
           "data": {"news_count": len(enriched.get("news", [])),
                    "jobs_count": len(enriched.get("job_postings", [])),
                    "website_scraped": bool(enriched.get("company_website", {}))}}

    # ── Step 3: Extract facts ──────────────────────────────────────────────
    yield {"step": 3, "label": "Extracting structured facts", "status": "running", "data": None}
    facts = extract_facts(parsed.combined_raw)
    yield {"step": 3, "label": "Extracting structured facts", "status": "done",
           "data": {"input_quality": facts.get("input_quality", "unknown")}}

    # ── Step 4: Reason ─────────────────────────────────────────────────────
    yield {"step": 4, "label": "Generating commercial intelligence", "status": "running", "data": None}
    analysis = reason(facts, enriched_text, parsed.seller_context)
    yield {"step": 4, "label": "Generating commercial intelligence", "status": "done",
           "data": {"hooks_found": len(analysis.get("conversation_hooks", []))}}

    # ── Step 5: Synthesize ─────────────────────────────────────────────────
    yield {"step": 5, "label": "Writing the brief", "status": "running", "data": None}
    brief = synthesize(facts, analysis)
    yield {"step": 5, "label": "Writing the brief", "status": "done", "data": None}

    # ── Step 6: Quality check ──────────────────────────────────────────────
    yield {"step": 6, "label": "Running quality / slop filter", "status": "running", "data": None}
    quality = score_brief(brief)
    yield {"step": 6, "label": "Running quality / slop filter", "status": "done",
           "data": {"score": quality["overall_specificity_score"],
                    "passed": quality["passed"],
                    "banned": quality["banned_words_found"]}}

    # ── Step 7: Save & return ──────────────────────────────────────────────
    person_name = (facts.get("person") or {}).get("name") or name_guess or "Unknown"
    company_name = (facts.get("company") or {}).get("name") or company_guess or "Unknown"

    brief_id = save_brief(
        person_name=person_name,
        company_name=company_name,
        inputs={"linkedin": linkedin, "company": company, "context": context, "seller_context": seller_context},
        enriched_data=enriched,
        brief=brief,
    )

    yield {
        "step": 7,
        "label": "Complete",
        "status": "done",
        "data": {
            "brief": brief,
            "facts": facts,
            "analysis": analysis,
            "enriched": enriched,
            "quality": quality,
            "brief_id": brief_id,
            "person_name": person_name,
            "company_name": company_name,
            "warnings": parsed.warnings,
        },
    }


def _guess_name(text: str) -> str:
    """Heuristic: first line of LinkedIn text often contains the name."""
    if not text:
        return ""
    first_line = text.strip().split("\n")[0].strip()
    # If it looks like a name (2-4 words, no lowercase-start words except prepositions)
    words = first_line.split()
    if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w not in ("de", "van", "von", "la")):
        return first_line
    return ""


def _guess_company(text: str) -> str:
    """Try to find a company name via common patterns."""
    import re
    patterns = [
        r"(?:at|@)\s+([A-Z][a-zA-Z0-9\s&\.]+?)(?:\s*[,|\n]|$)",
        r"([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3})\s+(?:Ltd|Limited|Inc|Corp|LLC|GmbH|SaaS|AI|Tech)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""
