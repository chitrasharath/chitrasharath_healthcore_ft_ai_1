"""Pattern-recovery: seasonal factors lowest in Jul–Aug, highest in Oct–Dec."""

from __future__ import annotations

import pandas as pd

from data.forecast.clean import clean_sales, load_raw, split_train_test
from data.forecast.models_statsforecast import seasonal_factors_from_ets


def test_ets_seasonal_factors_recover_flu_and_summer_pattern() -> None:
    cleaned = clean_sales(load_raw())
    train, _test = split_train_test(cleaned)
    factors = seasonal_factors_from_ets(train)

    low = min(factors[7], factors[8])
    high = max(factors[10], factors[11], factors[12])
    summer_avg = (factors[7] + factors[8]) / 2
    flu_avg = (factors[10] + factors[11] + factors[12]) / 3

    assert flu_avg > summer_avg
    assert high > low
    # Flu months should sit above the annual mean of factors; summer below
    mean_factor = sum(factors.values()) / len(factors)
    assert flu_avg >= mean_factor * 0.98
    assert summer_avg <= mean_factor * 1.02
