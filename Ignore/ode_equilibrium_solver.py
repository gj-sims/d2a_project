"""Dynamic equilibrium solver using differential equations (ODE).

This script models market prices as state variables evolving toward equilibrium
via a tâtonnement-style ODE system:

    dp_i/dt = α * (S_i(p) + imports_i(p) - D_i(p) - exports_i(p))

It then uses this ODE solver to evaluate true equilibria for different edge sets
and greedily selects edges to maximize welfare under budget.

Computational note: ODE integration is typically fast per-solve (10-100ms),
but still requires many solves for edge search. Total time scales with the
number of candidate edges and search iterations.
"""

from __future__ import annotations

import contextlib
import io
import time
from itertools import combinations
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np
from scipy.integrate import odeint

from network_fix import build_problem, total_surplus
from constants import Constants
from markets import Market

Edge = Tuple[str, str]


def _quiet_build(extra_edges: Sequence[Edge] = ()):
    """Build and solve a network quietly."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        problem, markets = build_problem()
        for left, right in extra_edges:
            if left in markets and right in markets:
                problem.connect(markets[left], markets[right])
    return problem, markets


def _market_names(problem) -> List[str]:
    return [m.name for m in problem.nodes if m.name not in {"pl", "ro"}]


def _edge_cost(problem, left: str, right: str) -> float:
    i = problem.index_dict[left]
    j = problem.index_dict[right]
    return float((problem.cost_to_create_matrix[i][j] + problem.cost_to_create_matrix[j][i]) / 2.0)


def candidate_edges(problem) -> List[Edge]:
    names = _market_names(problem)
    edges: List[Edge] = []
    for left, right in combinations(names, 2):
        i = problem.index_dict[left]
        j = problem.index_dict[right]
        if problem.connection_matrix[i][j] != 1:
            edges.append((left, right))
    return edges


def ode_price_dynamics(
    p_vector: np.ndarray,
    t: float,
    problem: Constants,
    markets_dict: Dict[str, Market],
    names: List[str],
    speed: float = 1.0,
) -> np.ndarray:
    """Compute dp/dt for the market network.

    Args:
        p_vector: price vector, one element per market in `names`
        t: time (unused in this static ODE)
        problem: Constants network object
        markets_dict: dict mapping market name to Market object
        names: ordered list of market names
        speed: adjustment speed parameter

    Returns:
        dp/dt vector
    """
    dp = np.zeros_like(p_vector)
    prices = {name: float(p) for name, p in zip(names, p_vector)}

    for idx, market_name in enumerate(names):
        market = markets_dict[market_name]
        i_idx = problem.index_dict.get(market_name)
        if i_idx is None:
            continue

        # Autarky supply and demand at current price
        supply_q = float(market.inverse_supply(prices[market_name]))
        demand_q = float(market.inverse_demand(prices[market_name]))

        # Net exports (positive = exporting)
        net_exports = 0.0
        for other_name in names:
            if other_name == market_name or other_name in {"ro", "pl"}:
                continue

            j_idx = problem.index_dict.get(other_name)
            if j_idx is None or problem.connection_matrix[i_idx][j_idx] != 1:
                continue

            other_market = markets_dict[other_name]
            loss = (
                problem.transmission_loss_matrix[i_idx][j_idx]
                + problem.transmission_loss_matrix[j_idx][i_idx]
            ) / 2.0

            other_price = prices[other_name]

            # Export if our price is lower
            if prices[market_name] < other_price * loss:
                exports = float(other_market.inverse_demand(other_price)) - float(
                    other_market.inverse_supply(other_price)
                )
                net_exports += exports / loss

            # Import if other's price is lower
            if other_price < prices[market_name] * loss:
                imports = float(other_market.inverse_supply(other_price)) - float(
                    other_market.inverse_demand(other_price)
                )
                net_exports -= imports * loss

        # Excess demand (negative = excess supply)
        excess = supply_q + net_exports - demand_q
        dp[idx] = speed * (-excess)  # Price increases if there is excess demand

    return dp


def solve_ode_equilibrium(problem: Constants, markets_dict: Dict[str, Market], max_time: float = 10.0) -> None:
    """Solve for equilibrium using ODE integration.

    Updates market.adj_price and market.adj_quantity.
    """
    names = _market_names(problem)
    p0 = np.array([markets_dict[name].price for name in names])

    # Integrate ODE to equilibrium
    t_eval = np.linspace(0, max_time, 1000)
    solution = odeint(
        ode_price_dynamics,
        p0,
        t_eval,
        args=(problem, markets_dict, names, 1.0),
        full_output=False,
    )

    # Take final state
    p_final = solution[-1]

    for name, p in zip(names, p_final):
        market = markets_dict[name]
        market.adj_price = float(p)
        market.adj_quantity = float(market.inverse_demand(float(p)))


def greedy_edge_selection_ode(problem: Constants, markets_dict: Dict[str, Market], budget: float):
    """Greedily select edges using ODE solving.

    At each step:
    1. Solve current network with ODE
    2. Evaluate all candidate edges
    3. Pick the edge with best welfare gain
    4. Add it permanently and repeat
    """
    selected_edges: List[Edge] = []
    spent = 0.0
    remaining_edges = set(candidate_edges(problem))

    print("[ODE greedy] starting edge selection", flush=True)
    iteration = 0

    while remaining_edges:
        iteration += 1
        print(f"[ODE greedy iteration {iteration}] {len(remaining_edges)} edges to consider", flush=True)

        start_iter = time.time()
        solve_ode_equilibrium(problem, markets_dict)
        base_surplus = total_surplus(problem.nodes, adjusted=True)
        print(f"[ODE greedy iteration {iteration}] current surplus = {base_surplus:.4f}", flush=True)

        # Evaluate each candidate edge
        best_edge = None
        best_gain = -np.inf

        for edge in sorted(remaining_edges):
            left, right = edge
            cost = _edge_cost(problem, left, right)
            if spent + cost > budget:
                continue

            problem.connect(markets_dict[left], markets_dict[right])
            solve_ode_equilibrium(problem, markets_dict)
            new_surplus = total_surplus(problem.nodes, adjusted=True)
            gain = new_surplus - base_surplus
            problem.connect(markets_dict[left], markets_dict[right])  # undo

            print(
                f"  {edge[0]:3} -- {edge[1]:3}  cost={cost:8.0f}  gain={gain:10.4f}",
                flush=True,
            )

            if gain > best_gain:
                best_gain = gain
                best_edge = edge

        if best_edge is None:
            print("[ODE greedy] no more edges fit budget", flush=True)
            break

        # Commit the best edge
        left, right = best_edge
        cost = _edge_cost(problem, left, right)
        problem.connect(markets_dict[left], markets_dict[right])
        selected_edges.append(best_edge)
        spent += cost
        remaining_edges.discard(best_edge)

        elapsed = time.time() - start_iter
        print(
            f"[ODE greedy iteration {iteration}] selected {best_edge[0]} -- {best_edge[1]} "
            f"(gain={best_gain:.4f}, cost={cost:.0f}, total_spent={spent:.0f})",
            flush=True,
        )

    return selected_edges


def main():
    print("=" * 70, flush=True)
    print("ODE-BASED DYNAMIC EQUILIBRIUM SOLVER", flush=True)
    print("=" * 70, flush=True)

    start_time = time.time()
    problem, markets_dict = _quiet_build()
    budget = 10.0 * float(np.max(problem.cost_to_create_matrix))

    print(f"budget = {budget:.2f}", flush=True)
    print(f"candidate edges = {len(candidate_edges(problem))}", flush=True)
    print("", flush=True)

    selected = greedy_edge_selection_ode(problem, markets_dict, budget)

    print("", flush=True)
    print("=" * 70, flush=True)
    print("FINAL RESULTS (ODE)", flush=True)
    print("=" * 70, flush=True)

    solve_ode_equilibrium(problem, markets_dict)
    final_surplus = total_surplus(problem.nodes, adjusted=True)

    print(f"selected edges: {len(selected)}", flush=True)
    for left, right in selected:
        print(f"  {left} -- {right}  cost={_edge_cost(problem, left, right):.0f}", flush=True)

    print(f"final social surplus = {final_surplus:.4f}", flush=True)
    print("final market prices:", flush=True)
    for market in problem.nodes:
        if market.name not in {"ro", "pl"}:
            print(
                f"  {market.name}: autarky={market.price:.4f} adjusted={market.adj_price:.4f}",
                flush=True,
            )

    elapsed = time.time() - start_time
    print("", flush=True)
    print(f"total elapsed time: {elapsed:.1f} seconds", flush=True)


if __name__ == "__main__":
    main()
