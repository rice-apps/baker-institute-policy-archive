"""Evaluate one case using an itemizer or a saved result."""

import argparse
import json
from dataclasses import asdict
from importlib import import_module
from pathlib import Path

from ..models import Page
from .metrics import evaluate


METHODS = {
    "heuristic": ("itemization.heuristic", "HeuristicItemizer"),
    "llm": ("itemization.llm", "LLMItemizer"),
}


def run_itemizer(method, pages):
    module_name, class_name = METHODS[method]
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            raise ValueError(f"{method} is not implemented yet. Add {module_name.replace('.', '/')}.py with {class_name}.") from error
        raise ValueError(f"Missing itemizer dependency: {error.name}") from error
    itemizer = getattr(module, class_name)()
    return asdict(itemizer.itemize([Page(**page) for page in pages]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="case_001", help="Case ID (default: case_001)")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--method", choices=METHODS, help="Run an itemizer on the OCR input")
    source.add_argument("--predictions", type=Path, help="Evaluate a saved itemizer result instead")
    args = parser.parse_args()
    cases = Path(__file__).parent / "cases"

    try:
        pages = json.loads((cases / f"{args.case}_pages.json").read_text())
        expected = json.loads((cases / f"{args.case}_expected.json").read_text())
        predicted = run_itemizer(args.method, pages) if args.method else json.loads(args.predictions.read_text())
        report = evaluate(pages, expected, predicted)
    except NotImplementedError:
        parser.exit(2, "Evaluation failed: The itemizer's itemize() method is not implemented yet.\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(2, f"Evaluation failed: {error}\n")

    print(json.dumps({"case": args.case, **report}, indent=2))


if __name__ == "__main__":
    main()
