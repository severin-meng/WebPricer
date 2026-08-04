import json
import random
import numpy as np
import itertools
import pandas as pd
from calendar import monthrange
from datetime import date, timedelta
from typing import Sequence
import csv


def generate_cliquet(
    start_date_iso: str = "2026-09-15",
    fixing_period_days: int = 30,
) -> str:
    """
    Generate approximately equidistant fixing dates from the input date
    through a maturity 365 days later.

    Both the start date and maturity date are included.
    """
    if fixing_period_days <= 0:
        raise ValueError("fixing_period_days must be positive")

    start_date = date.fromisoformat(start_date_iso)
    maturity_date = start_date + timedelta(days=365)

    # Choose the closest integer number of fixing intervals.
    number_of_intervals = max(1, round(365 / fixing_period_days))

    dates = [
        start_date
        + timedelta(
            days=round(i * 365 / number_of_intervals)
        )
        for i in range(1, number_of_intervals + 1)
    ]
    fixing_dates = [fixing_date.isoformat() for fixing_date in dates]

    product = {
        "name": f"Cliquet_{fixing_period_days}",
        "type": "Cliquet",
        "exercise_date": fixing_dates[-1],
        "settle_date": fixing_dates[-1],
        "fixing_dates": fixing_dates,
        "past_fixings": [],
        "underlyings": "S1"
    }

    return json.dumps(product, indent=2)


if __name__ == "__main__":
    days = [7, 14, 31, 61, 91, 182]
    for day in days:
        cliquet = generate_cliquet(fixing_period_days=day)
        with open(f"experiments/cliquets/products_{day}.json", "w", encoding="utf-8") as json_file:
            json_file.write(cliquet)
