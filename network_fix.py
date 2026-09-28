"""Standalone network adjustment script.

This does not modify the existing project files.
It makes the node order deterministic, connects markets by name,
handles multiple equilibrium intervals more safely, and keeps a
separate adjusted price/quantity pass for surplus comparison.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np

from load_data import load_dfs
from markets import Market
from constants import Constants


MARKET_ORDER = [
    "dk",
    "lv",
    "ger",
    "fr",
    "se",
    "no",
    "nl",
    "at",
    "be",
    "bg",
    "fi",
    "ro",
]


# Same topology as the hard-coded connections in main.py, but by name.
CONNECTED_EDGES = [
    ("at", "bg"),
    ("at", "fr"),
    ("fr", "be"),
    ("be", "nl"),
    ("nl", "dk"),
    ("ger", "dk"),
    ("dk", "no"),
    ("nl", "se"),
    ("se", "fi"),
    ("se", "lv"),
    ("fi", "lv"),
]


COORDS = {
    "at": (48.2085, 16.3721),
    "be": (50.8505, 4.3488),
    "ger": (52.5200, 13.4050),
    "fr": (48.8566, 2.3522),
    "nl": (52.37, 4.89),
    "dk": (55.6761, 12.5683),
    "fi": (60.17, 24.94),
    "no": (59.91, 10.75),
    "se": (59.33, 18.06),
    "bg": (42.73, 25.49),
    "lv": (59.437, 24.754),
    "ro": (44.4268, 26.1025),
}


def build_problem() -> Tuple[Constants, Dict[str, Market]]:
    dfs = load_dfs()
    problem = Constants()
    problem.nodes = []

    markets: Dict[str, Market] = {}

    for name in MARKET_ORDER:
        if name not in dfs:
            continue

        market = Market(name, dfs[name])
        market.find_price()
        markets[name] = market
        problem.nodes.append(market)

    for market in problem.nodes:
        if market.name in COORDS:
            market.lat, market.lon = COORDS[market.name]

    for i in problem.nodes:
        for j in problem.nodes:
            if i.name == j.name:
                continue
            if i.name in {"pl", "ro"} or j.name in {"pl", "ro"}:
                continue
            problem.cost_to_create(i, j)

    for left, right in CONNECTED_EDGES:
        if left in markets and right in markets:
            problem.connect(markets[left], markets[right])

    return problem, markets


def contiguous_segments(mask: np.ndarray) -> List[Tuple[int, int]]:
    segments: List[Tuple[int, int]] = []
    start = None
    for idx, flag in enumerate(mask):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            segments.append((start, idx - 1))
            start = None
    if start is not None:
        segments.append((start, len(mask) - 1))
    return segments


def network_excess(problem: Constants, market: Market, price: float, prices_by_name: Dict[str, float]) -> float:
    i_idx = problem.index_dict.get(market.name)
    if i_idx is None:
        return 0.0

    exports = 0.0
    imports = 0.0

    for other in problem.nodes:
        if other.name in {"ro", "pl"} or other.name == market.name:
            continue

        j_idx = problem.index_dict.get(other.name)
        if j_idx is None:
            continue

        if problem.connection_matrix[i_idx][j_idx] != 1:
            continue

        loss = (
            problem.transmission_loss_matrix[i_idx][j_idx]
            + problem.transmission_loss_matrix[j_idx][i_idx]
        ) / 2.0

        other_price = prices_by_name[other.name]

        # Use the candidate price here, not the original autarky price.
        # Otherwise a market can move even when the final candidate state
        # would not make the transfer profitable.
        if price < other_price * loss:
            exports += (1.0 / loss) * (
                other.inverse_supply(other_price) - other.inverse_demand(other_price)
            )

        if other_price < price * loss:
            imports += loss * (
                other.inverse_demand(other_price) - other.inverse_supply(other_price)
            )

    return float(market.inverse_supply(price) + exports - market.inverse_demand(price) - imports)


def has_active_trade(problem: Constants, market: Market, prices_by_name: Dict[str, float]) -> bool:
    i_idx = problem.index_dict.get(market.name)
    if i_idx is None:
        return False

    current_price = prices_by_name[market.name]

    for other in problem.nodes:
        if other.name in {"ro", "pl"} or other.name == market.name:
            continue

        j_idx = problem.index_dict.get(other.name)
        if j_idx is None:
            continue

        if problem.connection_matrix[i_idx][j_idx] != 1:
            continue

        loss = (
            problem.transmission_loss_matrix[i_idx][j_idx]
            + problem.transmission_loss_matrix[j_idx][i_idx]
        ) / 2.0

        other_price = prices_by_name[other.name]

        if current_price < other_price * loss or other_price < current_price * loss:
            return True

    return False


def frozen_markets(problem: Constants, prices_by_name: Dict[str, float]) -> set[str]:
    """Markets with no profitable transfer on any incident edge.

    These markets remain at autarky price because the network does not give
    them a direct reason to move.
    """

    frozen: set[str] = set()
    for market in problem.nodes:
        if market.name in {"ro", "pl"}:
            continue
        if not has_active_trade(problem, market, prices_by_name):
            frozen.add(market.name)
    return frozen


def solve_network_prices(problem: Constants, markets: Dict[str, Market], max_iter: int = 25) -> None:
    prices_by_name = {name: market.price for name, market in markets.items()}
    frozen = frozen_markets(problem, prices_by_name)

    for _ in range(max_iter):
        updated = dict(prices_by_name)

        for market in problem.nodes:
            if market.name in {"ro", "pl"}:
                continue

            # If the market never has a profitable direct transfer in the
            # autarky snapshot, keep it fixed at its autarky equilibrium.
            if market.name in frozen:
                updated[market.name] = float(market.price)
                continue

            low = max(float(market.supply["price"].min()), float(market.demand["price"].min()), 0.0)
            high = min(float(market.supply["price"].max()), float(market.demand["price"].max()))
            if not np.isfinite(low) or not np.isfinite(high) or low >= high:
                updated[market.name] = float(market.price)
                continue

            grid = np.linspace(low, high, 2501)
            excess = np.array([
                network_excess(problem, market, float(p), prices_by_name) for p in grid
            ])

            near_zero = np.abs(excess) <= 1e-8
            zero_segments = contiguous_segments(near_zero)
            if zero_segments:
                best_start, best_end = max(zero_segments, key=lambda seg: seg[1] - seg[0])
                chosen = float((grid[best_start] + grid[best_end]) / 2.0)
            else:
                signs = np.sign(excess)
                sign_change = np.where(signs[:-1] * signs[1:] < 0)[0]
                if len(sign_change) > 0:
                    idx = int(sign_change[0])
                    chosen = float((grid[idx] + grid[idx + 1]) / 2.0)
                else:
                    chosen = float(grid[int(np.argmin(np.abs(excess)))])

            updated[market.name] = chosen

        delta = max(abs(updated[name] - prices_by_name[name]) for name in updated)
        prices_by_name = updated
        if delta < 1e-6:
            break

    for name, market in markets.items():
        market.adj_price = prices_by_name[name]
        market.adj_quantity = float(market.inverse_demand(market.adj_price))


def total_surplus(markets: Iterable[Market], adjusted: bool = False) -> float:
    total = 0.0
    for market in markets:
        if market.name in {"ro", "pl"}:
            continue
        if adjusted:
            total += market.adj_find_consumer_surplus() + market.adj_find_producer_surplus()
        else:
            total += market.find_consumer_surplus() + market.find_producer_surplus()
    return float(total)


def main() -> None:
    problem, markets = build_problem()

    pre = total_surplus(problem.nodes, adjusted=False)
    print("pre surplus:", pre)

    solve_network_prices(problem, markets)

    post = total_surplus(problem.nodes, adjusted=True)
    print("post surplus:", post)
    print("delta:", post - pre)

    for market in problem.nodes:
        if market.name in {"ro", "pl"}:
            continue
        print(market.name, "autarky=", market.price, "adjusted=", market.adj_price)


if __name__ == "__main__":
    main()