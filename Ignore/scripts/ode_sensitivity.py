#!/usr/bin/env python3
"""Sensitivity sweep for the ODE-style solver on the base network.

This compares dynamic_solve(alpha, max_iter) against the LP benchmark
prices from solve_network_prices on the same base network.

It is intentionally lightweight so it can finish quickly and show how
alpha/max_iter affect distance to the benchmark prices.
"""
from __future__ import annotations

import pathlib
import statistics
import sys
from time import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network_fix import build_problem, solve_network_prices
import ode_dynamic_equilibrium as ode_mod


def price_map(markets):
    out = {}
    for m in markets.values():
        p = getattr(m, "adj_price", None)
        if p is None:
            p = getattr(m, "price", None)
        out[m.name] = float(p) if p is not None else float("nan")
    return out


# LP benchmark on the base network
base_problem, base_markets = build_problem()
solve_network_prices(base_problem, base_markets)
lp_prices = price_map(base_markets)

alphas = [0.001, 0.01, 0.05, 0.1]
max_iters = [25, 100, 250, 500]
results = []
original_dyn = ode_mod.dynamic_solve

start_all = time()
try:
    for alpha in alphas:
        for max_iter in max_iters:
            # fresh problem for each run
            problem, markets = build_problem()

            def dyn(problem_, markets_):
                return original_dyn(problem_, markets_, alpha=alpha, max_iter=max_iter)

            ode_mod.dynamic_solve = dyn
            run_start = time()
            try:
                ode_mod.dynamic_solve(problem, markets)
            finally:
                ode_mod.dynamic_solve = original_dyn
            elapsed = time() - run_start

            ode_prices = price_map(markets)
            diffs = []
            near_autarky = 0
            for mk, lpv in lp_prices.items():
                od = ode_prices.get(mk)
                aut = getattr(markets[mk], "price", float("nan"))
                if od != od or lpv != lpv:
                    continue
                diffs.append(abs(od - lpv))
                if abs(od - aut) <= max(0.01, 0.001 * abs(aut)):
                    near_autarky += 1

            results.append(
                {
                    "alpha": alpha,
                    "max_iter": max_iter,
                    "elapsed": elapsed,
                    "mean_abs_diff_lp": statistics.mean(diffs) if diffs else float("nan"),
                    "median_abs_diff_lp": statistics.median(diffs) if diffs else float("nan"),
                    "near_autarky_count": near_autarky,
                    "ode_prices": ode_prices,
                }
            )
finally:
    ode_mod.dynamic_solve = original_dyn

elapsed_all = time() - start_all

print(f"Total sweep time: {elapsed_all:.2f}s")
print("alpha,max_iter,elapsed_s,mean_abs_diff_to_LP,median_abs_diff_to_LP,near_autarky_count")
for r in results:
    print(
        f"{r['alpha']},{r['max_iter']},{r['elapsed']:.2f},"
        f"{r['mean_abs_diff_lp']:.4f},{r['median_abs_diff_lp']:.4f},{r['near_autarky_count']}"
    )

# Show the best scenario by LP closeness
best = min(results, key=lambda x: x["mean_abs_diff_lp"])
print("\nBest by mean abs diff to LP:")
print(best["alpha"], best["max_iter"], best["mean_abs_diff_lp"], best["median_abs_diff_lp"], best["near_autarky_count"])
print("\nLP benchmark prices:")
for k in sorted(lp_prices):
    print(f"  {k}: {lp_prices[k]:.4f}")
