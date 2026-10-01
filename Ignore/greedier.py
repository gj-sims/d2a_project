# ============================================================
# MAB vs. GREEDY NETWORK EXPANSION ANALYSIS
#
# Comparative analysis of Network Expansion algorithms:
#   1. Pure Greedy Baseline (Max Surplus Gain ΔW)
#   2. ROI / Cost-Weighted Greedy (Max ΔW / Cost)
#   3. Epsilon-Greedy (Exploration via random edge selection)
#   4. Upper Confidence Bound (UCB1)
#
# Settings:
#   - Budget Multiplier = 3.0 (3x maximum single edge cost)
#   - Minimum Surplus Gain = 0.01
# ============================================================

import copy
import math
import random
import time
import numpy as np
import pandas as pd

from constants import Constants
from gurobi_v3_inner import (
    calculate_surplus,
    extract_solution,
    solve_network,
)
from load_data import load_dfs
from markets import Market

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

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
]

INITIAL_CONNECTIONS = [
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
    "nl": (52.3700, 4.8900),
    "dk": (55.6761, 12.5683),
    "fi": (60.1700, 24.9400),
    "no": (59.9100, 10.7500),
    "se": (59.3300, 18.0600),
    "bg": (42.7300, 25.4900),
    "lv": (59.4370, 24.7540),
}

BUDGET_MULTIPLIER = 3.0
MAX_ITERATIONS = 50
MIN_SURPLUS_GAIN = 0.01
RANDOM_SEED = 42

# ============================================================
# NETWORK SETUP & HELPER FUNCTIONS
# ============================================================


def build_markets():
    dfs = load_dfs()
    markets = {}
    for name in MARKET_ORDER:
        market = Market(name, dfs[name])
        market.lat = COORDS[name][0]
        market.lon = COORDS[name][1]
        market.find_price()
        markets[name] = market
    return markets


def normalize_edge(a, b):
    idx_a = MARKET_ORDER.index(a)
    idx_b = MARKET_ORDER.index(b)
    return (a, b) if idx_a < idx_b else (b, a)


def get_all_possible_edges(markets):
    edges = []
    for i in range(len(MARKET_ORDER)):
        for j in range(i + 1, len(MARKET_ORDER)):
            a, b = MARKET_ORDER[i], MARKET_ORDER[j]
            if a in markets and b in markets:
                edges.append(normalize_edge(a, b))
    return list(set(edges))


def get_current_edges(constants, markets):
    edges = []
    for i in range(len(MARKET_ORDER)):
        for j in range(i + 1, len(MARKET_ORDER)):
            a, b = MARKET_ORDER[i], MARKET_ORDER[j]
            idx_a = constants.index_dict[a]
            idx_b = constants.index_dict[b]
            if constants.connection_matrix[idx_a][idx_b] == 1:
                edges.append(normalize_edge(a, b))
    return list(set(edges))


def get_candidate_edges(constants, markets):
    all_edges = get_all_possible_edges(markets)
    current_edges = set(get_current_edges(constants, markets))
    return [e for e in all_edges if e not in current_edges]


def initialize_edge_costs(constants, markets):
    for i in range(len(MARKET_ORDER)):
        for j in range(i + 1, len(MARKET_ORDER)):
            a, b = MARKET_ORDER[i], MARKET_ORDER[j]
            m_a, m_b = markets[a], markets[b]
            idx_a, idx_b = constants.index_dict[a], constants.index_dict[b]
            dist = constants.distance(m_a, m_b)
            cost = float(1.6 * dist)
            constants.cost_to_create_matrix[idx_a][idx_b] = cost
            constants.cost_to_create_matrix[idx_b][idx_a] = cost


def get_edge_cost(constants, edge):
    a, b = edge
    idx_a, idx_b = constants.index_dict[a], constants.index_dict[b]
    return constants.cost_to_create_matrix[idx_a][idx_b]


