"""
Step 1 — Parse and validate raw user inputs.
Returns a normalised input bundle with quality signals.
"""
from dataclasses import dataclass, field


@dataclass
class ParsedInput:
    linkedin_text: str = ""
    company_text: str = ""
    extra_context: str = ""
    seller_context: str = ""
    company_url: str = ""
    combined_raw: str = ""
    warnings: list[str] = field(default_factory=list)
    is_viable: bool = True


def parse_inputs(
    linkedin: str,
    company: str,
    context: str,
    seller_context: str,
) -> ParsedInput:
    inp = ParsedInput(
        linkedin_text=linkedin.strip(),
        company_text=company.strip(),
        extra_context=context.strip(),
        seller_context=seller_context.strip(),
    )

    # Extract URL if present in company field
    for word in company.split():
        if word.startswith(("http://", "https://", "www.")):
            inp.company_url = word if word.startswith("http") else f"https://{word}"
            break

    total_chars = len(inp.linkedin_text) + len(inp.company_text) + len(inp.extra_context)

    if total_chars < 80:
        inp.warnings.append(
            "Very little input provided. The brief will have low confidence — paste a LinkedIn profile or company description for better results."
        )
        inp.is_viable = total_chars > 20

    if not inp.linkedin_text and not inp.company_text:
        inp.is_viable = False
        inp.warnings.append("Please provide at least a LinkedIn profile snippet or company description.")

    inp.combined_raw = "\n\n---\n\n".join(
        filter(
            None,
            [
                f"LINKEDIN PROFILE:\n{inp.linkedin_text}" if inp.linkedin_text else "",
                f"COMPANY INFO:\n{inp.company_text}" if inp.company_text else "",
                f"ADDITIONAL CONTEXT:\n{inp.extra_context}" if inp.extra_context else "",
            ],
        )
    )

    return inp
