from src.evaluation.writers import resolve_report_dir


def test_resolve_report_dir_uses_output_dir_for_legacy_config(tmp_path) -> None:
    report_dir = resolve_report_dir({"reports": {"output_dir": str(tmp_path / "legacy")}})

    assert report_dir == tmp_path / "legacy"
    assert report_dir.exists()


def test_resolve_report_dir_uses_experiment_name(tmp_path) -> None:
    report_dir = resolve_report_dir(
        {
            "reports": {
                "output_dir": str(tmp_path),
                "experiment_name": "synthetic_500_ml",
            }
        }
    )

    assert report_dir == tmp_path / "experiments" / "synthetic_500_ml"
    assert report_dir.exists()