def copy_network(base_constants):
    constants = Constants()
    constants.connection_matrix = base_constants.connection_matrix.copy()
    constants.cost_to_create_matrix = (
        base_constants.cost_to_create_matrix.copy()
    )
    constants.transmission_loss_matrix = (
        base_constants.transmission_loss_matrix.copy()
    )
    constants.nodes = list(base_constants.nodes)
    return constants


def solve_current_network(markets, constants):
    solution = solve_network(markets, constants)
    extracted = extract_solution(markets, constants, solution)
    surplus = calculate_surplus(markets, extracted["markets"])
    return solution, extracted, surplus


def evaluate_candidate(markets, base_constants, candidate):
    candidate_constants = copy_network(base_constants)
    a, b = candidate
    candidate_constants.connect(markets[a], markets[b])
    try:
        solution, extracted, surplus = solve_current_network(
            markets, candidate_constants
        )
        return {
            "edge": candidate,
            "constants": candidate_constants,
            "solution": solution,
            "extracted": extracted,
            "surplus": surplus,
        }
    except Exception as e:
        return None


# ============================================================
# MAB AND GREEDY EXPANSION ENGINE
# ============================================================


class NetworkExpansionEngine:

    def __init__(
        self, budget_multiplier=BUDGET_MULTIPLIER, seed=RANDOM_SEED
    ):
        np.random.seed(seed)
        random.seed(seed)

        self.markets = build_markets()
        self.constants = Constants()
        self.constants.nodes = list(self.markets.values())
        initialize_edge_costs(self.constants, self.markets)

        # Connect initial baseline network
        for a, b in INITIAL_CONNECTIONS:
            self.constants.connect(self.markets[a], self.markets[b])

        self.all_edges = get_all_possible_edges(self.markets)
        self.max_edge_cost = max(
            get_edge_cost(self.constants, e) for e in self.all_edges
        )

        # Expansion Budget (allocated for newly constructed edges)
        self.expansion_budget = budget_multiplier * self.max_edge_cost

        # Base equilibrium solve
        _, _, self.initial_surplus = solve_current_network(
            self.markets, self.constants
        )

    def run_greedy(self):
        """Pure Greedy Outer Loop (Max Surplus Gain)"""
        constants = copy_network(self.constants)
        spent_cost = 0.0
        current_surplus = self.initial_surplus
        selected_edges = []
        inner_solves = 1

        for iteration in range(MAX_ITERATIONS):
            candidates = get_candidate_edges(constants, self.markets)
            if not candidates:
                break

            best_candidate = None
            best_gain = -float("inf")

            for candidate in candidates:
                edge_cost = get_edge_cost(constants, candidate)
                if spent_cost + edge_cost > self.expansion_budget:
                    continue

                inner_solves += 1
                res = evaluate_candidate(self.markets, constants, candidate)
                if res is None:
                    continue

                gain = res["surplus"] - current_surplus
                if gain > MIN_SURPLUS_GAIN and gain > best_gain:
                    best_gain = gain
                    best_candidate = res

            if best_candidate is None:
                break

            selected_edge = best_candidate["edge"]
            constants.connect(
                self.markets[selected_edge[0]], self.markets[selected_edge[1]]
            )
            selected_edges.append(selected_edge)
            spent_cost += get_edge_cost(constants, selected_edge)
            current_surplus = best_candidate["surplus"]

        return {
            "strategy": "Pure Greedy",
            "final_surplus": current_surplus,
            "net_surplus_gain": current_surplus - self.initial_surplus,
            "expansion_cost_spent": spent_cost,
            "edges_added": len(selected_edges),
            "inner_solves": inner_solves,
            "selected_edges": [f"{a}-{b}" for a, b in selected_edges],
        }

    def run_roi_greedy(self):
        """ROI / Cost-Weighted Greedy Outer Loop (Max Gain / Cost)"""
        constants = copy_network(self.constants)
        spent_cost = 0.0
        current_surplus = self.initial_surplus
        selected_edges = []
        inner_solves = 1

        for iteration in range(MAX_ITERATIONS):
            candidates = get_candidate_edges(constants, self.markets)
            if not candidates:
                break

            best_candidate = None
            best_roi = -float("inf")

            for candidate in candidates:
                edge_cost = get_edge_cost(constants, candidate)
                if spent_cost + edge_cost > self.expansion_budget:
                    continue

                inner_solves += 1
                res = evaluate_candidate(self.markets, constants, candidate)
                if res is None:
                    continue

                gain = res["surplus"] - current_surplus
                if gain > MIN_SURPLUS_GAIN:
                    roi = gain / edge_cost
                    if roi > best_roi:
                        best_roi = roi
                        best_candidate = res

            if best_candidate is None:
                break

            selected_edge = best_candidate["edge"]
            constants.connect(
                self.markets[selected_edge[0]], self.markets[selected_edge[1]]
            )
            selected_edges.append(selected_edge)
            spent_cost += get_edge_cost(constants, selected_edge)
            current_surplus = best_candidate["surplus"]

        return {
            "strategy": "ROI Greedy (Gain/Cost)",
            "final_surplus": current_surplus,
            "net_surplus_gain": current_surplus - self.initial_surplus,
            "expansion_cost_spent": spent_cost,
            "edges_added": len(selected_edges),
            "inner_solves": inner_solves,
            "selected_edges": [f"{a}-{b}" for a, b in selected_edges],
        }

    def run_epsilon_greedy(self, epsilon=0.10):
        """Epsilon-Greedy Outer Loop"""
        constants = copy_network(self.constants)
        spent_cost = 0.0
        current_surplus = self.initial_surplus
        selected_edges = []
        inner_solves = 1

        for iteration in range(MAX_ITERATIONS):
            candidates = get_candidate_edges(constants, self.markets)
            if not candidates:
                break

            eligible_results = []
            for candidate in candidates:
                edge_cost = get_edge_cost(constants, candidate)
                if spent_cost + edge_cost > self.expansion_budget:
                    continue

                inner_solves += 1
                res = evaluate_candidate(self.markets, constants, candidate)
                if res is None:
                    continue

                gain = res["surplus"] - current_surplus
                if gain > MIN_SURPLUS_GAIN:
                    eligible_results.append((gain, res))

            if not eligible_results:
                break

            # Epsilon-Greedy Choice
            if random.random() < epsilon:
                selected_candidate = random.choice(eligible_results)[1]
            else:
                eligible_results.sort(key=lambda x: x[0], reverse=True)
                selected_candidate = eligible_results[0][1]

            selected_edge = selected_candidate["edge"]
            constants.connect(
                self.markets[selected_edge[0]], self.markets[selected_edge[1]]
            )
            selected_edges.append(selected_edge)
            spent_cost += get_edge_cost(constants, selected_edge)
            current_surplus = selected_candidate["surplus"]

        return {
            "strategy": f"Epsilon-Greedy (eps={epsilon:.2f})",
            "final_surplus": current_surplus,
            "net_surplus_gain": current_surplus - self.initial_surplus,
            "expansion_cost_spent": spent_cost,
            "edges_added": len(selected_edges),
            "inner_solves": inner_solves,
            "selected_edges": [f"{a}-{b}" for a, b in selected_edges],
        }

    def run_ucb(self, c=1.0):
        """Upper Confidence Bound (UCB1) Outer Loop"""
        constants = copy_network(self.constants)
        spent_cost = 0.0
        current_surplus = self.initial_surplus
        selected_edges = []
        inner_solves = 1

        arm_counts = {normalize_edge(a, b): 0 for a, b in self.all_edges}
        arm_total_gain = {normalize_edge(a, b): 0.0 for a, b in self.all_edges}
        total_evaluations = 0

        for iteration in range(MAX_ITERATIONS):
            candidates = get_candidate_edges(constants, self.markets)
            if not candidates:
                break

            best_candidate = None
            best_ucb_val = -float("inf")

            for candidate in candidates:
                edge = normalize_edge(candidate[0], candidate[1])
                edge_cost = get_edge_cost(constants, candidate)
                if spent_cost + edge_cost > self.expansion_budget:
                    continue

                inner_solves += 1
                res = evaluate_candidate(self.markets, constants, candidate)
                if res is None:
                    continue

                gain = res["surplus"] - current_surplus
                if gain <= MIN_SURPLUS_GAIN:
                    continue

                total_evaluations += 1
                arm_counts[edge] += 1
                arm_total_gain[edge] += gain

                q_hat = arm_total_gain[edge] / arm_counts[edge]
                exploration_bonus = c * math.sqrt(
                    math.log(total_evaluations + 1) / arm_counts[edge]
                )
                ucb_val = q_hat + exploration_bonus

                if ucb_val > best_ucb_val:
                    best_ucb_val = ucb_val
                    best_candidate = res

            if best_candidate is None:
                break

            selected_edge = best_candidate["edge"]
            constants.connect(
                self.markets[selected_edge[0]], self.markets[selected_edge[1]]
            )
            selected_edges.append(selected_edge)
            spent_cost += get_edge_cost(constants, selected_edge)
            current_surplus = best_candidate["surplus"]

        return {
            "strategy": f"UCB1 (c={c:.2f})",
            "final_surplus": current_surplus,
            "net_surplus_gain": current_surplus - self.initial_surplus,
            "expansion_cost_spent": spent_cost,
            "edges_added": len(selected_edges),
            "inner_solves": inner_solves,
            "selected_edges": [f"{a}-{b}" for a, b in selected_edges],
        }


