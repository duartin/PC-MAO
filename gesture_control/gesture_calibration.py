"""Robust calibration helpers for gesture distance thresholds."""
from statistics import median


MIN_CALIBRATION_SAMPLES = 10


def estimate_pinch_threshold(pinch_samples, neutral_samples, minimum=0.12,
                             maximum=0.60, min_separation=0.06):
    """Estimate a normalized pinch threshold between held-pinch and neutral samples.

    Values are expected to be thumb-to-middle fingertip distance divided by
    palm width. A median is used to reduce occasional tracking outliers.
    """
    pinch = [float(value) for value in pinch_samples]
    neutral = [float(value) for value in neutral_samples]
    if len(pinch) < MIN_CALIBRATION_SAMPLES or len(neutral) < MIN_CALIBRATION_SAMPLES:
        raise ValueError(
            f"Calibração insuficiente: capture ao menos {MIN_CALIBRATION_SAMPLES} amostras em cada pose."
        )
    if any(value < 0 for value in pinch + neutral):
        raise ValueError("As distâncias da calibração não podem ser negativas")
    pinch_median = median(pinch)
    neutral_median = median(neutral)
    separation = neutral_median - pinch_median
    if separation < min_separation:
        raise ValueError(
            "As poses ficaram parecidas demais. Repita a pinça e a mão relaxada com a palma visível."
        )
    threshold = (pinch_median + neutral_median) / 2.0
    if not minimum <= threshold <= maximum:
        raise ValueError(
            f"Limiar calculado ({threshold:.2f}) fora da faixa permitida ({minimum:.2f}–{maximum:.2f})."
        )
    return threshold
