"""Greedy dynamic edge selection using iterative network equilibrium solving.

This script uses the existing network solver (from network_fix.py) to evaluate
edges iteratively:

1. Solve the current network to equilibrium
2. For each candidate edge, temporarily add it, resolve, and measure gain
3. Commit the edge with the highest gain
4. Repeat until budget exhausted

This is simpler and more transparent than ODE solving, but can be slower
because it resolves the full network many times.

Computational note: Each edge evaluation requires a full network solve (~100-500ms).
With ~50 candidate edges and ~10 iterations, this approach requires ~500 solves,
or roughly 50-250 seconds total.
"""

from __future__ import annotations

import contextlib
import io
import time
from itertools import combinations
from typing import Dict, List, Sequence, Tuple

import numpy as np

from network_fix import build_problem, solve_network_prices, total_surplus
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
        solve_network_prices(problem, markets)
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


def greedy_edge_selection_iterative(problem: Constants, markets_dict: Dict[str, Market], budget: float):
    """Greedily select edges using iterative equilibrium solving.

    At each step:
    1. Solve current network
    2. Test each remaining edge individually
    3. Pick the edge with best welfare gain
    4. Commit and repeat
    """
    selected_edges: List[Edge] = []
    spent = 0.0
    remaining_edges = set(candidate_edges(problem))

    print("[greedy iterative] starting edge selection", flush=True)
    iteration = 0

    while remaining_edges:
        iteration += 1
        print(
            f"[greedy iteration {iteration}] {len(remaining_edges)} edges to consider",
            flush=True,
        )

        start_iter = time.time()

        # Solve current network
        solve_network_prices(problem, markets_dict)
        base_surplus = total_surplus(problem.nodes, adjusted=True)
        print(f"[greedy iteration {iteration}] current surplus = {base_surplus:.4f}", flush=True)

        # Evaluate each candidate edge
        best_edge = None
        best_gain = -np.inf
        edge_count = 0

        for edge in sorted(remaining_edges):
            edge_count += 1
            left, right = edge
            cost = _edge_cost(problem, left, right)

            # Skip if over budget
            if spent + cost > budget:
                continue

            # Temporarily add edge and resolve
            problem.connect(markets_dict[left], markets_dict[right])
            solve_network_prices(problem, markets_dict)
            new_surplus = total_surplus(problem.nodes, adjusted=True)
            gain = new_surplus - base_surplus

            # Undo the connection (remove from matrix)
            i_idx = problem.index_dict[left]
            j_idx = problem.index_dict[right]
            problem.connection_matrix[i_idx][j_idx] = 0
            problem.connection_matrix[j_idx][i_idx] = 0

            print(
                f"  {edge[0]:3} -- {edge[1]:3}  cost={cost:8.0f}  gain={gain:10.4f}",
                flush=True,
            )

            if gain > best_gain:
                best_gain = gain
                best_edge = edge

        if best_edge is None:
            print("[greedy iterative] no more edges fit budget", flush=True)
            break

        # Commit the best edge permanently
        left, right = best_edge
        cost = _edge_cost(problem, left, right)
        problem.connect(markets_dict[left], markets_dict[right])
        selected_edges.append(best_edge)
        spent += cost
        remaining_edges.discard(best_edge)

        elapsed = time.time() - start_iter
        print(
            f"[greedy iteration {iteration}] selected {best_edge[0]} -- {best_edge[1]} "
            f"(gain={best_gain:.4f}, cost={cost:.0f}, total_spent={spent:.0f}, "
            f"elapsed={elapsed:.1f}s)",
            flush=True,
        )

    return selected_edges


def main():
    print("=" * 70, flush=True)
    print("GREEDY ITERATIVE EDGE SELECTION", flush=True)
    print("=" * 70, flush=True)

    start_time = time.time()
    problem, markets_dict = _quiet_build()
    budget = 10.0 * float(np.max(problem.cost_to_create_matrix))

    print(f"budget = {budget:.2f}", flush=True)
    print(f"candidate edges = {len(candidate_edges(problem))}", flush=True)
    print("", flush=True)

    selected = greedy_edge_selection_iterative(problem, markets_dict, budget)

    print("", flush=True)
    print("=" * 70, flush=True)
    print("FINAL RESULTS (GREEDY ITERATIVE)", flush=True)
    print("=" * 70, flush=True)

    solve_network_prices(problem, markets_dict)
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
