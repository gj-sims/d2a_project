# ============================================================
# D2A PROJECT
# Greedy Network Expansion using the existing Gurobi
# network equilibrium solver
#
# IMPORTANT:
#   - The inner equilibrium formulation is NOT changed.
#   - This file only controls the outer greedy expansion.
#   - Every candidate network is solved using the exact same
#     solve_network() function.
#
# Surplus-gain rule:
#   - An edge is only eligible if it increases surplus by
#     MORE THAN 0.50.
#
# BUDGET:
#   - The initial network is considered pre-existing.
#   - Initial connection costs DO NOT count against the budget.
#   - Only newly added edges are subtracted from the budget.
# ============================================================

from load_data import load_dfs
from markets import Market
from constants import Constants

from gurobi_v3_inner import (
    solve_network,
    extract_solution,
    calculate_surplus,
)

import numpy as np


# ============================================================
# SETTINGS
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


# ============================================================
# INITIAL NETWORK
# ============================================================

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


# ============================================================
# MARKET COORDINATES
#
# Used only by Constants.cost_to_create()
# ============================================================

COORDS = {
    "at":  (48.2085, 16.3721),
    "be":  (50.8505, 4.3488),
    "ger": (52.5200, 13.4050),
    "fr":  (48.8566, 2.3522),
    "nl":  (52.3700, 4.8900),
    "dk":  (55.6761, 12.5683),
    "fi":  (60.1700, 24.9400),
    "no":  (59.9100, 10.7500),
    "se":  (59.3300, 18.0600),
    "bg":  (42.7300, 25.4900),
    "lv":  (59.4370, 24.7540),
}


# ============================================================
# SETTINGS
# ============================================================

BUDGET_MULTIPLIER = 10.0
MAX_ITERATIONS = 50

# Only add an edge if it increases surplus by MORE than this.
MIN_SURPLUS_GAIN = 0.50


# ============================================================
# BUILD MARKETS
# ============================================================

def build_markets():

    dfs = load_dfs()

    markets = {}

    for name in MARKET_ORDER:

        print(name)

        market = Market(
            name,
            dfs[name]
        )

        # Coordinates are needed by Constants.distance()
        market.lat = COORDS[name][0]
        market.lon = COORDS[name][1]

        # Find autarky equilibrium
        market.find_price()

        markets[name] = market

        print("done")

    print("DONE")

    return markets


# ============================================================
# EDGE NORMALIZATION
# ============================================================

def normalize_edge(a, b):

    if MARKET_ORDER.index(a) < MARKET_ORDER.index(b):
        return (a, b)

    return (b, a)


# ============================================================
# ALL POSSIBLE EDGES
# ============================================================

def get_all_possible_edges(markets):

    edges = []

    for i in range(len(MARKET_ORDER)):

        for j in range(i + 1, len(MARKET_ORDER)):

            a = MARKET_ORDER[i]
            b = MARKET_ORDER[j]

            if a not in markets:
                continue

            if b not in markets:
                continue

            edges.append((a, b))

    return edges


# ============================================================
# CURRENT EDGES
# ============================================================

def get_current_edges(constants, markets):

    edges = []

    for i in range(len(MARKET_ORDER)):

        for j in range(i + 1, len(MARKET_ORDER)):

            a = MARKET_ORDER[i]
            b = MARKET_ORDER[j]

            index_a = constants.index_dict[a]
            index_b = constants.index_dict[b]

            if constants.connection_matrix[index_a][index_b] == 1:

                edges.append((a, b))

    return edges


# ============================================================
# CANDIDATE EDGES
# ============================================================

def get_candidate_edges(constants, markets):

    all_edges = get_all_possible_edges(
        markets
    )

    current_edges = get_current_edges(
        constants,
        markets
    )

    current_edges = {
        normalize_edge(a, b)
        for a, b in current_edges
    }

    candidates = []

    for edge in all_edges:

        edge = normalize_edge(
            edge[0],
            edge[1]
        )

        if edge not in current_edges:

            candidates.append(edge)

    return candidates


# ============================================================
# INITIALIZE EDGE COSTS
# ============================================================

def initialize_edge_costs(constants, markets):

    print()
    print("Calculating edge costs...")

    for i in range(len(MARKET_ORDER)):

        for j in range(i + 1, len(MARKET_ORDER)):

            a = MARKET_ORDER[i]
            b = MARKET_ORDER[j]

            constants.cost_to_create(
                markets[a],
                markets[b]
            )

    print("DONE")


