"""Run the clarification-judgment eval suite against a real LLM.

Usage (from the project root, with the ideaos-agent environment):

    conda run -n ideaos-agent python evals/run_eval.py

The script reads the same configuration as the app. When a real LLM is not
configured (Fake mode or missing key), it falls back to FakeLlmClient so the
report shape stays runnable anywhere. Run it before and after a prompt change
and compare the per-case table.
"""

import json
from pathlib import Path

from ideaos_agent.config import get_settings
from ideaos_agent.infrastructure.llm.client import HttpLlmClient
from ideaos_agent.infrastructure.llm.fake_client import FakeLlmClient
from ideaos_agent.infrastructure.llm.parsing import parse_idea_analysis_response
from ideaos_agent.prompts.idea_analysis import IdeaAnalysisPromptBuilder

EVALS_DIR = Path(__file__).resolve().parent
CASES_PATH = EVALS_DIR / "clarification_cases.json"


def load_cases() -> list[dict[str, object]]:
    """Load and validate the eval case list."""

    with CASES_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    cases = payload["cases"] if isinstance(payload, dict) else payload
    if not isinstance(cases, list) or not cases:
        raise ValueError("clarification_cases.json must contain a non-empty 'cases' list.")
    return cases


def main() -> None:
    """Run every case and print a per-case report with an overall summary."""

    settings = get_settings()
    prompt_builder = IdeaAnalysisPromptBuilder()

    if settings.use_fake_llm or not settings.llm_api_key:
        print("Real LLM not configured; falling back to FakeLlmClient.")
        client = FakeLlmClient()
    else:
        client = HttpLlmClient(
            provider=settings.llm_provider,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    cases = load_cases()
    rows: list[dict[str, object]] = []
    clarified_count = 0
    matched_count = 0

    for case in cases:
        case_id = str(case["id"])
        content = str(case["input"])
        expected = bool(case["expected"]["needs_clarification"])
        user_prompt = prompt_builder.build_user_prompt(content, [])
        raw_text = client.generate_text(
            system_prompt=prompt_builder.system_prompt,
            user_prompt=user_prompt,
        )
        parsed = parse_idea_analysis_response(raw_text)
        actual = parsed.needs_clarification
        if actual:
            clarified_count += 1
        if actual == expected:
            matched_count += 1
        rows.append(
            {
                "id": case_id,
                "category": case.get("category", ""),
                "expected": expected,
                "actual": actual,
                "match": actual == expected,
                "rationale": parsed.clarification_rationale,
            }
        )

    total = len(rows)
    print(
        f"cases={total} clarified={clarified_count} ({clarified_count / total:.0%}) "
        f"matched={matched_count}/{total} ({matched_count / total:.0%})"
    )
    for row in rows:
        mark = "OK  " if row["match"] else "MISS"
        print(
            f"[{mark}] {row['id']} ({row['category']}) expected={row['expected']} "
            f"actual={row['actual']} rationale={row['rationale']}"
        )


if __name__ == "__main__":
    main()