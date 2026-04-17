"""Debug test — calls OpenAI for real to validate the reasoning evaluation prompt.

Requires OPENAI_API_KEY in env.
Run: python -m pytest tests/test_score_reasoning_openai.py -v -s
"""

import os

import pytest
import pytest_asyncio

from crunch_node.tasks.score_reasoning import ScoreReasoning

SAMPLE_REASONING = """
Based on Federal Reserve meeting minutes from March 2025 (source: federalreserve.gov),
the Fed signaled a hold on interest rates at 5.25-5.50%. Combined with BLS employment
data showing 275K jobs added (source: bls.gov), the labor market remains tight.

Key evidence ranked by importance:
1. Fed funds rate unchanged — strongest signal for continued dollar strength
2. Employment data above consensus (expected 200K) — reduces rate cut probability
3. CPI at 3.1% (source: bls.gov) — still above 2% target

Weighting: Fed policy (50%) + Employment (30%) + Inflation (20%)
Combined score: 0.5 * 0.8 + 0.3 * 0.7 + 0.2 * 0.6 = 0.73 probability of resolution YES.

Uncertainties:
- Geopolitical risk (Ukraine, Middle East) could shift sentiment unexpectedly
- Banking sector stress (regional banks) not fully priced in
- Impact on probability: +/- 10% depending on escalation

Final probability: 73% YES, mapped from the weighted evidence above.
The 73% reflects strong macro fundamentals slightly tempered by geopolitical tail risks.
"""


@pytest.fixture
def openai_api_key():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set")
    return key


@pytest.mark.asyncio
async def test_evaluate_reasoning(openai_api_key, mock_logger):
    """Call OpenAI with sample reasoning and verify structured output."""
    task = ScoreReasoning(
        interval_seconds=300,
        pg_client=None,
        openai_api_key=openai_api_key,
        openai_model="gpt-5.4",
        logger=mock_logger,
    )

    result = await task._evaluate(SAMPLE_REASONING)

    assert result is not None, "OpenAI returned None"
    print(f"\nScores: {result}")

    for key in ("sources", "evidence", "weighting", "uncertainties", "mapping"):
        assert key in result, f"Missing key: {key}"
        assert 1 <= result[key] <= 5, f"{key}={result[key]} out of range"

    avg = sum(result.values()) / 5
    print(f"Average: {avg:.1f}/5")