"""
Step 2 — Web enrichment.
Scrapes company website and searches for recent news about the person/company.
Degrades gracefully if tools are unavailable.
"""
import os
import re
import requests
from typing import Optional

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SalesIntelBot/1.0; research tool)"
}
TIMEOUT = 8


def _fetch_url(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        if HAS_TRAFILATURA:
            text = trafilatura.extract(resp.text, include_links=False, include_images=False)
            return (text or "")[:4000]
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:4000]
    except Exception:
        return ""


def _scrape_company_site(url: str) -> dict:
    if not url:
        return {}

    # Normalise URL
    if not url.startswith("http"):
        url = "https://" + url

    homepage = _fetch_url(url)
    about = _fetch_url(url.rstrip("/") + "/about")
    blog_index = _fetch_url(url.rstrip("/") + "/blog")

    # Grab latest blog post if we found any links
    latest_blog = ""
    if blog_index and HAS_TRAFILATURA:
        # rough heuristic: find first article-like URL
        links = re.findall(r'href=["\']([^"\']*blog[^"\']*)["\']', blog_index)
        for link in links[:2]:
            if link.startswith("/"):
                link = url.rstrip("/") + link
            if link.startswith("http"):
                latest_blog = _fetch_url(link)
                if latest_blog:
                    break

    return {
        "homepage": homepage,
        "about_page": about,
        "blog_latest": latest_blog,
    }


def _search_news(person_name: str, company_name: str, max_results: int = 5) -> list[dict]:
    if not HAS_DDG:
        return []

    results = []
    queries = []

    if person_name and company_name:
        queries.append(f'"{person_name}" "{company_name}"')
    if company_name:
        queries.append(f'"{company_name}" funding OR announcement OR launch OR partnership')
    if person_name:
        queries.append(f'"{person_name}" interview OR announcement')

    try:
        with DDGS() as ddgs:
            for query in queries[:2]:
                hits = ddgs.text(query, max_results=max_results, safesearch="off")
                for h in (hits or []):
                    results.append({
                        "title": h.get("title", ""),
                        "body": h.get("body", "")[:500],
                        "url": h.get("href", ""),
                        "query": query,
                    })
    except Exception:
        pass

    # Deduplicate by URL
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:8]


def _search_serper(person_name: str, company_name: str) -> list[dict]:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []

    results = []
    queries = []
    if person_name and company_name:
        queries.append(f'"{person_name}" "{company_name}"')
    if company_name:
        queries.append(f'"{company_name}" funding OR product OR announcement')

    for query in queries[:2]:
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5},
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                timeout=TIMEOUT,
            )
            data = resp.json()
            for item in data.get("organic", [])[:4]:
                results.append({
                    "title": item.get("title", ""),
                    "body": item.get("snippet", "")[:500],
                    "url": item.get("link", ""),
                    "query": query,
                })
        except Exception:
            pass

    return results


def _scrape_job_postings(company_name: str, company_url: str) -> list[str]:
    """Look for open roles — they reveal current hiring priorities."""
    roles = []
    if not HAS_DDG or not company_name:
        return roles

    try:
        with DDGS() as ddgs:
            query = f'site:linkedin.com/jobs OR site:greenhouse.io OR site:lever.co "{company_name}" jobs'
            hits = ddgs.text(query, max_results=6, safesearch="off")
            for h in (hits or [])[:6]:
                title = h.get("title", "")
                if title:
                    # Strip boilerplate from job titles
                    title = re.sub(r'\s*[-|].*$', '', title).strip()
                    if len(title) < 80:
                        roles.append(title)
    except Exception:
        pass

    return roles[:6]


def enrich(
    person_name: Optional[str],
    company_name: Optional[str],
    company_url: Optional[str],
) -> dict:
    enriched = {
        "company_website": {},
        "news": [],
        "job_postings": [],
        "enrichment_notes": [],
    }

    # Prefer Serper if available (better quality), fall back to DDG
    if os.getenv("SERPER_API_KEY"):
        enriched["news"] = _search_serper(person_name or "", company_name or "")
        enriched["enrichment_notes"].append("News search: Serper (Google)")
    elif HAS_DDG:
        enriched["news"] = _search_news(person_name or "", company_name or "")
        enriched["enrichment_notes"].append("News search: DuckDuckGo")
    else:
        enriched["enrichment_notes"].append("News search: unavailable (install duckduckgo-search)")

    if company_url:
        enriched["company_website"] = _scrape_company_site(company_url)
        enriched["enrichment_notes"].append(f"Company website scraped: {company_url}")

    enriched["job_postings"] = _scrape_job_postings(company_name or "", company_url or "")

    return enriched


def format_enriched_for_prompt(enriched: dict) -> str:
    parts = []

    website = enriched.get("company_website", {})
    if website.get("homepage"):
        parts.append(f"COMPANY HOMEPAGE CONTENT:\n{website['homepage'][:2000]}")
    if website.get("about_page"):
        parts.append(f"ABOUT PAGE:\n{website['about_page'][:1500]}")
    if website.get("blog_latest"):
        parts.append(f"LATEST BLOG POST:\n{website['blog_latest'][:1000]}")

    news = enriched.get("news", [])
    if news:
        news_text = "\n".join(
            f"- [{n['title']}] {n['body']} (source: {n['url']})"
            for n in news
        )
        parts.append(f"WEB SEARCH RESULTS:\n{news_text}")

    jobs = enriched.get("job_postings", [])
    if jobs:
        parts.append(f"OPEN JOB POSTINGS FOUND:\n" + "\n".join(f"- {j}" for j in jobs))

    if not parts:
        return "No enrichment data available — analysis based solely on provided input."

    return "\n\n".join(parts)
