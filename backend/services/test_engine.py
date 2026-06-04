import json
import os
import random
import httpx
from typing import List
from models.schemas import TestSubmissionItem

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

async def generate_weekly_test(level: str = "A1"):
    try:
        with open(f"data/test_prompts/weekly_{level.lower()}.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        # Fallback to A1 if level file doesn't exist
        with open("data/test_prompts/weekly_a1.json", "r") as f:
            data = json.load(f)
            
    # Randomly select questions to ensure variety while keeping format locked
    return {
        "word_order": random.sample(data.get("word_order", []), min(4, len(data.get("word_order", [])))),
        "vocabulary": random.sample(data.get("vocabulary", []), min(3, len(data.get("vocabulary", [])))),
        "short_response": random.sample(data.get("short_response", []), min(3, len(data.get("short_response", []))))
    }

async def evaluate_short_response(prompt: str, answer: str) -> float:
    """Evaluates a short response and returns a score between 0.0 and 1.0"""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return 0.8  # Stub for testing

    system_prompt = f"""\
You are a German language test evaluator.
The prompt was: "{prompt}"
The learner answered: "{answer}"

Evaluate the answer based on word order, vocabulary appropriateness, and comprehensibility.
Return ONLY a valid JSON object:
{{
  "score": <float between 0.0 and 1.0>
}}
"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "deepseek/deepseek-v4-flash",
                    "messages": [{"role": "user", "content": system_prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
            )
            data = resp.json()
            result = json.loads(data["choices"][0]["message"]["content"])
            return float(result.get("score", 0.0))
    except Exception as e:
        print(f"Error evaluating response: {e}")
        return 0.5

async def evaluate_test(level: str, answers: List[TestSubmissionItem]) -> dict:
    try:
        with open(f"data/test_prompts/weekly_{level.lower()}.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        with open("data/test_prompts/weekly_a1.json", "r") as f:
            data = json.load(f)

    total_possible = 10
    score = 0.0
    details = {"word_order": 0, "vocabulary": 0, "short_response": 0.0}
    breakdown = []

    import string
    
    for item in answers:
        if item.type == "word_order":
            q = next((x for x in data["word_order"] if x["id"] == item.id), None)
            if q:
                clean_correct = q["correct"].lower().strip(string.punctuation + " ")
                clean_answer = item.answer.lower().strip(string.punctuation + " ")
                is_correct = clean_correct == clean_answer
                if is_correct:
                    score += 1.0
                    details["word_order"] += 1
                breakdown.append({
                    "id": item.id,
                    "type": item.type,
                    "is_correct": is_correct,
                    "user_answer": item.answer,
                    "correct_answer": q["correct"]
                })
        elif item.type == "vocabulary":
            q = next((x for x in data["vocabulary"] if x["id"] == item.id), None)
            if q:
                is_correct = str(q["correct_index"]) == item.answer
                if is_correct:
                    score += 1.0
                    details["vocabulary"] += 1
                breakdown.append({
                    "id": item.id,
                    "type": item.type,
                    "is_correct": is_correct,
                    "user_answer": item.answer,
                    "correct_answer": q["options"][q["correct_index"]]
                })
        elif item.type == "short_response":
            q = next((x for x in data["short_response"] if x["id"] == item.id), None)
            if q:
                item_score = await evaluate_short_response(q["prompt"], item.answer)
                score += item_score
                details["short_response"] += item_score
                breakdown.append({
                    "id": item.id,
                    "type": item.type,
                    "is_correct": item_score > 0.6,
                    "user_answer": item.answer,
                    "correct_answer": "AI evaluated score: " + str(item_score)
                })

    normalized_score = score / total_possible
    return {
        "score": round(normalized_score, 2),
        "details": details,
        "cefr_level": level,
        "breakdown": breakdown
    }
