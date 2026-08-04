import json
import random
import numpy as np
import itertools
import pandas as pd
from calendar import monthrange
from datetime import date, timedelta
from typing import Sequence
import csv


def generate_geometric_asians(
    start_date_iso: str = "2026-09-15",
    fixing_period_days: list[int] = [7],
    strike: float = 1.0
) -> str:
    """
    Generate approximately equidistant fixing dates from the input date
    through a maturity 365 days later.

    Both the start date and maturity date are included.
    """
    if any([fixing_days <= 0 for fixing_days in fixing_period_days]):
        raise ValueError("fixing_period_days must be positive")

    start_date = date.fromisoformat(start_date_iso)
    maturity_date = (start_date + timedelta(days=365)).isoformat()
    products = []

    for fixing_days in fixing_period_days:
        # Choose the closest integer number of fixing intervals.
        number_of_intervals = max(1, round(365 / fixing_days))

        dates = [
            start_date
            + timedelta(
                days=round(i * 365 / number_of_intervals)
            )
            for i in range(1, number_of_intervals + 1)
        ]
        fixing_dates = [fixing_date.isoformat() for fixing_date in dates]

        product = {
            "name": f"AsianGeom_{fixing_days}",
            "type": "Asian",
            "strike": strike,
            "exercise_date": maturity_date,
            "settle_date": maturity_date,
            "fixing_dates": fixing_dates,
            "past_fixings": [],
            "is_arithmetic": False,
            "underlyings": "S1"
        }
        products.append(product)

    return json.dumps(products, indent=2)


if __name__ == "__main__":
    days = [1, 3, 7, 14, 31, 61, 91, 182]
    geomAsians = generate_geometric_asians(fixing_period_days=days)
    with open(f"experiments/asians/products.json", "w", encoding="utf-8") as json_file:
        json_file.write(geomAsians)
