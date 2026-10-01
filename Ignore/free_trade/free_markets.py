from __future__ import annotations

import pathlib
import sys
from typing import Dict, Iterable, Tuple

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from load_data import load_dfs
from markets import Market
from transportless_constants import TransportlessConstants

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


def build_problem() -> tuple[TransportlessConstants, Dict[str, Market]]:
    dfs = load_dfs()
    problem = TransportlessConstants()
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


def aggregate_excess(problem: TransportlessConstants, markets: Dict[str, Market], price: float) -> float:
    total_supply = 0.0
    total_demand = 0.0
    for name, market in markets.items():
        if name in {"pl", "ro"}:
            continue
        total_supply += float(market.inverse_supply(price))
        total_demand += float(market.inverse_demand(price))
    return total_supply - total_demand


def solve_world_price(problem: TransportlessConstants, markets: Dict[str, Market], tol: float = 1e-6, max_iter: int = 250) -> tuple[float, float]:
    price_points = set()
    for market in markets.values():
        price_points.update(float(x) for x in market.supply["price"].tolist())
        price_points.update(float(x) for x in market.demand["price"].tolist())

    price_grid = sorted(p for p in price_points if np.isfinite(p))
    if not price_grid:
        raise ValueError("No price breakpoints available to solve world price.")

    low = price_grid[0]
    high = price_grid[-1]
    ex_low = aggregate_excess(problem, markets, low)
    ex_high = aggregate_excess(problem, markets, high)

    # Ensure we bracket a sign change if possible.
    if ex_low > 0 and ex_high > 0:
        world_price = low
    elif ex_low < 0 and ex_high < 0:
        world_price = high
    else:
        for _ in range(max_iter):
            mid = (low + high) / 2.0
            excess = aggregate_excess(problem, markets, mid)
            if abs(excess) < tol or abs(high - low) < tol:
                low = high = mid
                break
            if excess > 0:
                high = mid
            else:
                low = mid
        world_price = (low + high) / 2.0

    total_supply = 0.0
    total_demand = 0.0
    for name, market in markets.items():
        if name in {"pl", "ro"}:
            continue
        total_supply += float(market.inverse_supply(world_price))
        total_demand += float(market.inverse_demand(world_price))

    world_quantity = 0.5 * (total_supply + total_demand)
    return float(world_price), float(world_quantity)


def apply_world_price(markets: Dict[str, Market], world_price: float) -> None:
    for name, market in markets.items():
        if name in {"pl", "ro"}:
            continue
        supply_qty = float(market.inverse_supply(world_price))
        demand_qty = float(market.inverse_demand(world_price))
        market.adj_price = float(world_price)
        market.adj_quantity = demand_qty
        market.world_supply = supply_qty
        market.world_demand = demand_qty
        market.world_net_trade = supply_qty - demand_qty


def total_social_surplus(markets: Dict[str, Market]) -> float:
    total = 0.0
    for name, market in markets.items():
        if name in {"pl", "ro"}:
            continue
        total += float(market.adj_find_consumer_surplus())
        total += float(market.adj_find_producer_surplus())
    return float(total)


def report_free_trade(problem: TransportlessConstants, markets: Dict[str, Market]) -> None:
    world_price, world_quantity = solve_world_price(problem, markets)
    apply_world_price(markets, world_price)
    surplus = total_social_surplus(markets)

    print("FREE TRADE WORLD EQUILIBRIUM")
    print("=" * 60)
    print(f"World price:    {world_price:.4f}")
    print(f"World quantity: {world_quantity:.4f}")
    print(f"Total social surplus: {surplus:.4f}")
    print()
    print("Market-level outcomes")
    print("-" * 60)
    print("market  autarky   worldP    supply    demand    net_trade")
    for name in MARKET_ORDER:
        if name not in markets or name in {"pl", "ro"}:
            continue
        market = markets[name]
        supply_qty = float(market.world_supply)
        demand_qty = float(market.world_demand)
        net_trade = float(market.world_net_trade)
        trade_label = "export" if net_trade > 0 else "import"
        trade_amt = abs(net_trade)
        print(
            f"{name:>5}  {market.price:8.4f}  {market.adj_price:8.4f}  "
            f"{supply_qty:8.4f}  {demand_qty:8.4f}  {net_trade:9.4f}  "
            f"({trade_label} {trade_amt:.4f})"
        )


def main() -> None:
    problem, markets = build_problem()
    report_free_trade(problem, markets)


if __name__ == "__main__":
    main()
