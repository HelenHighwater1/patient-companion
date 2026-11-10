from patient_companion.eval.run import run_eval


def test_mock_eval_runs_and_reports():
    summary = run_eval(mock=True, skip_rewrite=False)
    assert summary["n_questions"] > 0
    # Refusal questions must all refuse — that's a safety property, mock or not.
    assert summary["refusal_accuracy"] == 1.0