# ============================================================
# COMPREHENSIVE BENCHMARK RUNNER
# ============================================================


def run_comparative_benchmark():
    print("============================================================")
    print("MAB vs. GREEDY NETWORK EXPANSION BENCHMARK")
    print(f"Expansion Budget Multiplier: {BUDGET_MULTIPLIER}")
    print("============================================================")

    engine = NetworkExpansionEngine(
        budget_multiplier=BUDGET_MULTIPLIER, seed=RANDOM_SEED
    )

    results = []

    # 1. Baseline Pure Greedy
    print("\n[1/6] Running Pure Greedy Baseline...")
    results.append(engine.run_greedy())

    # 2. ROI Greedy
    print("[2/6] Running ROI Greedy (Gain / Cost)...")
    results.append(engine.run_roi_greedy())

    # 3. Epsilon-Greedy (eps = 0.10)
    print("[3/6] Running Epsilon-Greedy (eps=0.10)...")
    results.append(engine.run_epsilon_greedy(epsilon=0.10))

    # 4. Epsilon-Greedy (eps = 0.25)
    print("[4/6] Running Epsilon-Greedy (eps=0.25)...")
    results.append(engine.run_epsilon_greedy(epsilon=0.25))

    # 5. UCB1 (c = 0.50)
    print("[5/6] Running UCB1 (c=0.50)...")
    results.append(engine.run_ucb(c=0.50))

    # 6. UCB1 (c = 1.50)
    print("[6/6] Running UCB1 (c=1.50)...")
    results.append(engine.run_ucb(c=1.50))

    # Format output DataFrame
    df = pd.DataFrame(results)
    df["ROI (ΔW / Cost)"] = df["net_surplus_gain"] / (
        df["expansion_cost_spent"] + 1e-6
    )

    summary_df = df[
        [
            "strategy",
            "final_surplus",
            "net_surplus_gain",
            "expansion_cost_spent",
            "edges_added",
            "inner_solves",
            "ROI (ΔW / Cost)",
            "selected_edges",
        ]
    ].copy()

    summary_df.columns = [
        "Strategy",
        "Final Surplus",
        "Net Gain (ΔW)",
        "Cost Spent",
        "Edges Added",
        "Gurobi Solves",
        "ROI (ΔW / Cost)",
        "Added Edges",
    ]

    print("\n============================================================")
    print("FINAL SUMMARY & COMPARISON TABLE")
    print("============================================================")
    print(
        summary_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )
    print("============================================================")

    return summary_df, results


if __name__ == "__main__":
    summary_table, full_results = run_comparative_benchmark()