import io
import contextlib
import numpy as np

from load_data import load_dfs
from markets import Market
from constants import Constants
from new_gurobi_atempt import solve_network_equilibrium


# ============================================================
# SETTINGS
# ============================================================

SKIP_MARKETS = {"ro", "pl"}

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


# ============================================================
# EXISTING NETWORK
# ============================================================

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


# ============================================================
# COORDINATES
# ============================================================

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


# ============================================================
# LOAD MARKET DATA ONCE
# ============================================================

print("Loading market data...")

DFS = load_dfs()

print("Market data loaded.")


# ============================================================
# CREATE BASE CONSTANTS ONCE
# ============================================================

print("Creating network constants...")

np.random.seed(42)

BASE_CONSTANTS = Constants()


# ============================================================
# CACHE COST MATRIX
# ============================================================

COST_INITIALIZED = False


def initialize_cost_matrix():

    global COST_INITIALIZED

    if COST_INITIALIZED:
        return

    markets = []

    for name in MARKET_ORDER:

        if name in SKIP_MARKETS:
            continue

        market = Market(
            name,
            DFS[name]
        )

        market.lat = COORDS[name][0]
        market.lon = COORDS[name][1]

        markets.append(market)

    for i in range(len(markets)):

        for j in range(i + 1, len(markets)):

            BASE_CONSTANTS.cost_to_create(
                markets[i],
                markets[j]
            )

    COST_INITIALIZED = True


initialize_cost_matrix()


# ============================================================
# CACHE AUTARKY PRICES
# ============================================================

AUTARKY_PRICES = {}


def initialize_autarky_prices():

    if len(AUTARKY_PRICES) > 0:
        return

    print("Calculating autarky prices...")

    for name in MARKET_ORDER:

        if name in SKIP_MARKETS:
            continue

        market = Market(
            name,
            DFS[name]
        )

        market.find_price()

        AUTARKY_PRICES[name] = market.price

    print("Autarky prices calculated.")


initialize_autarky_prices()


# ============================================================
# BUILD PROBLEM
# ============================================================

def build_problem(extra_edges=()):

    problem = Constants()

    # Reuse the same transmission-loss matrix.
    problem.transmission_loss_matrix = (
        BASE_CONSTANTS.transmission_loss_matrix.copy()
    )

    # Reuse the same cost matrix.
    problem.cost_to_create_matrix = (
        BASE_CONSTANTS.cost_to_create_matrix.copy()
    )

    markets = []

    for name in MARKET_ORDER:

        if name in SKIP_MARKETS:
            continue

        market = Market(
            name,
            DFS[name]
        )

        market.lat = COORDS[name][0]
        market.lon = COORDS[name][1]

        # Reuse cached autarky price.
        market.price = AUTARKY_PRICES[name]

        markets.append(market)

    problem.nodes = markets

    # Fast lookup.
    market_lookup = {}

    for market in markets:
        market_lookup[market.name] = market

    # ========================================================
    # EXISTING NETWORK
    # ========================================================

    for left, right in CONNECTED_EDGES:

        if left in SKIP_MARKETS or right in SKIP_MARKETS:
            continue

        left_market = market_lookup.get(left)
        right_market = market_lookup.get(right)

        if left_market is not None and right_market is not None:

            problem.connect(
                left_market,
                right_market
            )

    # ========================================================
    # NEW EDGES
    # ========================================================

    for left, right in extra_edges:

        if left in SKIP_MARKETS or right in SKIP_MARKETS:
            continue

        left_market = market_lookup.get(left)
        right_market = market_lookup.get(right)

        if left_market is not None and right_market is not None:

            problem.connect(
                left_market,
                right_market
            )

    return problem, markets


# ============================================================
# SOLVE QUIETLY
# ============================================================

def solve_quietly(problem):

    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer):

        model = solve_network_equilibrium(
            problem.nodes,
            problem,
            verbose=False
        )

    return model


# ============================================================
# EDGE COST
# ============================================================

def edge_cost(problem, left, right):

    i = problem.index_dict[left]
    j = problem.index_dict[right]

    return float(
        (
            problem.cost_to_create_matrix[i][j]
            +
            problem.cost_to_create_matrix[j][i]
        ) / 2.0
    )


# ============================================================
# CANDIDATE EDGES
# ============================================================

def candidate_edges(problem, selected_edges):

    candidates = []

    active_markets = []

    for market in problem.nodes:

        if market.name in SKIP_MARKETS:
            continue

        active_markets.append(
            market.name
        )

    for i in range(len(active_markets)):

        for j in range(i + 1, len(active_markets)):

            left = active_markets[i]
            right = active_markets[j]

            edge = (left, right)

            if edge in selected_edges:
                continue

            if (right, left) in selected_edges:
                continue

            left_index = problem.index_dict[left]
            right_index = problem.index_dict[right]

            if (
                problem.connection_matrix[
                    left_index
                ][
                    right_index
                ] == 1
            ):
                continue

            candidates.append(edge)

    return candidates


# ============================================================
# EVALUATE ONE CANDIDATE
# ============================================================

def evaluate_candidate(
    selected_edges,
    candidate
):

    if (
        candidate[0] in SKIP_MARKETS
        or candidate[1] in SKIP_MARKETS
    ):
        return (
            None,
            None,
            -np.inf,
            None
        )

    test_edges = list(
        selected_edges
    )

    test_edges.append(
        candidate
    )

    test_problem, test_markets = build_problem(
        test_edges
    )

    test_model = solve_quietly(
        test_problem
    )

    if test_model is None:

        return (
            None,
            None,
            -np.inf,
            None
        )

    test_surplus = float(
        test_model.ObjVal
    )

    test_cost = edge_cost(
        test_problem,
        candidate[0],
        candidate[1]
    )

    return (
        test_problem,
        test_model,
        test_surplus,
        test_cost
    )


