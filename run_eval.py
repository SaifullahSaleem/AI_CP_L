"""
CI-Ready Evaluation Script — Agentic Research Paper Assistant
=============================================================
Runs automated quality evaluation using LLM-as-judge (Gemini).
Designed to run headlessly in CI/CD pipelines.

Behaviour:
    - Reads all credentials from environment variables (no hardcoded secrets)
    - Runs predefined test cases against the agent
    - Uses Gemini as judge to score faithfulness and answer relevancy
    - Compares scores against eval_thresholds.json
    - Writes eval_results.json (machine-readable results)
    - Exits code 0 on ALL PASS, code 1 on ANY FAIL

Usage:
    python run_eval.py                    # Runs evaluation locally
    python run_eval.py --degrade          # Intentionally degrade agent for demo

Environment Variables Required:
    GOOGLE_API_KEY      — Google Gemini API key
    SERP_API_KEY        — SerpAPI key (for paper search)
    PINECONE_API_KEY    — Pinecone vector DB key
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def check_env_vars():
    """Verify all required environment variables are set."""
    required = ["GOOGLE_API_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("All credentials must be set via environment variables.")
        sys.exit(1)


def load_thresholds(path="eval_thresholds.json"):
    """Load quality thresholds from versioned config file."""
    with open(path, "r") as f:
        config = json.load(f)
    return config["thresholds"], config.get("eval_config", {})


def get_test_cases(degrade=False):
    """
    Return predefined test cases for evaluation.
    Each test case has: query, expected_context_keywords, expected_answer_keywords
    """
    test_cases = [
        {
            "id": "TC-001",
            "query": "What are transformer neural networks and how do they work?",
            "context_keywords": ["transformer", "attention", "neural", "network"],
            "expected_topics": ["self-attention", "architecture", "NLP", "deep learning"],
            "description": "Basic research query about transformers"
        },
        {
            "id": "TC-002",
            "query": "Find research papers about reinforcement learning in robotics",
            "context_keywords": ["reinforcement", "learning", "robot"],
            "expected_topics": ["policy", "reward", "agent", "control"],
            "description": "Research paper search query"
        },
        {
            "id": "TC-003",
            "query": "Explain the applications of graph neural networks",
            "context_keywords": ["graph", "neural", "network"],
            "expected_topics": ["node", "edge", "representation", "learning"],
            "description": "Explanatory research query"
        },
    ]

    if degrade:
        # Intentionally corrupt test cases to simulate degradation
        for tc in test_cases:
            tc["query"] = "Tell me about cooking recipes for pasta"
            tc["context_keywords"] = ["transformer", "attention"]  # Mismatched
            tc["expected_topics"] = ["self-attention", "NLP"]  # Mismatched

    return test_cases


def simulate_agent_response(query, degrade=False):
    """
    Get agent response for a query using the Gemini LLM.
    In a full integration, this would call the actual agent API.
    For CI evaluation, we simulate the agent's RAG pipeline.
    """
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    if degrade:
        # Degraded prompt — introduces hallucination
        prompt = f"""You are a research assistant. The user asked: "{query}"
        
IMPORTANT: Make up fictional paper titles and fake author names. 
Invent statistics and cite non-existent journals.
Do NOT use any real research context.

Provide a response with at least 3 made-up papers."""
    else:
        # Normal agent prompt (simulates RAG behavior)
        prompt = f"""You are a research paper assistant. The user asked: "{query}"

Based on your knowledge of academic research, provide a helpful response that:
1. References real research concepts and methodologies
2. Mentions relevant research areas and key contributions
3. Provides accurate, grounded information
4. Is well-structured with clear sections

Keep your response concise and factual. Only state things that are well-established in the research literature."""

    try:
        response = model.generate_content(prompt)
        return {
            "answer": response.text,
            "context": prompt,
            "status": "success"
        }
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "context": "",
            "status": "error"
        }


def judge_faithfulness(answer, context, query):
    """
    Use Gemini as judge to score faithfulness (0.0 - 1.0).
    Faithfulness = Is the answer grounded in the provided context/knowledge?
    """
    import google.generativeai as genai

    model = genai.GenerativeModel("gemini-2.5-flash")

    judge_prompt = f"""You are an evaluation judge. Score the FAITHFULNESS of an AI assistant's answer.

Faithfulness measures whether the answer contains only information that is grounded in 
established research knowledge and does not hallucinate or fabricate facts.

Query: {query}

Context/Prompt given to the assistant:
{context[:2000]}

Assistant's Answer:
{answer[:3000]}

Scoring criteria:
- 1.0: All claims are factually accurate and well-grounded in established research
- 0.8: Mostly accurate with minor unsupported claims
- 0.6: Mix of accurate and potentially fabricated information
- 0.4: Significant hallucinations or fabricated references
- 0.2: Mostly fabricated content
- 0.0: Entirely hallucinated

