import json
import random
import numpy as np
import itertools
import pandas as pd
from calendar import monthrange
from datetime import date
from typing import Sequence
import csv


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
) -> tuple[str, list[str], list[list[float]]]:
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
    param_keys = ["name", "initial_fixing_1", "initial_fixing_2", "initial_fixing_3", "down_in", "autocall_barrier", "maturity_months", "is_euro_barrier", "dist_to_barrier", "dist_to_autoc"]
    param_data = []


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

        init_fixings = [
                round(rng.uniform(initial_fixings_min, initial_fixings_max), 3)
                for _ in range(3)
            ]

        product = {
            "name": f"{name_prefix}_{index}",
            "type": "Autocall",
            "asset_names": ["S1", "S2", "S3"],
            "initial_fixings": init_fixings,
            "strike": 1.0,
            "down_in": round(rng.uniform(down_in_min, min(1 / max(init_fixings), down_in_max)), 3),  # down in barrier should be below current min - i.e. no present breach
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

        dist_to_barrier = 1 - product["down_in"] * max(init_fixings)  # assuming spot is 1, then perf is 1 / init_fixing
        dist_to_autocall = product["autocall_barrier"] * max(init_fixings) - 1
        # dist = (worst - abs_barrier) / worst = 1 - product["down_in"] * max(init_fixings)
        params = [product["name"]] + product["initial_fixings"] + [product["down_in"], product["autocall_barrier"], maturity_months, product["is_euro_barrier"], dist_to_barrier, dist_to_autocall]
        param_data.append(params)


    return json.dumps(products, indent=2), param_keys, param_data


def _stratified_unit(
    n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate one randomized point in each of n equal strata of [0, 1)."""
    return (rng.permutation(n) + rng.random(n)) / n


def sample_autocall_portfolio(
    n_products: int = 200,
    seed: int = 1234,
    max_relative_name_spread: float = 0.35,
    min_di_relative_gap: float = 0.035,
) -> pd.DataFrame:
    """
    Generate a stratified portfolio of three-name worst-of autocallables.

    Assumptions
    -----------
    - Current spots are normalized to 1.
    - Strike is normalized to 1.
    - performance_i = current_spot / initial_fixing_i
                    = 1 / initial_fixing_i.
    - The down-in barrier is expressed relative to the initial fixing.
    """
    if n_products <= 0:
        raise ValueError("n_products must be positive.")

    if not 0.0 < min_di_relative_gap < 0.10:
        raise ValueError(
            "min_di_relative_gap should lie between 0 and 0.10."
        )

    rng = np.random.default_rng(seed)

    # Extra resolution at short maturities, where barrier gamma is most unstable.
    maturity_edges = np.array(
        [1.0, 3.0, 6.0, 12.0, 24.0, 36.0]
    )

    # Conditional down-in barrier-position strata.
    # Equal counts in these intervals oversample q close to one.
    di_q_edges = np.array(
        [0.00, 0.50, 0.75, 0.90, 0.97, 1.00]
    )

    cells = list(
        itertools.product(
            ["down", "up"],
            [False, True],
            range(len(maturity_edges) - 1),
            range(len(di_q_edges) - 1),
        )
    )

    # There are 2 * 2 * 5 * 5 = 100 cells.
    n_cells = len(cells)
    full_repetitions, remainder = divmod(n_products, n_cells)

    rows = cells * full_repetitions

    # For portfolio sizes not divisible by 100, select additional cells randomly.
    if remainder:
        selected = rng.choice(
            n_cells,
            size=remainder,
            replace=False,
        )
        rows.extend(cells[index] for index in selected)

    rng.shuffle(rows)

    portfolio = pd.DataFrame(
        rows,
        columns=[
            "direction",
            "continuous_down_in",
            "maturity_bucket",
            "di_position_bucket",
        ],
    )

    # ---------------------------------------------------------------
    # Worst-of current performance
    # ---------------------------------------------------------------

    worst_performance = np.empty(n_products)

    for direction, lower, upper in [
        ("down", 0.5, 1.0),
        ("up", 1.0, 2.0),
    ]:
        indices = np.flatnonzero(
            portfolio["direction"].to_numpy() == direction
        )

        u = _stratified_unit(len(indices), rng)

        # Uniform in logarithmic performance.
        worst_performance[indices] = np.exp(
            np.log(lower)
            + u * (np.log(upper) - np.log(lower))
        )

    portfolio["worst_performance"] = worst_performance

    # ---------------------------------------------------------------
    # Three underlying performances
    # ---------------------------------------------------------------

    performances = np.empty((n_products, 3))

    for row, worst in enumerate(worst_performance):
        # Limit dispersion between basket constituents.
        max_log_gap = min(
            np.log1p(max_relative_name_spread),
            np.log(2.0 / worst),
        )

        # Beta distribution places the other names reasonably close
        # to the worst name while still allowing basket dispersion.
        gaps = np.sort(
            rng.beta(2.0, 5.0, size=2) * max_log_gap
        )

        basket = np.array(
            [
                worst,
                worst * np.exp(gaps[0]),
                worst * np.exp(gaps[1]),
            ]
        )

        # Avoid assigning the same underlying as the worst in every product.
        rng.shuffle(basket)
        performances[row] = basket

    for underlying in range(3):
        number = underlying + 1

        portfolio[f"performance_{number}"] = (
            performances[:, underlying]
        )

        portfolio[f"initial_fixing_{number}"] = (
            1.0 / performances[:, underlying]
        )

    # ---------------------------------------------------------------
    # Time to expiry
    # ---------------------------------------------------------------

    maturity_indices = portfolio["maturity_bucket"].to_numpy()

    maturity_lower = maturity_edges[maturity_indices]
    maturity_upper = maturity_edges[maturity_indices + 1]

    portfolio["months_to_expiry"] = (
        maturity_lower
        + rng.random(n_products)
        * (maturity_upper - maturity_lower)
    )

    portfolio["years_to_expiry"] = (
        portfolio["months_to_expiry"] / 12.0
    )

    # ---------------------------------------------------------------
    # Down-in barrier
    # ---------------------------------------------------------------

    # Strictly separate current worst performance and down-in barrier.
    maximum_down_in = np.minimum(
        0.90,
        worst_performance - min_di_relative_gap,
    )

    if np.any(maximum_down_in <= 0.45):
        raise RuntimeError(
            "No feasible down-in barrier for at least one product."
        )

    di_bucket = portfolio["di_position_bucket"].to_numpy()

    q_lower = di_q_edges[di_bucket]
    q_upper = di_q_edges[di_bucket + 1]

    q = (
        q_lower
        + rng.random(n_products) * (q_upper - q_lower)
    )

    down_in_barrier = (
        0.45
        + q * (maximum_down_in - 0.45)
    )

    portfolio["down_in_barrier"] = down_in_barrier

    # ---------------------------------------------------------------
    # Autocall barrier
    # ---------------------------------------------------------------

    # Equal counts across five absolute barrier intervals:
    # [0.90, 0.94), ..., [1.06, 1.10].
    autocall_bucket = np.resize(
        np.arange(5),
        n_products,
    )
    rng.shuffle(autocall_bucket)

    portfolio["autocall_bucket"] = autocall_bucket

    portfolio["autocall_barrier"] = (
        0.90
        + (
            autocall_bucket
            + rng.random(n_products)
        )
        * (0.20 / 5.0)
    )

    # ---------------------------------------------------------------
    # Explanatory variables for later analysis
    # ---------------------------------------------------------------

    # perf = 1 / init_fix
    # barr dist = (1 - di_barr*init_fix) / 1 = init_fix * (1 / init_fix - di_barr) / 1 = (perf - di_barr) / (perf)
    portfolio["di_distance"] = (
        worst_performance - down_in_barrier
    ) / worst_performance

    portfolio["autocall_distance"] = (
        portfolio["autocall_barrier"].to_numpy() - worst_performance
    ) / worst_performance

    portfolio["di_log_distance"] = np.log(
        worst_performance / down_in_barrier
    )

    portfolio["autocall_log_distance"] = np.log(
        worst_performance
        / portfolio["autocall_barrier"].to_numpy()
    )

    # ---------------------------------------------------------------
    # Integrity checks
    # ---------------------------------------------------------------

    fixing_columns = [
        "initial_fixing_1",
        "initial_fixing_2",
        "initial_fixing_3",
    ]

    assert portfolio[fixing_columns].to_numpy().min() >= 0.5
    assert portfolio[fixing_columns].to_numpy().max() <= 2.0

    assert portfolio["down_in_barrier"].between(
        0.45,
        0.90,
    ).all()

    assert (
        portfolio["down_in_barrier"]
        < portfolio["worst_performance"]
    ).all()

    assert portfolio["autocall_barrier"].between(
        0.90,
        1.10,
    ).all()

    assert portfolio["months_to_expiry"].between(
        1.0,
        36.0,
    ).all()

    portfolio.insert(0, "name", [f"Autocall_{idx}" for idx in portfolio.index])

    return portfolio


def portfolio_to_json(portfolio, valuation_date = "2026-09-15"):
    products = []
    valuation = date.fromisoformat(valuation_date)
    for row in portfolio.iterrows():
        data = row[1]
        maturity_months = int(data.months_to_expiry)
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
        prod = {
            "name": data["name"],
            "type": "Autocall",
            "asset_names": ["S1", "S2", "S3"],
            "initial_fixings": [data["initial_fixing_1"], data["initial_fixing_2"], data["initial_fixing_3"]],
            "strike": 1.0,
            "down_in": data["down_in_barrier"],
            "autocall_barrier": data["autocall_barrier"],
            "coupon_amount": 0.04,
            "coupon_dates": coupon_dates,
            "autocall_dates": autocall_dates,
            "exercise_date": exercise_date.isoformat(),
            "monitor_period": 0.009615384615384616,
            "smooth": 0.01,
            "is_euro_barrier": not data["continuous_down_in"]
        }

        products.append(prod)
    return json.dumps(products, indent=2)


if __name__ == "__main__":
    """
    products_json, param_keys, param_data = generate_products(
        number_of_products=200,
        initial_fixings_range=(0.5, 2.0),
        down_in_range=(0.45, 0.9),
        autocall_barrier_range=(0.9, 1.1),
        exercise_months_range=(1, 36),
        seed=42,  # Remove or change for different results.
    )
    # random: initial fixings, downIn Barrier, autocall Barrier, exercise runtime and subsequently the remaining call dates, euro vs american

    print(products_json)

    # Optional: write the JSON to a file.

    with open("experiments/autocalls/products.json", "w", encoding="utf-8") as json_file:
        json_file.write(products_json)

    with open("experiments/autocalls/products_params.csv", "w", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(param_keys)
        writer.writerows(param_data)"""

    portfolio = sample_autocall_portfolio(
        n_products=200,
        seed=20260803,
        min_di_relative_gap=0.035,  # worst is at least 3.5% above the DI barrier so I can bump with 3% spot shift without crossing
    )
    portfolio.to_csv("experiments/autocalls/products_params_v4.csv", index=False)
    ptf_json = portfolio_to_json(portfolio)
    with open("experiments/autocalls/products_v4.json", "w", encoding="utf-8") as json_file:
        json_file.write(ptf_json)