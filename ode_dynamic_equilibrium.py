"""ODE-inspired dynamic equilibrium solver with stepwise market functions.

Since supply/demand curves are stepwise (not smooth), we cannot use
standard ODE solvers like odeint. Instead, this uses a price-adjustment
rule inspired by tâtonnement dynamics:

    dp_i(t) = alpha * (S_i(p) + imports - D_i(p) - exports)

But solved via fixed-point iteration rather than numerical integration,
which is more stable for discontinuous functions and smaller networks.

For each candidate edge, we:
1. Add it to the edge set
2. Solve the dynamic equilibrium
3. Measure the surplus change
4. Track which edge gives the best marginal improvement

Then greedily add edges under budget.
"""

from __future__ import annotations

import contextlib
import io
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

from network_fix import build_problem, total_surplus

Edge = Tuple[str, str]


def _quiet_build(extra_edges: Sequence[Edge] = ()):
    """Build network and solve with fixed-point dynamics."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        problem, markets = build_problem()
        for left, right in extra_edges:
            if left in markets and right in markets:
                problem.connect(markets[left], markets[right])
        dynamic_solve(problem, markets)
    return problem, markets


def dynamic_solve(
    problem, markets: Dict[str, object], alpha: float = 0.01, max_iter: int = 100, tol: float = 1e-6
) -> None:
    """Solve network equilibrium using price-adjustment dynamics.
    
    Uses fixed-point iteration with a tâtonnement-like adjustment rule:
        p_i(k+1) = p_i(k) + alpha * excess_i(p(k))
    
    This avoids requiring derivatives, so it works with stepwise curves.
    """
    
    prices = {name: market.price for name, market in markets.items()}
    
    for iteration in range(max_iter):
        new_prices = dict(prices)
        
        for market in problem.nodes:
            if market.name in {"ro", "pl"}:
                continue
            
            i_idx = problem.index_dict.get(market.name)
            if i_idx is None:
                continue
            
            # Compute supply and demand at current price
            p_i = prices[market.name]
            supply = float(market.inverse_supply(p_i))
            demand = float(market.inverse_demand(p_i))
            
            # Compute network imports/exports
            imports = 0.0
            exports = 0.0
            
            for other in problem.nodes:
                if other.name in {"ro", "pl"} or other.name == market.name:
                    continue
                
                j_idx = problem.index_dict.get(other.name)
                if j_idx is None or problem.connection_matrix[i_idx][j_idx] != 1:
                    continue
                
                loss = (
                    problem.transmission_loss_matrix[i_idx][j_idx]
                    + problem.transmission_loss_matrix[j_idx][i_idx]
                ) / 2.0
                
                p_j = prices[other.name]
                
                if p_i < p_j * loss:
                    other_supply = float(other.inverse_supply(p_j))
                    other_demand = float(other.inverse_demand(p_j))
                    exports += (1.0 / loss) * (other_supply - other_demand)
                
                if p_j < p_i * loss:
                    other_supply = float(other.inverse_supply(p_j))
                    other_demand = float(other.inverse_demand(p_j))
                    imports += loss * (other_demand - other_supply)
            
            # Excess: positive means price should rise
            excess = supply + imports - demand - exports
            
            # Price adjustment
            new_prices[market.name] = p_i + alpha * excess
            
            # Keep prices in valid range
            low = max(float(market.supply["price"].min()), float(market.demand["price"].min()), 0.0)
            high = min(float(market.supply["price"].max()), float(market.demand["price"].max()))
            new_prices[market.name] = np.clip(new_prices[market.name], low, high)
        
        # Check convergence
        delta = max(abs(new_prices[name] - prices[name]) for name in prices)
        prices = new_prices
        
        if delta < tol:
            break
    
    # Store results
    for name, market in markets.items():
        market.adj_price = prices[name]
        market.adj_quantity = float(market.inverse_demand(market.adj_price))


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


def ode_based_greedy_search(budget_multiplier: float = 10.0, max_iterations: int = 50) -> None:
    """ODE-inspired dynamic solver with greedy edge selection."""
    
    print("[ode_greedy] initializing base network...", flush=True)
    start_time = time.time()
    base_problem, base_markets = _quiet_build()
    base_surplus = total_surplus(base_problem.nodes, adjusted=True)
    init_time = time.time() - start_time
    print(f"[ode_greedy] base network solved in {init_time:.2f}s, surplus={base_surplus:.4f}", flush=True)
    
    budget = budget_multiplier * float(np.max(base_problem.cost_to_create_matrix))
    print(f"[ode_greedy] budget = {budget:.2f}", flush=True)
    
    selected_edges: set[Edge] = set()
    total_cost = 0.0
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[ode_greedy] iteration {iteration}:", flush=True)
        
        candidates = candidate_edges_not_in(base_problem, selected_edges)
        if not candidates:
            print("[ode_greedy] no more candidate edges available.", flush=True)
            break
        
        print(f"[ode_greedy]   evaluating {len(candidates)} candidate edges...", flush=True)
        
        best_edge = None
        best_edge_gain = -np.inf
        best_edge_cost = None
        best_problem = None
        best_markets = None
        
        for edge_idx, edge in enumerate(candidates):
            if (edge_idx + 1) % 10 == 0 or edge_idx == 0 or edge_idx == len(candidates) - 1:
                print(f"[ode_greedy]   tested {edge_idx + 1}/{len(candidates)} edges...", flush=True)
            
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
            print("[ode_greedy] no edge with positive gain found.", flush=True)
            break
        
        if total_cost + best_edge_cost > budget:
            print(
                f"[ode_greedy]   best edge {best_edge} would exceed budget "
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
            f"[ode_greedy]   selected {best_edge[0]} -- {best_edge[1]}, "
            f"cost={best_edge_cost:.2f}, gain={best_edge_gain:.4f}, "
            f"total_surplus={base_surplus:.4f}, total_cost={total_cost:.2f}",
            flush=True,
        )
    
    print(f"\n[ode_greedy] final selection:", flush=True)
    for edge in sorted(selected_edges):
        cost = _edge_cost(base_problem, edge[0], edge[1])
        print(f"  {edge[0]} -- {edge[1]}  cost={cost:.2f}", flush=True)
    print(f"[ode_greedy] final total cost = {total_cost:.2f} / {budget:.2f}", flush=True)
    print(f"[ode_greedy] final social surplus = {base_surplus:.4f}", flush=True)
    print(f"[ode_greedy] final prices:", flush=True)
    for market in base_problem.nodes:
        if market.name in {"pl", "ro"}:
            continue
        print(f"  {market.name}: {market.adj_price:.4f}", flush=True)


if __name__ == "__main__":
    ode_based_greedy_search(budget_multiplier=10.0, max_iterations=50)
