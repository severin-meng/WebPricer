import json
import numpy as np


def generate_multi_ssvi_markets(spots):
    markets = []
    for idx, spot in enumerate(spots):
        market = {
            "name": f"Market_{idx}",
            "assets": [
                {"name": "S1", "spot": 1.0, "div_yield": 0.00, "ivs": {
                    "type": "SSVI_PowerLaw", "vol": 0.2, "rho": -0.7, "eta": 0.9, "gamma": 0.4}
                 },
                {"name": "S2", "spot": 1.0, "div_yield": 0.00, "ivs": {
                    "type": "SSVI_PowerLaw", "vol": 0.2, "rho": -0.7, "eta": 0.9, "gamma": 0.4}
                 },
                {"name": "S3", "spot": spot, "div_yield": 0.00, "ivs": {
                    "type": "SSVI_PowerLaw", "vol": 0.2, "rho": -0.7, "eta": 0.9, "gamma": 0.4}
                 }
            ],
            "rate": 0.03,
            "correlation": {"S2_S1": 0.8, "S3_S1": 0.2, "S3_S2": 0.2}
        }
        markets.append(market)

    data = json.dumps(markets, indent=2)
    with open(f"experiments/autocalls/markets.json", "w", encoding="utf-8") as json_file:
        json_file.write(data)


if __name__ == "__main__":
    spots = np.linspace(0.6, 1.4, 100)
    generate_multi_ssvi_markets(spots)