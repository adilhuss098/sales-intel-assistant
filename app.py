import json
import streamlit as st
from datetime import datetime
from pipeline.runner import run_pipeline
from storage.db import init_db, list_briefs, get_brief, delete_brief

st.set_page_config(
    page_title="Sales Intel Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


# ══════════════════════════════════════════════════════════════════════════
# Helper functions — defined before any page routing
# ══════════════════════════════════════════════════════════════════════════

def _render_brief(result: dict):
    brief = result["brief"]
    quality = result["quality"]
    person = result["person_name"]
    company = result["company_name"]
    enriched = result.get("enriched", {})
    warnings = result.get("warnings", [])

    st.divider()

    # Header
    hcol1, hcol2, hcol3 = st.columns([3, 1, 1])
    with hcol1:
        st.subheader(f"{person} · {company}")
    with hcol2:
        level = brief.get("confidence_level", "low")
        colour = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(level, "⚪")
        st.metric("Confidence", f"{colour} {level.capitalize()}")
    with hcol3:
        score = quality.get("overall_specificity_score", 0)
        st.metric("Specificity", f"{score}/5")

    st.info(f"**Snapshot:** {brief.get('snapshot', '')}")

    for w in warnings:
        st.warning(w)

    if brief.get("confidence_note"):
        st.caption(f"⚠️ {brief['confidence_note']}")

    st.divider()

    # Main content: two columns
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("### 🧭 Role Context")
        st.markdown(brief.get("role_context_summary", ""))
        st.divider()

        st.markdown("### 🏢 Company Signals")
        st.markdown(brief.get("company_signals", ""))
        st.divider()

        st.markdown("### 🎯 Commercial Priorities")
        for p in brief.get("commercial_priorities", []):
            conf = p.get("confidence", "low")
            badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
            st.markdown(f"{badge} **{p.get('priority', '')}**")
            st.caption(f"Basis: {p.get('basis', '')}")
        st.divider()

        st.markdown("### ⚡ Pain Points")
        for p in brief.get("pain_points", []):
            conf = p.get("confidence", "low")
            badge = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "⚪")
            st.markdown(f"{badge} **{p.get('pain', '')}**")
            st.caption(f"Basis: {p.get('basis', '')}")

    with right:
        if brief.get("seller_relevance"):
            st.markdown("### 🔗 Why You're Relevant")
            st.markdown(brief["seller_relevance"])
            st.divider()

        st.markdown("### 🪝 Conversation Hooks")
        for h in brief.get("conversation_hooks", []):
            hook_text = h.get("hook", "")
            label = hook_text[:80] + ("..." if len(hook_text) > 80 else "")
            with st.expander(label):
                st.markdown(f"**Hook:** {hook_text}")
                st.caption(f"Basis: {h.get('basis', '')}")
                st.caption(f"Opens angle: {h.get('opens_angle', '')}")
        st.divider()

        if brief.get("timing_signals"):
            st.markdown("### ⏰ Timing Signals")
            for t in brief["timing_signals"]:
                st.markdown(f"- {t}")
            st.divider()

        if brief.get("things_to_avoid"):
            st.markdown("### 🚫 Things to Avoid")
            for t in brief["things_to_avoid"]:
                st.markdown(f"- {t}")

    st.divider()

    # Templates
    st.markdown("### ✉️ Outreach Templates")
    t1, t2, t3 = st.tabs(["LinkedIn DM", "Cold Email", "Discovery Questions"])

    with t1:
        dm = brief.get("linkedin_dm", "")
        st.text_area("LinkedIn DM (edit before sending)", dm, height=150, key="dm_out")
        st.caption(f"{len(dm.split())} words")

    with t2:
        email = brief.get("cold_email", {})
        st.text_input("Subject", email.get("subject", ""), key="email_subject")
        st.text_area("Body (edit before sending)", email.get("body", ""), height=200, key="email_body")
        st.caption(f"{len(email.get('body','').split())} words")

    with t3:
        st.markdown("Questions grounded in this specific prospect's situation:")
        for i, q in enumerate(brief.get("call_questions", []), 1):
            st.markdown(f"**{i}.** {q}")

    st.divider()

    # Quality report
    with st.expander("🔬 Quality Report (slop filter output)"):
        slop_report = quality.get("slop_report", [])
        banned = quality.get("banned_words_found", [])

        if banned:
            st.error(f"Banned words detected in output: {', '.join(banned)}")
        else:
            st.success("No banned words detected")

        for item in slop_report:
            if not isinstance(item, dict):
                continue
            sc = item.get("specificity_score", 0)
            verdict = item.get("verdict", "")
            colour = "🟢" if sc >= 4 else ("🟡" if sc >= 3 else "🔴")
            st.markdown(f"{colour} **[{item.get('section','')}]** score {sc}/5 · {verdict}")
            if item.get("generic_phrases_found"):
                st.caption(f"Generic phrases: {', '.join(item['generic_phrases_found'])}")
            if item.get("notes"):
                st.caption(item["notes"])

    # Raw research
    with st.expander("🔍 Raw Research Data (evidence trail)"):
        news = enriched.get("news", [])
        jobs = enriched.get("job_postings", [])
        website = enriched.get("company_website", {})

        if news:
            st.markdown("**News search results:**")
            for n in news:
                st.markdown(f"- [{n.get('title','')}]({n.get('url','')}) — {n.get('body','')[:200]}")

        if jobs:
            st.markdown("**Open job postings found:**")
            for j in jobs:
                st.markdown(f"- {j}")

        if website.get("homepage"):
            st.markdown("**Company homepage extract:**")
            st.text(website["homepage"][:800])

    # Export
    st.divider()
    ecol1, ecol2 = st.columns(2)
    with ecol1:
        brief_md = _brief_to_markdown(brief, person, company, quality)
        st.download_button(
            "⬇️ Download as Markdown",
            data=brief_md,
            file_name=f"brief_{person.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )
    with ecol2:
        st.download_button(
            "⬇️ Download raw JSON",
            data=json.dumps(
                {"brief": brief, "facts": result.get("facts"), "quality": quality}, indent=2
            ),
            file_name=f"brief_{person.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
        )

    st.caption(f"Brief ID {result.get('brief_id')} · saved to local history")


def _brief_to_markdown(brief: dict, person: str, company: str, quality: dict) -> str:
    lines = [
        f"# Sales Intelligence Brief: {person} · {company}",
        f"**Confidence:** {brief.get('confidence_level','').capitalize()} · **Specificity score:** {quality.get('overall_specificity_score','?')}/5",
        "",
        "## Snapshot",
        brief.get("snapshot", ""),
        "",
        "## Role Context",
        brief.get("role_context_summary", ""),
        "",
        "## Company Signals",
        brief.get("company_signals", ""),
        "",
        "## Commercial Priorities",
    ]
    for p in brief.get("commercial_priorities", []):
        lines.append(f"- **{p.get('priority','')}** [{p.get('confidence','')}]")
        lines.append(f"  - Basis: {p.get('basis','')}")

    lines += ["", "## Pain Points"]
    for p in brief.get("pain_points", []):
        lines.append(f"- **{p.get('pain','')}** [{p.get('confidence','')}]")
        lines.append(f"  - Basis: {p.get('basis','')}")

    lines += ["", "## Conversation Hooks"]
    for h in brief.get("conversation_hooks", []):
        lines.append(f"- **{h.get('hook','')}**")
        lines.append(f"  - Basis: {h.get('basis','')}")
        lines.append(f"  - Opens angle: {h.get('opens_angle','')}")

    if brief.get("seller_relevance"):
        lines += ["", "## Why You're Relevant", brief["seller_relevance"]]

    lines += ["", "## LinkedIn DM", brief.get("linkedin_dm", "")]

    email = brief.get("cold_email", {})
    lines += [
        "", "## Cold Email",
        f"**Subject:** {email.get('subject','')}",
        "",
        email.get("body", ""),
    ]

    lines += ["", "## Discovery Questions"]
    for i, q in enumerate(brief.get("call_questions", []), 1):
        lines.append(f"{i}. {q}")

    if brief.get("things_to_avoid"):
        lines += ["", "## Things to Avoid"]
        for t in brief["things_to_avoid"]:
            lines.append(f"- {t}")

    if brief.get("timing_signals"):
        lines += ["", "## Timing Signals"]
        for t in brief["timing_signals"]:
            lines.append(f"- {t}")

    if brief.get("confidence_note"):
        lines += ["", f"> ⚠️ {brief['confidence_note']}"]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# Sidebar navigation
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎯 Sales Intel")
    page = st.radio("", ["Generate Brief", "History", "How It Works"], label_visibility="collapsed")
    st.divider()
    st.caption("Powered by Claude Sonnet · Local storage only")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Generate Brief
# ══════════════════════════════════════════════════════════════════════════
if page == "Generate Brief":
    st.title("Sales Intelligence Brief")
    st.caption("Paste in what you know. Get back a specific, grounded brief — not generic AI filler.")

    col_left, col_right = st.columns([2, 1], gap="large")

    with col_left:
        with st.expander("📋 LinkedIn Profile", expanded=True):
            linkedin = st.text_area(
                "Paste their LinkedIn profile text (name, title, experience, about section)",
                height=160,
                placeholder="James Whitmore\nCTO at Vanta AI · London\n\nPreviously VP Engineering at Monzo (3 years)...",
                key="linkedin",
            )

        with st.expander("🏢 Company Info", expanded=True):
            company = st.text_area(
                "Company website URL, description, or paste from Crunchbase / news",
                height=120,
                placeholder="https://vanta.ai  —  OR—  'Vanta raised $150M Series C in Oct 2024, ~400 employees, sells compliance automation to mid-market tech companies'",
                key="company",
            )

        with st.expander("📎 Additional Context"):
            context = st.text_area(
                "Anything else: recent conversations, referrals, specific projects, mutual connections",
                height=80,
                placeholder="Met at SaaStr. Said they're mid-way through a CRM migration. Referred by Tom Haines.",
                key="context",
            )

    with col_right:
        st.markdown("**What are you selling?**")
        seller_context = st.text_area(
            "Your company and product — used to tailor hooks and relevance section",
            height=140,
            placeholder="I'm at Gong. We sell revenue intelligence — call recording, AI summaries, deal risk alerts. Target: VP Sales / CRO at B2B SaaS companies with 50-500 reps.",
            key="seller",
        )

        st.divider()
        generate = st.button("Generate Brief →", type="primary", use_container_width=True)

        st.caption(
            "Pipeline: parse → enrich from web → extract (Haiku) → "
            "reason (Sonnet) → synthesize (Sonnet) → slop filter (Haiku)"
        )

    if generate:
        if not linkedin.strip() and not company.strip():
            st.error("Add a LinkedIn profile or company description to continue.")
        else:
            result = None
            progress_area = st.container()

            with progress_area:
                status_box = st.status("Running pipeline...", expanded=True)
                with status_box:
                    step_labels = {
                        1: "Parsing inputs",
                        2: "Enriching from web (scrape + news search)",
                        3: "Extracting structured facts",
                        4: "Generating commercial intelligence (Sonnet)",
                        5: "Writing the brief (Sonnet)",
                        6: "Quality check / slop filter (Haiku)",
                    }
                    placeholders = {k: st.empty() for k in step_labels}

                    for update in run_pipeline(
                        linkedin=linkedin,
                        company=company,
                        context=context,
                        seller_context=seller_context,
                    ):
                        s = update["step"]
                        status = update["status"]
                        data = update.get("data")

                        if s in placeholders:
                            icon = "⏳" if status == "running" else ("✅" if status == "done" else "❌")
                            extra = ""
                            if status == "done" and data:
                                if s == 2:
                                    extra = f" · {data.get('news_count',0)} news hits, {data.get('jobs_count',0)} job postings"
                                    if data.get("website_scraped"):
                                        extra += ", website scraped"
                                elif s == 3:
                                    extra = f" · input quality: {data.get('input_quality','?')}"
                                elif s == 4:
                                    extra = f" · {data.get('hooks_found',0)} conversation hooks found"
                                elif s == 6:
                                    sc = data.get("score", 0)
                                    banned = data.get("banned", [])
                                    extra = f" · specificity score {sc}/5"
                                    if banned:
                                        extra += f" ⚠️ banned words: {', '.join(banned)}"
                            placeholders[s].markdown(f"{icon} **{step_labels.get(s, '')}**{extra}")

                        if status == "error":
                            st.error(f"Pipeline stopped: {data}")
                            break

                        if s == 7 and status == "done":
                            result = data
                            status_box.update(label="Brief generated", state="complete")

            if result:
                _render_brief(result)

    else:
        st.divider()
        st.markdown(
            """
**How this works:**
1. Paste what you know about the prospect
2. The pipeline enriches it with live web data (company site, news, job postings)
3. Claude reasons about their specific commercial situation — not generic role archetypes
4. A slop filter removes anything generic before you see it
5. You get a brief grounded in actual facts, with evidence trails and confidence scores
            """
        )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: History
# ══════════════════════════════════════════════════════════════════════════
elif page == "History":
    st.title("Brief History")
    briefs = list_briefs()

    if not briefs:
        st.info("No briefs yet. Generate one on the main page.")
    else:
        for row in briefs:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                ts = row["created_at"][:16].replace("T", " ")
                label = f"**{row['person_name']}** · {row['company_name']}  ({ts})"
                if st.button(label, key=f"load_{row['id']}", use_container_width=True):
                    st.session_state["history_view"] = row["id"]
            with col2:
                level = row.get("confidence_level", "")
                colour = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(level, "⚪")
                st.markdown(f"{colour} {level.capitalize()}")
            with col3:
                if st.button("🗑️", key=f"del_{row['id']}"):
                    delete_brief(row["id"])
                    st.rerun()

        if "history_view" in st.session_state:
            bid = st.session_state["history_view"]
            record = get_brief(bid)
            if record:
                st.divider()
                _render_brief({
                    "brief": record["brief_json"],
                    "facts": {},
                    "analysis": {},
                    "enriched": record["enriched_data"],
                    "quality": {
                        "overall_specificity_score": "–",
                        "slop_report": [],
                        "banned_words_found": [],
                    },
                    "brief_id": bid,
                    "person_name": record["person_name"],
                    "company_name": record["company_name"],
                    "warnings": [],
                })


# ══════════════════════════════════════════════════════════════════════════
# PAGE: How It Works
# ══════════════════════════════════════════════════════════════════════════
elif page == "How It Works":
    st.title("How It Works")
    st.markdown("""
## The pipeline

This tool runs a 6-step pipeline rather than one big AI prompt.
Each step does exactly one job. This is why the output is specific rather than generic.

```
Input
  │
  ▼
[1] Parse & Validate
    Normalise inputs, detect company URL, flag thin inputs early.
  │
  ▼
[2] Web Enrichment
    Scrape company website (homepage, about, blog).
    Search for recent news about the person and company.
    Pull open job postings (reveals hiring priorities).
  │
  ▼
[3] Extract Facts  [Claude Haiku — cheap]
    Parse the raw input into a clean, structured fact sheet.
    Rule: extract only what's stated. Never infer at this step.
  │
  ▼
[4] Reason  [Claude Sonnet — heavy lifting]
    Given the fact sheet + enriched data, produce grounded analysis.
    Every insight must cite a specific source.
    Banned word list enforced in the prompt.
    What makes THIS person's situation different from the generic archetype?
  │
  ▼
[5] Synthesize  [Claude Sonnet]
    Render the analysis into the final brief format.
    Templates must contain specific references — no fill-in-the-blank.
  │
  ▼
[6] Quality Check  [Claude Haiku — cheap]
    Slop filter: read every section, score specificity 1–5.
    Flag banned words.
    Flag sentences that could apply to anyone in the same role.
```

## Why it's not generic

The key constraint is in the **reason** prompt:

> *"Every insight must cite a specific fact that caused you to conclude it.
> If you can't point to something concrete, do not state the insight."*

Combined with a banned-words list ("leverage", "synergy", etc.) and a requirement
to name competitors, tools, and metrics — the model is forced to reason from evidence.

The slop filter is a second model call that reads the output and flags anything that
could apply to any person with the same title. Specificity is scored 1–5 per section.

## Storage

Everything stays local. No data leaves your machine except API calls to Anthropic.
All briefs are stored in `history.db` (SQLite) in the project folder.

## Models used

| Step | Model | Why |
|------|-------|-----|
| Extract | Claude Haiku | Cheap, fast. Just parsing — no heavy reasoning needed. |
| Reason | Claude Sonnet | Best reasoning quality for the analytical core. |
| Synthesize | Claude Sonnet | Needs to render complex analysis faithfully. |
| Slop filter | Claude Haiku | Simple classification task — no need for Sonnet. |
""")
