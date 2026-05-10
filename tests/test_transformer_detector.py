from src.pipeline.transformer_detector import TransformerDetector


def test_positive_score_prefers_label_1() -> None:
    detector = object.__new__(TransformerDetector)

    score = detector._positive_score(
        [
            {"label": "LABEL_0", "score": 0.2},
            {"label": "LABEL_1", "score": 0.8},
        ]
    )

    assert score == 0.8


def test_positive_score_supports_named_injection_label() -> None:
    detector = object.__new__(TransformerDetector)

    score = detector._positive_score(
        [
            {"label": "BENIGN", "score": 0.35},
            {"label": "INJECTION", "score": 0.65},
        ]
    )

    assert score == 0.65