# ============================================================
# GREEDY SEARCH
# ============================================================

def greedy_search(
    budget_multiplier=10.0,
    max_iterations=50
):

    # ========================================================
    # BASE NETWORK
    # ========================================================

    print()
    print("Building base network...")

    base_problem, base_markets = build_problem()

    print("Solving base network...")

    base_model = solve_quietly(
        base_problem
    )

    if base_model is None:

        print(
            "Base network could not be solved."
        )

        return

    base_surplus = float(
        base_model.ObjVal
    )

    # ========================================================
    # BUDGET
    # ========================================================

    budget = (
        budget_multiplier
        *
        float(
            np.max(
                base_problem.cost_to_create_matrix
            )
        )
    )

    total_cost = 0.0

    selected_edges = set()

    # ========================================================
    # HEADER
    # ========================================================

    print()
    print("========================================")
    print("GREEDY NETWORK EXPANSION")
    print("========================================")
    print()

    print(
        "Initial systemwide surplus:",
        base_surplus
    )

    print(
        "Budget:",
        budget
    )

    print()

    # ========================================================
    # GREEDY ITERATIONS
    # ========================================================

    def _fmt_price(value):
        return "None" if value is None else f"{float(value):.4f}"

    for iteration in range(
        max_iterations
    ):

        print(
            "----------------------------------------"
        )

        print(
            "Iteration:",
            iteration + 1
        )

        print(
            "----------------------------------------"
        )

        candidates = candidate_edges(
            base_problem,
            selected_edges
        )

        if len(candidates) == 0:

            print(
                "No candidate edges remain."
            )

            break

        print(
            "Candidate edges:",
            len(candidates)
        )

        best_edge = None
        best_problem = None
        best_model = None
        best_edge_cost = None
        best_edge_gain = -np.inf
        best_surplus = None

        # ====================================================
        # EVALUATE CANDIDATES
        # ====================================================

        for candidate in candidates:

            (
                test_problem,
                test_model,
                test_surplus,
                test_cost
            ) = evaluate_candidate(
                selected_edges,
                candidate
            )

            if test_model is None:
                continue

            if (
                total_cost
                +
                test_cost
                >
                budget
            ):
                continue

            gain = (
                test_surplus
                -
                base_surplus
            )

            print(
                candidate,
                "| cost:",
                test_cost,
                "| gain:",
                gain,
                "| new total surplus:",
                test_surplus
            )

            if gain > best_edge_gain:

                best_edge = candidate
                best_problem = test_problem
                best_model = test_model
                best_edge_cost = test_cost
                best_edge_gain = gain
                best_surplus = test_surplus

        # ====================================================
        # NO FEASIBLE CANDIDATE
        # ====================================================

        if best_edge is None:

            print()
            print(
                "No affordable candidate edges remain."
            )

            break

        # ====================================================
        # NO POSITIVE GAIN
        # ====================================================

        if best_edge_gain <= 0:

            print()
            print(
                "No remaining affordable edge increases "
                "systemwide surplus."
            )

            break

        # ====================================================
        # SAVE OLD SURPLUS BEFORE UPDATING
        # ========================================================

        old_surplus = base_surplus

        # ====================================================
        # ACCEPT BEST EDGE
        # ========================================================

        selected_edges.add(
            best_edge
        )

        total_cost += (
            best_edge_cost
        )

        # The selected candidate is already solved,
        # so do not solve it again.

        base_problem = best_problem
        base_model = best_model

        base_surplus = float(
            best_model.ObjVal
        )

        # ====================================================
        # REPORT SELECTED EDGE
        # ========================================================

        print()

        print(
            "========================================"
        )

        print(
            "SELECTED EDGE"
        )

        print(
            "========================================"
        )

        print(
            "Edge:",
            best_edge
        )

        print(
            "Edge cost:",
            best_edge_cost
        )

        print(
            "Previous total surplus:",
            old_surplus
        )

        print(
            "Surplus gain:",
            best_edge_gain
        )

        print(
            "NEW TOTAL SURPLUS:",
            base_surplus
        )

        print(
            "Total network-expansion cost:",
            total_cost
        )

        print(
            "Remaining budget:",
            budget - total_cost
        )

        print()

        # ====================================================
        # EQUILIBRIUM PRICES
        # ====================================================

        print(
            "Updated equilibrium prices after this edge:"
        )

        for market in base_problem.nodes:

            if market.name in SKIP_MARKETS:
                continue

            print(
                market.name,
                ":",
                _fmt_price(market.adj_price)
            )

        print()

    # ========================================================
    # FINAL NETWORK
    # ========================================================

    print()
    print(
        "========================================"
    )

    print(
        "FINAL NETWORK"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Selected new edges:"
    )

    for edge in selected_edges:

        print(
            edge
        )

    print()

    print(
        "Total new-edge cost:",
        total_cost
    )

    print(
        "Budget:",
        budget
    )

    print(
        "Remaining budget:",
        budget - total_cost
    )

    print()

    print(
        "FINAL SYSTEMWIDE SURPLUS:",
        base_surplus
    )

    print()

    print(
        "Final equilibrium prices:"
    )

    for market in base_problem.nodes:

        if market.name in SKIP_MARKETS:
            continue

        print(
            market.name,
            ":",
            _fmt_price(market.adj_price)
        )

    print()

    return (
        selected_edges,
        base_problem,
        base_model
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    greedy_search(
        budget_multiplier=10.0,
        max_iterations=50
    )
