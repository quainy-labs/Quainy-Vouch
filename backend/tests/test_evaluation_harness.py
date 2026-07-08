from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_evaluation_harness_runs_golden_cases(tmp_path: Path):
    output = tmp_path / "eval_report.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_eval.py"),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output.read_text())

    assert "pass_rate" in completed.stdout
    assert report["summary"]["total"] == 3
    assert report["summary"]["failed"] == 0
    assert {result["kind"] for result in report["results"]} == {
        "source_backed_flow",
        "unsupported_metric_block",
        "duplicate_memory",
    }
