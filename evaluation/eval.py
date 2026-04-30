"""
RAGAS evaluation pipeline.

Evaluates the RAG system on a JSONL dataset using:
  - faithfulness (answer grounded in context)
  - answer_relevancy (answer addresses the question)
  - context_recall (context covers the ground truth)

Usage:
    python eval.py --dataset dataset/sample_eval.jsonl --output report.json
    python eval.py  # uses defaults
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import click
import httpx
import structlog
from datasets import Dataset
from dotenv import load_dotenv
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_recall, faithfulness
from rich.console import Console
from rich.table import Table

load_dotenv()
logger = structlog.get_logger(__name__)
console = Console()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


async def call_ask_endpoint(query: str, client: httpx.AsyncClient) -> dict:
    """Call the /api/v1/ask endpoint and return the response."""
    try:
        resp = await client.post(
            f"{BACKEND_URL}/api/v1/ask",
            json={"query": query, "top_k": 5},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("eval.ask_failed", query=query[:80], error=str(exc))
        return {"answer": "", "citations": []}


async def build_ragas_dataset(
    eval_samples: list[dict],
    use_live_endpoint: bool,
) -> Dataset:
    """
    Build a HuggingFace Dataset for RAGAS evaluation.

    If use_live_endpoint is True, queries the running backend for answers.
    Otherwise, uses placeholder answers for offline testing.
    """
    questions, answers, ground_truths, contexts_list = [], [], [], []

    if use_live_endpoint:
        async with httpx.AsyncClient() as client:
            for sample in eval_samples:
                result = await call_ask_endpoint(sample["question"], client)
                questions.append(sample["question"])
                answers.append(result.get("answer", ""))
                ground_truths.append(sample["ground_truth"])
                contexts_list.append(sample["contexts"])
    else:
        for sample in eval_samples:
            questions.append(sample["question"])
            answers.append(sample.get("answer", sample["ground_truth"]))
            ground_truths.append(sample["ground_truth"])
            contexts_list.append(sample["contexts"])

    return Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths,
        }
    )


def load_dataset(path: Path) -> list[dict]:
    """Load JSONL evaluation dataset."""
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    logger.info("eval.dataset_loaded", path=str(path), count=len(samples))
    return samples


def print_report(report: dict) -> None:
    """Print evaluation results as a Rich table."""
    table = Table(title="RAGAS Evaluation Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Threshold", justify="right")
    table.add_column("Status")

    thresholds = {
        "faithfulness": float(os.environ.get("EVAL_FAITHFULNESS_THRESHOLD", "0.85")),
        "answer_relevancy": float(os.environ.get("EVAL_RELEVANCE_THRESHOLD", "0.80")),
        "context_recall": 0.70,
    }

    all_pass = True
    for metric, score in report["metrics"].items():
        threshold = thresholds.get(metric, 0.0)
        passed = score >= threshold
        all_pass = all_pass and passed
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        table.add_row(metric, f"{score:.4f}", f"{threshold:.2f}", status)

    console.print(table)
    if all_pass:
        console.print("\n[bold green]✓ All metrics above threshold — CI gate PASSED[/bold green]")
    else:
        console.print("\n[bold red]✗ One or more metrics below threshold — CI gate FAILED[/bold red]")

    return all_pass


@click.command()
@click.option(
    "--dataset",
    type=click.Path(exists=True, path_type=Path),
    default="dataset/sample_eval.jsonl",
    show_default=True,
    help="Path to JSONL evaluation dataset",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default="report.json",
    show_default=True,
    help="Path to write JSON report",
)
@click.option(
    "--live",
    is_flag=True,
    default=False,
    help="Query the live backend endpoint for answers",
)
def main(dataset: Path, output: Path, live: bool) -> None:
    """
    Run RAGAS evaluation on the dataset and write a JSON report.

    Exits with code 1 if any metric is below the defined threshold.
    """
    console.print(f"[bold]Loading dataset:[/bold] {dataset}")
    samples = load_dataset(dataset)

    console.print("[bold]Building RAGAS dataset...[/bold]")
    ragas_dataset = asyncio.run(build_ragas_dataset(samples, use_live_endpoint=live))

    console.print("[bold]Running RAGAS evaluation...[/bold]")
    result = evaluate(
        ragas_dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
    )

    metrics_dict = {
        "faithfulness": float(result["faithfulness"]),
        "answer_relevancy": float(result["answer_relevancy"]),
        "context_recall": float(result["context_recall"]),
    }

    report = {
        "dataset": str(dataset),
        "sample_count": len(samples),
        "metrics": metrics_dict,
    }

    # Write JSON report
    output.write_text(json.dumps(report, indent=2))
    console.print(f"\n[dim]Report written to {output}[/dim]")

    passed = print_report(report)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
