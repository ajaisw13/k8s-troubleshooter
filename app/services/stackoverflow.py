import re
import requests

STACK_API = "https://api.stackexchange.com/2.3"


def search_stackoverflow(query: str, max_results: int = 3) -> str:
    try:
        questions = _fetch_questions(query, max_results)
        if not questions:
            return "No relevant Stack Overflow results found."

        answers_by_qid = _fetch_answers(questions)
        return _format_results(questions, answers_by_qid)
    except requests.RequestException as e:
        return f"Stack Overflow search failed: {e}"


def _fetch_questions(query: str, max_results: int) -> list:
    resp = requests.get(f"{STACK_API}/search/advanced", params={
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "tagged": "kubernetes",
        "site": "stackoverflow",
        "pagesize": max_results,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


def _fetch_answers(questions: list) -> dict:
    ids = ";".join(str(q["question_id"]) for q in questions)
    resp = requests.get(f"{STACK_API}/questions/{ids}/answers", params={
        "order": "desc",
        "sort": "votes",
        "site": "stackoverflow",
        "filter": "withbody",
    }, timeout=10)
    resp.raise_for_status()
    answers = {}
    for answer in resp.json().get("items", []):
        qid = answer["question_id"]
        if qid not in answers:
            answers[qid] = answer
    return answers


def _format_results(questions: list, answers_by_qid: dict) -> str:
    results = []
    for q in questions:
        qid = q["question_id"]
        title = q.get("title", "")
        link = q.get("link", "")
        answer = answers_by_qid.get(qid)
        if answer:
            body = re.sub(r"<[^>]+>", "", answer.get("body", "")).strip()
            body = body[:600] + "..." if len(body) > 600 else body
        else:
            body = "No answer available."
        results.append(f"Q: {title}\nLink: {link}\nTop Answer:\n{body}")
    return "\n\n---\n\n".join(results)
