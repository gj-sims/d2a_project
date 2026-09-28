"""Gurobi-based network design for the D2A project.

This script does not modify any existing project files.

Model idea
==========
The exact equilibrium response of the market network is nonlinear, so this
script uses the full network solver from network_fix.py to estimate the
marginal social surplus gain of each candidate new edge.

Those gains become the linear objective coefficients in a Gurobi model:

    maximize  baseline_social_surplus + sum(gain_e * x_e)

subject to

    sum(cost_e * x_e) <= 10 * max(cost_to_create)
    x_e in {0, 1}

The selected edges are then applied to the base network and the final
social surplus is recomputed.
"""

from __future__ import annotations

import contextlib
import io
import time
from itertools import combinations
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from network_fix import build_problem, solve_network_prices, total_surplus

try:
    import gurobipy as gp
    from gurobipy import GRB

    HAVE_GUROBI = True
except Exception:  # pragma: no cover - import guard for environments without Gurobi
    gp = None
    GRB = None
    HAVE_GUROBI = False


Edge = Tuple[str, str]


def _quiet_build(extra_edges: Sequence[Edge] = ()):
    """Build and solve a network quietly so edge gains can be estimated."""

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        problem, markets = build_problem()
        for left, right in extra_edges:
            if left in markets and right in markets:
                problem.connect(markets[left], markets[right])
        solve_network_prices(problem, markets)
    return problem, markets


def _all_market_names(problem) -> List[str]:
    return [market.name for market in problem.nodes if market.name not in {"pl", "ro"}]


def _edge_cost(problem, left: str, right: str) -> float:
    i = problem.index_dict[left]
    j = problem.index_dict[right]
    return float(
        (problem.cost_to_create_matrix[i][j] + problem.cost_to_create_matrix[j][i]) / 2.0
    )


def candidate_edges(problem) -> List[Edge]:
    """All non-existing undirected edges among the modelled markets."""

    names = _all_market_names(problem)
    edges: List[Edge] = []
    for left, right in combinations(names, 2):
        i = problem.index_dict[left]
        j = problem.index_dict[right]
        if problem.connection_matrix[i][j] == 1:
            continue
        edges.append((left, right))
    return edges


def estimate_marginal_gains(problem, edges: Sequence[Edge]) -> Dict[Edge, float]:
    """Estimate each edge's welfare gain relative to the current network."""

    base_problem, base_markets = _quiet_build()
    base_surplus = total_surplus(base_problem.nodes, adjusted=True)

    gains: Dict[Edge, float] = {}
    start_time = time.time()
    total_edges = len(edges)

    for edge in edges:
        edge_num = len(gains) + 1
        elapsed = time.time() - start_time
        print(
            f"[gain pass] {edge_num}/{total_edges} testing {edge[0]} -- {edge[1]} "
            f"(elapsed {elapsed:.1f}s)",
            flush=True,
        )

        trial_problem, trial_markets = _quiet_build([edge])
        trial_surplus = total_surplus(trial_problem.nodes, adjusted=True)
        gains[edge] = float(trial_surplus - base_surplus)

        if edge_num % 10 == 0 or edge_num == total_edges:
            elapsed = time.time() - start_time
            print(
                f"[gain pass] completed {edge_num}/{total_edges} edges in {elapsed:.1f}s",
                flush=True,
            )

    return gains


def solve_with_gurobi(problem, edges: Sequence[Edge], gains: Dict[Edge, float]) -> List[Edge]:
    """Solve the edge-selection problem with Gurobi."""

    if not HAVE_GUROBI:
        raise RuntimeError(
            "gurobipy is not installed in the active environment. "
            "Install Gurobi to run this model."
        )

    budget = 10.0 * float(np.max(problem.cost_to_create_matrix))

    model = gp.Model("network_design")
    model.Params.OutputFlag = 0
    model.Params.TimeLimit = 300

    x = {}
    for edge in edges:
        x[edge] = model.addVar(vtype=GRB.BINARY, name=f"x_{edge[0]}_{edge[1]}")

    model.update()

    model.addConstr(
        gp.quicksum(_edge_cost(problem, left, right) * x[(left, right)] for left, right in edges)
        <= budget,
        name="budget",
    )

    base_problem, _ = _quiet_build()
    base_surplus = total_surplus(base_problem.nodes, adjusted=True)

    model.setObjective(
        base_surplus + gp.quicksum(gains[edge] * x[edge] for edge in edges),
        GRB.MAXIMIZE,
    )

    model.optimize()

    if model.Status == GRB.TIME_LIMIT:
        print("[gurobi] time limit reached; returning best incumbent found so far.", flush=True)
    elif model.Status == GRB.OPTIMAL:
        print("[gurobi] optimal solution found.", flush=True)
    else:
        print(f"[gurobi] finished with status {model.Status}.", flush=True)

    selected = [edge for edge in edges if x[edge].X > 0.5]
    return selected


def apply_selected_edges(selected_edges: Sequence[Edge]):
    """Build the final network, add the chosen edges, and solve it."""

    problem, markets = _quiet_build()
    for left, right in selected_edges:
        problem.connect(markets[left], markets[right])

    solve_network_prices(problem, markets)
    final_surplus = total_surplus(problem.nodes, adjusted=True)
    return problem, markets, final_surplus


def main() -> None:
    problem, markets = _quiet_build()
    edges = candidate_edges(problem)
    gains = estimate_marginal_gains(problem, edges)

    budget = 10.0 * float(np.max(problem.cost_to_create_matrix))
    print(f"budget = {budget:.2f}")
    print(f"candidate edges = {len(edges)}")
    print("starting edge-gain estimation and Gurobi solve...", flush=True)

    if HAVE_GUROBI:
        selected = solve_with_gurobi(problem, edges, gains)
        final_problem, final_markets, final_surplus = apply_selected_edges(selected)

        print("selected edges:")
        for left, right in selected:
            print(f"  {left} -- {right}  cost={_edge_cost(problem, left, right):.2f}  gain={gains[(left, right)]:.2f}")

        print(f"final social surplus = {final_surplus:.4f}")
        print("final market prices:")
        for market in final_problem.nodes:
            if market.name in {"pl", "ro"}:
                continue
            print(f"  {market.name}: autarky={market.price:.4f} adjusted={market.adj_price:.4f}")
    else:
        print("gurobipy is not installed in this environment.")
        print("This file is ready for Gurobi, but cannot optimize until gurobipy is available.")


if __name__ == "__main__":
    main()