# ============================================================
# GET EDGE COST
# ============================================================

def get_edge_cost(constants, edge):

    a, b = edge

    index_a = constants.index_dict[a]
    index_b = constants.index_dict[b]

    cost_ab = (
        constants.cost_to_create_matrix[
            index_a
        ][
            index_b
        ]
    )

    cost_ba = (
        constants.cost_to_create_matrix[
            index_b
        ][
            index_a
        ]
    )

    return (cost_ab + cost_ba) / 2.0


# ============================================================
# COPY NETWORK
# ============================================================

def copy_network(base_constants):

    constants = Constants()

    constants.connection_matrix = (
        base_constants.connection_matrix.copy()
    )

    constants.cost_to_create_matrix = (
        base_constants.cost_to_create_matrix.copy()
    )

    constants.transmission_loss_matrix = (
        base_constants.transmission_loss_matrix.copy()
    )

    constants.nodes = list(
        base_constants.nodes
    )

    return constants


# ============================================================
# SOLVE NETWORK
# ============================================================

def solve_current_network(markets, constants):

    # --------------------------------------------------------
    # EXACT INNER SOLVER
    # --------------------------------------------------------

    solution = solve_network(
        markets,
        constants
    )

    # --------------------------------------------------------
    # Extract the solution.
    # --------------------------------------------------------

    extracted = extract_solution(
        markets,
        constants,
        solution
    )

    # --------------------------------------------------------
    # calculate_surplus() expects only:
    #
    # extracted["markets"]
    # --------------------------------------------------------

    surplus = calculate_surplus(
        markets,
        extracted["markets"]
    )

    return (
        solution,
        extracted,
        surplus
    )


# ============================================================
# EVALUATE ONE CANDIDATE EDGE
# ============================================================

def evaluate_candidate(
    markets,
    base_constants,
    candidate
):

    # Make a copy so the actual network is untouched
    candidate_constants = copy_network(
        base_constants
    )

    a, b = candidate

    # Add candidate edge
    candidate_constants.connect(
        markets[a],
        markets[b]
    )

    try:

        (
            solution,
            extracted,
            surplus
        ) = solve_current_network(
            markets,
            candidate_constants
        )

    except Exception as e:

        print(
            f" -> FAILED: {e}"
        )

        return None

    return {
        "edge": candidate,
        "constants": candidate_constants,
        "solution": solution,
        "extracted": extracted,
        "surplus": surplus,
    }


# ============================================================
# GREEDY SEARCH
# ============================================================

