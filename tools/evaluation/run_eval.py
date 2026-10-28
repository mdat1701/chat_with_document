from __future__ import annotations

import argparse
import asyncio
import html
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


def load_items(paths: list[str]) -> list[dict]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("Install PyYAML to run the evaluation harness") from exc
    items: list[dict] = []
    for path in paths:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        items.extend(data.get("items", []))
    return items


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def parse_sse(raw: str) -> dict:
    events: dict[str, list[dict]] = {}
    for block in raw.split("\n\n"):
        event = next((line[7:] for line in block.splitlines() if line.startswith("event: ")), "")
        data = next((line[6:] for line in block.splitlines() if line.startswith("data: ")), "")
        if event and data:
            events.setdefault(event, []).append(json.loads(data))
    done = events.get("done", [{}])[-1]
    deltas = "".join(item.get("text", "") for item in events.get("delta", []))
    citations = events.get("citations", [{}])[-1].get("items", [])
    return {"done": done, "answer": deltas, "citations": citations, "events": events}


async def ask(base_url: str, cookie: str, csrf_token: str, item: dict) -> dict:
    # `POST /conversations*` chạy sau `csrf_protection` (app/api/main.py) khi
    # có cookie phiên — thiếu header này mọi request sẽ bị 403 CSRF_INVALID,
    # bất kể `cookie` có hợp lệ hay không.
    headers = {"Cookie": cookie, "Content-Type": "application/json", "X-CSRF-Token": csrf_token}
    request = Request(f"{base_url.rstrip('/')}/conversations", method="POST", headers=headers)
    with urlopen(request) as response:
        conversation_id = json.loads(response.read())["conversation_id"]
    request = Request(
        f"{base_url.rstrip('/')}/conversations/{conversation_id}/questions",
        method="POST",
        data=json.dumps({"text": item["question"]}).encode(),
        headers=headers,
    )
    started = time.perf_counter()
    with urlopen(request) as response:
        raw = response.read().decode()
    parsed = parse_sse(raw)
    return {
        "id": item["id"],
        "lang": item.get("lang", "other"),
        "expected_answer_type": item.get("expected_answer_type"),
        "expected_facts": item.get("expected_facts", []),
        "expected_documents": item.get("expected_documents", []),
        "expected_pages": item.get("expected_pages", []),
        "answer": parsed["answer"],
        "citations": parsed["citations"],
        "done": parsed["done"],
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def evaluate(results: list[dict]) -> dict:
    no_answer = [item for item in results if item["expected_answer_type"] == "not_found"]
    answered = [item for item in results if item["expected_answer_type"] != "not_found"]
    not_found_recall = sum(item["done"].get("type") == "not_found" for item in no_answer) / max(1, len(no_answer))
    uncited = [item for item in answered if item["done"].get("type") != "not_found" and not item["citations"]]
    grounded = []
    for item in answered:
        type_ok = item["done"].get("type") in {"answered", "partial"}
        facts_ok = all(fact.casefold() in item["answer"].casefold() for fact in item["expected_facts"])
        docs_ok = not item["expected_documents"] or any(
            citation.get("document_name") in item["expected_documents"]
            for citation in item["citations"]
        )
        grounded.append(type_ok and facts_ok and docs_ok and bool(item["citations"]))
    lang_accuracy = {}
    for lang in {"vi", "en"}:
        subset = [item for item in answered if item["lang"] == lang]
        lang_accuracy[lang] = sum(
            item["done"].get("type") in {"answered", "partial"} and bool(item["citations"])
            for item in subset
        ) / max(1, len(subset))
    latencies = [item["latency_ms"] for item in results]
    return {
        "grounded_accuracy": sum(grounded) / max(1, len(grounded)),
        "not_found_recall": not_found_recall,
        "false_not_found_rate": sum(item["done"].get("type") == "not_found" for item in answered) / max(1, len(answered)),
        "uncited_rate": len(uncited) / max(1, len(answered)),
        "citation_page_accuracy": None,
        "accuracy_by_lang": lang_accuracy,
        "retrieval_top_score": {"p10": None, "p50": None, "p90": None},
        "latency_ms": {
            "p10": percentile(latencies, 0.10),
            "p50": percentile(latencies, 0.50),
            "p90": percentile(latencies, 0.90),
        },
    }


def write_html(report: dict, output: Path) -> None:
    rows = "".join(
        f"<tr><td>{html.escape(item['id'])}</td><td>{html.escape(item['done'].get('type', 'error'))}</td>"
        f"<td>{len(item['citations'])}</td><td>{item['latency_ms']}</td></tr>"
        for item in report["results"]
    )
    body = json.dumps(report["metrics"], ensure_ascii=False, indent=2)
    output.with_suffix(".html").write_text(
        f"<html><body><h1>RAG evaluation</h1><pre>{html.escape(body)}</pre>"
        f"<table><tr><th>ID</th><th>Result</th><th>Citations</th><th>Latency ms</th></tr>{rows}</table></body></html>",
        encoding="utf-8",
    )


async def main(args: argparse.Namespace) -> None:
    items = load_items(args.datasets)
    results = [await ask(args.base_url, args.cookie, args.csrf_token, item) for item in items]
    report = {
        "run_id": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt_version": args.prompt_version,
        "model_id": args.model_id,
        "embedding_model": args.embedding_model,
        "chunk_size_tokens": args.chunk_size_tokens,
        "tau": args.tau,
        "metrics": evaluate(results),
        "results": results,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.html:
        write_html(report, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--cookie", default="")
    parser.add_argument(
        "--csrf-token", default="", help="Giá trị header X-CSRF-Token (lấy từ GET /me)"
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--prompt-version", default="v2")
    parser.add_argument("--model-id", default="configured")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--chunk-size-tokens", type=int, default=500)
    parser.add_argument("--tau", type=float, default=0.15)
    asyncio.run(main(parser.parse_args()))