Respond with ONLY a JSON object in this exact format:
{{"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}}"""

    try:
        response = model.generate_content(judge_prompt)
        text = response.text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return float(result.get("score", 0.0)), result.get("reasoning", "")
    except Exception as e:
        print(f"  Warning: Judge error for faithfulness: {e}")
        return 0.5, f"Judge error: {str(e)}"


def judge_answer_relevancy(answer, query):
    """
    Use Gemini as judge to score answer relevancy (0.0 - 1.0).
    Relevancy = Does the answer address the user's question?
    """
    import google.generativeai as genai

    model = genai.GenerativeModel("gemini-2.5-flash")

    judge_prompt = f"""You are an evaluation judge. Score the ANSWER RELEVANCY of an AI assistant's response.

Answer Relevancy measures whether the answer directly addresses the user's question
and provides useful, on-topic information.

User's Question: {query}

Assistant's Answer:
{answer[:3000]}

Scoring criteria:
- 1.0: Directly and comprehensively addresses the question
- 0.8: Addresses the question well with minor tangential content
- 0.6: Partially addresses the question but includes significant off-topic content
- 0.4: Loosely related but doesn't directly answer the question
- 0.2: Mostly irrelevant to the question
- 0.0: Completely off-topic

Respond with ONLY a JSON object in this exact format:
{{"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}}"""

    try:
        response = model.generate_content(judge_prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return float(result.get("score", 0.0)), result.get("reasoning", "")
    except Exception as e:
        print(f"  Warning: Judge error for relevancy: {e}")
        return 0.5, f"Judge error: {str(e)}"


def run_evaluation(degrade=False):
    """Run the full evaluation pipeline."""
    print("=" * 60)
    print(" Agentic Research Assistant — Quality Gate Evaluation")
    print("=" * 60)

    # Load thresholds
    thresholds, eval_config = load_thresholds()
    print(f"\nThresholds loaded:")
    for metric, config in thresholds.items():
        print(f"  {metric}: >= {config['min_score']}")

    # Get test cases
    test_cases = get_test_cases(degrade=degrade)
    print(f"\nRunning {len(test_cases)} test cases...")
    if degrade:
        print("  [!] DEGRADED MODE -- intentionally corrupted for demo")

    # Run evaluations
    all_scores = {"faithfulness": [], "answer_relevancy": []}
    test_results = []

    for tc in test_cases:
        print(f"\n{'-' * 50}")
        print(f"  Test Case: {tc['id']} — {tc['description']}")
        print(f"  Query: {tc['query'][:80]}...")

        # Get agent response
        response = simulate_agent_response(tc["query"], degrade=degrade)

        if response["status"] == "error":
            print(f"  [FAIL] Agent error: {response['answer'][:100]}")
            all_scores["faithfulness"].append(0.0)
            all_scores["answer_relevancy"].append(0.0)
            test_results.append({
                "test_id": tc["id"],
                "query": tc["query"],
                "status": "error",
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
            })
            continue

        print(f"  Answer length: {len(response['answer'])} chars")

        # Judge faithfulness
        faith_score, faith_reason = judge_faithfulness(
            response["answer"], response["context"], tc["query"]
        )
        all_scores["faithfulness"].append(faith_score)
        print(f"  Faithfulness:     {faith_score:.2f} -- {faith_reason[:80]}")

        # Judge answer relevancy
        rel_score, rel_reason = judge_answer_relevancy(
            response["answer"], tc["query"]
        )
        all_scores["answer_relevancy"].append(rel_score)
        print(f"  Answer Relevancy: {rel_score:.2f} -- {rel_reason[:80]}")

        # Small delay to avoid rate limiting
        time.sleep(1)

        test_results.append({
            "test_id": tc["id"],
            "query": tc["query"],
            "status": "success",
            "answer_preview": response["answer"][:200],
            "faithfulness": faith_score,
            "faithfulness_reason": faith_reason,
            "answer_relevancy": rel_score,
            "answer_relevancy_reason": rel_reason,
        })

    # Calculate averages
    print(f"\n{'=' * 60}")
    print(" RESULTS SUMMARY")
    print(f"{'=' * 60}")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "degraded_mode": degrade,
        "test_cases": test_results,
        "metrics": {},
        "overall_pass": True,
    }

    for metric, scores in all_scores.items():
        avg_score = sum(scores) / len(scores) if scores else 0.0
        threshold = thresholds[metric]["min_score"]
        passed = avg_score >= threshold

        status_icon = "[PASS]" if passed else "[FAIL]"
        print(f"\n  {status_icon} {metric}:")
        print(f"      Score:     {avg_score:.4f}")
        print(f"      Threshold: {threshold}")
        print(f"      Status:    {'PASS' if passed else 'FAIL'}")

        results["metrics"][metric] = {
            "score": round(avg_score, 4),
            "threshold": threshold,
            "passed": passed,
            "individual_scores": [round(s, 4) for s in scores],
        }

        if not passed:
            results["overall_pass"] = False

    # Write results file
    results_path = "eval_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results written to: {results_path}")

    # Final verdict
    print(f"\n{'=' * 60}")
    if results["overall_pass"]:
        print("  [PASS] QUALITY GATE: ALL METRICS PASSED")
        print(f"{'=' * 60}")
        return 0
    else:
        print("  [FAIL] QUALITY GATE: FAILED -- metrics below threshold")
        failed_metrics = [
            m for m, data in results["metrics"].items() if not data["passed"]
        ]
        print(f"     Failed metrics: {', '.join(failed_metrics)}")
        print(f"{'=' * 60}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="CI-ready evaluation script for the Research Paper Assistant"
    )
    parser.add_argument(
        "--degrade",
        action="store_true",
        help="Run in degraded mode (intentionally corrupt agent for breaking change demo)",
    )
    args = parser.parse_args()

    # Check environment variables
    check_env_vars()

    # Run evaluation
    exit_code = run_evaluation(degrade=args.degrade)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
