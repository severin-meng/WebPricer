import json
import random
from calendar import monthrange
from datetime import date
from typing import Sequence


def shift_months(input_date: date, months: int) -> date:
    """Shift a date by a whole number of months."""
    total_months = input_date.year * 12 + input_date.month - 1 + months
    year, month_index = divmod(total_months, 12)
    month = month_index + 1
    day = min(input_date.day, monthrange(year, month)[1])

    return date(year, month, day)


def generate_products(
    number_of_products: int,
    name_prefix: str = "Autocall",
    initial_fixings_range: Sequence[float] = (0.5, 2.0),
    down_in_range: Sequence[float] = (0.45, 0.9),
    autocall_barrier_range: Sequence[float] = (0.9, 1.1),
    exercise_months_range: Sequence[int] = (6, 36),
    valuation_date: str = "2026-09-15",
    seed: int | None = None,
) -> str:
    """
    Generate randomized product parameters and return them as a JSON list.

    Continuous numerical parameters use uniform distributions.
    Exercise dates use a uniformly selected whole-month maturity.
    """
    if number_of_products < 1:
        raise ValueError("number_of_products must be at least 1.")

    rng = random.Random(seed)
    valuation = date.fromisoformat(valuation_date)

    initial_fixings_min, initial_fixings_max = initial_fixings_range
    down_in_min, down_in_max = down_in_range
    autocall_min, autocall_max = autocall_barrier_range
    exercise_months_min, exercise_months_max = exercise_months_range

    products = []

    for index in range(1, number_of_products + 1):
        maturity_months = rng.randint(
            exercise_months_min,
            exercise_months_max,
        )
        exercise_date = shift_months(valuation, maturity_months)

        # Generate quarterly dates backwards from the exercise date.
        coupon_dates_descending = []
        current_date = exercise_date

        while current_date > valuation:
            coupon_dates_descending.append(current_date)
            current_date = shift_months(current_date, -3)

        # Every second coupon date, skipping the exercise date
        autocall_dates_descending = coupon_dates_descending[::2][1:]

        # Store dates chronologically in the output.
        coupon_dates = [
            value.isoformat()
            for value in reversed(coupon_dates_descending)
        ]
        autocall_dates = [
            value.isoformat()
            for value in reversed(autocall_dates_descending)
        ]

        product = {
            "name": f"{name_prefix}_{index}",
            "type": "Autocall",
            "asset_names": ["S1", "S2", "S3"],
            "initial_fixings": [
                round(rng.uniform(initial_fixings_min, initial_fixings_max), 6)
                for _ in range(3)
            ],
            "strike": 1.0,
            "down_in": round(rng.uniform(down_in_min, down_in_max), 6),
            "autocall_barrier": round(
                rng.uniform(autocall_min, autocall_max),
                6,
            ),
            "coupon_amount": 0.02,
            "coupon_dates": coupon_dates,
            "autocall_dates": autocall_dates,
            "exercise_date": exercise_date.isoformat(),
            "monitor_period": 0.009615384615384616,
            "smooth": 0.01,
            "is_euro_barrier": rng.choice([True, False]),
        }

        products.append(product)

    return json.dumps(products, indent=2)


if __name__ == "__main__":
    products_json = generate_products(
        number_of_products=5,
        initial_fixings_range=(0.5, 2.0),
        down_in_range=(0.45, 0.9),
        autocall_barrier_range=(0.9, 1.1),
        exercise_months_range=(6, 36),
        seed=42,  # Remove or change for different results.
    )
    # random: initial fixings, downIn Barrier, autocall Barrier, exercise runtime and subsequently the remaining call dates, euro vs american

    print(products_json)

    # Optional: write the JSON to a file.
    with open("experiments/autocalls/products.json", "w", encoding="utf-8") as json_file:
        json_file.write(products_json)