def greedy_search(
    budget_multiplier=BUDGET_MULTIPLIER,
    max_iterations=MAX_ITERATIONS
):

    # ========================================================
    # BUILD MARKETS
    # ========================================================

    print()
    print("============================================================")
    print("BUILDING MARKETS")
    print("============================================================")

    markets = build_markets()

    # ========================================================
    # CREATE CONSTANTS
    # ========================================================

    np.random.seed(42)

    constants = Constants()

    # ========================================================
    # CALCULATE ALL EDGE COSTS
    # ========================================================

    initialize_edge_costs(
        constants,
        markets
    )

    # ========================================================
    # BUILD INITIAL NETWORK
    # ========================================================

    print()
    print("============================================================")
    print("INITIAL NETWORK")
    print("============================================================")

    for a, b in INITIAL_CONNECTIONS:

        print(
            f"Connecting {a} - {b}"
        )

        constants.connect(
            markets[a],
            markets[b]
        )

    # ========================================================
    # EDGE COUNT CHECK
    # ========================================================

    all_edges = get_all_possible_edges(
        markets
    )

    current_edges = get_current_edges(
        constants,
        markets
    )

    candidate_edges = get_candidate_edges(
        constants,
        markets
    )

    total_possible_edges = len(all_edges)

    print()
    print("============================================================")
    print("NETWORK EDGE COUNTS")
    print("============================================================")

    print(
        f"Total possible edges: {total_possible_edges}"
    )

    print(
        f"Existing edges: {len(current_edges)}"
    )

    print(
        f"Candidate edges: {len(candidate_edges)}"
    )

    print(
        f"Edge accounting: "
        f"{len(current_edges)} + "
        f"{len(candidate_edges)} = "
        f"{len(current_edges) + len(candidate_edges)}"
    )

    assert (
        len(current_edges)
        + len(candidate_edges)
        == total_possible_edges
    )

    # ========================================================
    # PRINT CURRENT CONNECTIONS
    # ========================================================

    print()
    print("Current connections:")

    for a, b in current_edges:

        print(
            f"  {a} - {b}"
        )

    # ========================================================
    # SOLVE INITIAL NETWORK
    # ========================================================

    print()
    print("============================================================")
    print("SOLVING INITIAL NETWORK")
    print("============================================================")

    (
        base_solution,
        base_extracted,
        base_surplus
    ) = solve_current_network(
        markets,
        constants
    )

    print()
    print(
        f"Initial network surplus: "
        f"{base_surplus:.6f}"
    )

    # ========================================================
    # BUDGET
    # ========================================================

    max_edge_cost = max(
        get_edge_cost(
            constants,
            edge
        )
        for edge in all_edges
    )

    budget = (
        budget_multiplier
        * max_edge_cost
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # The initial network already exists.
    # Its construction cost does NOT count against the
    # expansion budget.
    #
    # Only edges added by the greedy algorithm are counted.
    # --------------------------------------------------------

    total_cost = 0.0

    print()
    print("============================================================")
    print("BUDGET")
    print("============================================================")

    print(
        f"Maximum edge cost: "
        f"{max_edge_cost:.6f}"
    )

    print(
        f"Budget multiplier: "
        f"{budget_multiplier}"
    )

    print(
        f"Total expansion budget: "
        f"{budget:.6f}"
    )

    print(
        f"Initial network cost: "
        f"NOT COUNTED"
    )

    print(
        f"Added-edge cost so far: "
        f"{total_cost:.6f}"
    )

    print(
        f"Remaining budget: "
        f"{budget - total_cost:.6f}"
    )

    # ========================================================
    # GREEDY EXPANSION
    # ========================================================

    selected_edges = []

    iteration = 0

    while iteration < max_iterations:

        iteration += 1

        print()
        print()
        print("============================================================")
        print(
            f"ITERATION {iteration}"
        )
        print("============================================================")

        # ----------------------------------------------------
        # Get currently unconnected edges.
        # ----------------------------------------------------

        candidate_edges = get_candidate_edges(
            constants,
            markets
        )

        print()
        print(
            f"Remaining candidate edges: "
            f"{len(candidate_edges)}"
        )

        if len(candidate_edges) == 0:

            print(
                "No candidate edges remain."
            )

            break

        # ----------------------------------------------------
        # Track best edge.
        # ----------------------------------------------------

        best_candidate = None
        best_gain = -float("inf")

        # ----------------------------------------------------
        # Evaluate every candidate.
        # ----------------------------------------------------

        print()
        print("Evaluating candidate edges:")

        for candidate in candidate_edges:

            a, b = candidate

            edge_cost = get_edge_cost(
                constants,
                candidate
            )

            # ------------------------------------------------
            # Budget check
            #
            # total_cost contains ONLY costs of edges added
            # by the greedy algorithm.
            # ------------------------------------------------

            if total_cost + edge_cost > budget:

                print(
                    f"  {a} - {b} | "
                    f"cost={edge_cost:.2f} | "
                    f"SKIPPED - OVER BUDGET"
                )

                continue

            # ------------------------------------------------
            # Solve candidate network
            # ------------------------------------------------

            result = evaluate_candidate(
                markets,
                constants,
                candidate
            )

            if result is None:

                continue

            candidate_surplus = (
                result["surplus"]
            )

            gain = (
                candidate_surplus
                - base_surplus
            )

            print(
                f"  {a} - {b} | "
                f"cost={edge_cost:.2f} | "
                f"surplus={candidate_surplus:.6f} | "
                f"gain={gain:.6f}"
            )

            # ------------------------------------------------
            # Greedy criterion:
            #
            # Only consider edges with a surplus gain
            # STRICTLY GREATER than 0.50.
            #
            # Among those eligible edges, select the one
            # with the largest absolute surplus gain.
            # ------------------------------------------------

            if (
                gain > MIN_SURPLUS_GAIN
                and gain > best_gain
            ):

                best_gain = gain
                best_candidate = result

        # ====================================================
        # NO FEASIBLE EDGE
        # ====================================================

        if best_candidate is None:

            print()
            print(
                f"No candidate edge produces a surplus "
                f"gain greater than {MIN_SURPLUS_GAIN:.2f}."
            )

            break

        # ====================================================
        # SELECT BEST EDGE
        # ====================================================

        selected_edge = (
            best_candidate["edge"]
        )

        a, b = selected_edge

        edge_cost = get_edge_cost(
            constants,
            selected_edge
        )

        print()
        print("============================================================")
        print("SELECTED EDGE")
        print("============================================================")

        print(
            f"Selected edge: {a} - {b}"
        )

        print(
            f"Edge cost: {edge_cost:.6f}"
        )

        print(
            f"Surplus gain: {best_gain:.6f}"
        )

        print(
            f"New surplus: "
            f"{best_candidate['surplus']:.6f}"
        )

        # ====================================================
        # PERMANENTLY ADD EDGE
        # ====================================================

        constants.connect(
            markets[a],
            markets[b]
        )

        selected_edges.append(
            selected_edge
        )

        # ----------------------------------------------------
        # ONLY NEWLY ADDED EDGES ARE CHARGED TO THE BUDGET.
        # ----------------------------------------------------

        total_cost += edge_cost

        # ----------------------------------------------------
        # The candidate was already solved using exactly the
        # network we just accepted.
        #
        # Make that the new current equilibrium.
        # ----------------------------------------------------

        base_solution = (
            best_candidate["solution"]
        )

        base_extracted = (
            best_candidate["extracted"]
        )

        base_surplus = (
            best_candidate["surplus"]
        )

        # ====================================================
        # CURRENT NETWORK
        # ====================================================

        current_edges = get_current_edges(
            constants,
            markets
        )

        candidate_edges = get_candidate_edges(
            constants,
            markets
        )

        print()
        print("Current connections:")

        for a, b in current_edges:

            print(
                f"  {a} - {b}"
            )

        print()
        print(
            f"Total edges: "
            f"{len(current_edges)}"
        )

        print(
            f"Remaining candidates: "
            f"{len(candidate_edges)}"
        )

        print(
            f"Added-edge cost: "
            f"{total_cost:.6f}"
        )

        print(
            f"Remaining budget: "
            f"{budget - total_cost:.6f}"
        )

        print(
            f"Current surplus: "
            f"{base_surplus:.6f}"
        )

    # ========================================================
    # FINAL NETWORK
    # ========================================================

    print()
    print()
    print("============================================================")
    print("FINAL NETWORK")
    print("============================================================")

    final_edges = get_current_edges(
        constants,
        markets
    )

    print()
    print("Selected edges:")

    for a, b in selected_edges:

        print(
            f"  {a} - {b}"
        )

    print()
    print("All final connections:")

    for a, b in final_edges:

        print(
            f"  {a} - {b}"
        )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    final_candidates = get_candidate_edges(
        constants,
        markets
    )

    print()
    print("============================================================")
    print("FINAL SUMMARY")
    print("============================================================")

    print(
        f"Initial edges: "
        f"{len(INITIAL_CONNECTIONS)}"
    )

    print(
        f"Added edges: "
        f"{len(selected_edges)}"
    )

    print(
        f"Final edges: "
        f"{len(final_edges)}"
    )

    print(
        f"Total possible edges: "
        f"{len(all_edges)}"
    )

    print(
        f"Remaining candidate edges: "
        f"{len(final_candidates)}"
    )

    print(
        f"Added-edge cost: "
        f"{total_cost:.6f}"
    )

    print(
        f"Expansion budget: "
        f"{budget:.6f}"
    )

    print(
        f"Remaining budget: "
        f"{budget - total_cost:.6f}"
    )

    print(
        f"Final network surplus: "
        f"{base_surplus:.6f}"
    )

    # ========================================================
    # FINAL ACTIVE FLOWS
    # ========================================================

    print()
    print("============================================================")
    print("FINAL ACTIVE FLOWS")
    print("============================================================")

    # Use the solution already associated with the final
    # accepted network rather than changing the network again.

    for flow in base_extracted["flows"]:

        print(
            f"  {flow['source']} -> "
            f"{flow['destination']} | "
            f"flow={flow['flow']:.6f} | "
            f"received={flow['received']:.6f} | "
            f"loss={flow['loss']:.6f}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "markets": markets,
        "constants": constants,
        "selected_edges": selected_edges,
        "final_edges": final_edges,
        "solution": base_solution,
        "extracted": base_extracted,
        "surplus": base_surplus,

        # This is now ONLY the cost of newly added edges.
        "total_cost": total_cost,

        # This is the total budget available for new edges.
        "budget": budget,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    greedy_search(
        budget_multiplier=10.0,
        max_iterations=50
    )