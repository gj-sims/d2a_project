"""Greedy iterative edge selection with full re-solve after each addition.

This approach:
1. Starts with the base network
2. Evaluates each candidate edge by temporarily adding it
3. Selects the edge that increases total surplus the most
4. Re-solves the full network with that edge
5. Repeats until budget is exhausted

This is slower but does not rely on linearity or additive effects.
It captures all multi-edge interactions dynamically.
"""

from __future__ import annotations

import contextlib
import io
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

from network_fix import build_problem, solve_network_prices, total_surplus

Edge = Tuple[str, str]


def _fmt_price(value):
    return "None" if value is None else f"{float(value):.4f}"


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


def _edge_cost(problem, left: str, right: str) -> float:
    i = problem.index_dict[left]
    j = problem.index_dict[right]
    return float(
        (problem.cost_to_create_matrix[i][j] + problem.cost_to_create_matrix[j][i]) / 2.0
    )


def candidate_edges_not_in(problem, selected: set[Edge]) -> List[Edge]:
    """All candidate edges minus those already selected."""
    names = [m.name for m in problem.nodes if m.name not in {"pl", "ro"}]
    candidates = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            idx_i = problem.index_dict[left]
            idx_j = problem.index_dict[right]
            if problem.connection_matrix[idx_i][idx_j] == 1:
                continue
            edge = tuple(sorted([left, right]))
            if edge not in selected:
                candidates.append(edge)
    return candidates


def greedy_search(budget_multiplier: float = 10.0, max_iterations: int = 50) -> None:
    """Greedily select edges that increase surplus the most, with full re-solve."""
    
    print("[greedy] initializing base network...", flush=True)
    start_time = time.time()
    base_problem, base_markets = _quiet_build()
    base_surplus = total_surplus(base_problem.nodes, adjusted=True)
    init_time = time.time() - start_time
    print(f"[greedy] base network solved in {init_time:.2f}s, surplus={base_surplus:.4f}", flush=True)
    
    budget = budget_multiplier * float(np.max(base_problem.cost_to_create_matrix))
    print(f"[greedy] budget = {budget:.2f}", flush=True)
    
    selected_edges: set[Edge] = set()
    total_cost = 0.0
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[greedy] iteration {iteration}:", flush=True)
        
        candidates = candidate_edges_not_in(base_problem, selected_edges)
        if not candidates:
            print("[greedy] no more candidate edges available.", flush=True)
            break
        
        print(f"[greedy]   evaluating {len(candidates)} candidate edges...", flush=True)
        
        best_edge = None
        best_edge_gain = -np.inf
        best_edge_cost = None
        best_problem = None
        best_markets = None
        
        for edge_idx, edge in enumerate(candidates):
            if (edge_idx + 1) % 10 == 0 or edge_idx == 0 or edge_idx == len(candidates) - 1:
                print(f"[greedy]   tested {edge_idx + 1}/{len(candidates)} edges...", flush=True)
            
            test_edges = list(selected_edges) + [edge]
            test_problem, test_markets = _quiet_build(test_edges)
            test_surplus = total_surplus(test_problem.nodes, adjusted=True)
            gain = test_surplus - base_surplus
            
            edge_cost = _edge_cost(base_problem, edge[0], edge[1])
            if gain > best_edge_gain:
                best_edge = edge
                best_edge_gain = gain
                best_edge_cost = edge_cost
                best_problem = test_problem
                best_markets = test_markets
        
        if best_edge is None or best_edge_cost is None:
            print("[greedy] no edge with positive gain found.", flush=True)
            break

        if best_edge_gain <= 0:
            print(
                f"[greedy]   best edge {best_edge} has non-positive gain "
                f"({best_edge_gain:.4f}); stopping.",
                flush=True,
            )
            break
        
        if total_cost + best_edge_cost > budget:
            print(
                f"[greedy]   best edge {best_edge} would exceed budget "
                f"({total_cost + best_edge_cost:.2f} > {budget:.2f})",
                flush=True,
            )
            break
        
        selected_edges.add(best_edge)
        total_cost += best_edge_cost
        base_surplus = total_surplus(best_problem.nodes, adjusted=True)
        base_problem = best_problem
        base_markets = best_markets

        print(
            f"[greedy]   selected {best_edge[0]} -- {best_edge[1]}, "
            f"cost={best_edge_cost:.2f}, gain={best_edge_gain:.4f}, "
            f"total_surplus={base_surplus:.4f}, total_cost={total_cost:.2f}",
            flush=True,
        )

        print("[greedy]   updated equilibrium prices:", flush=True)
        for market in best_problem.nodes:
            if market.name in {"pl", "ro"}:
                continue
            print(
                f"  {market.name}: autarky={_fmt_price(market.price)}, "
                f"adjusted={_fmt_price(market.adj_price)}, "
                f"change={'None' if market.price is None or market.adj_price is None else f'{float(market.adj_price - market.price):+.4f}'}",
                flush=True,
            )
    
    print(f"\n[greedy] final selection:", flush=True)
    for edge in sorted(selected_edges):
        cost = _edge_cost(base_problem, edge[0], edge[1])
        print(f"  {edge[0]} -- {edge[1]}  cost={cost:.2f}", flush=True)
    print(f"[greedy] final total cost = {total_cost:.2f} / {budget:.2f}", flush=True)
    print(f"[greedy] final social surplus = {base_surplus:.4f}", flush=True)
    print(f"[greedy] final prices:", flush=True)
    for market in base_problem.nodes:
        if market.name in {"pl", "ro"}:
            continue
        print(f"  {market.name}: {market.adj_price:.4f}", flush=True)

    return selected_edges, base_problem, base_surplus


if __name__ == "__main__":
    greedy_search(budget_multiplier=10.0, max_iterations=50)
