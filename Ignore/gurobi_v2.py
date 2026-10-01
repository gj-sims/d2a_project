# ============================================================
# D2A PROJECT
# Network Equilibrium using Gurobi PWL step functions
#
# Existing files NOT modified:
#   - markets.py
#   - constants.py
#   - load_data.py
#
# Poland (pl) and Romania (ro) are skipped.
#
# Goal:
#   1. Find base/autarky equilibrium
#   2. Find equilibrium for a given network
#   3. Recover adjusted prices
#   4. Calculate surplus at the adjusted network allocation
#   5. Report surplus gain relative to autarky
#
# No Gurobi duals (.Pi / .pi) are used.
# ============================================================

from load_data import load_dfs
from markets import Market
from constants import Constants

import gurobipy as gp
from gurobipy import GRB
from scipy.integrate import quad
import numpy as np


# ============================================================
# SETTINGS
# ============================================================

SKIP_MARKETS = {"pl", "ro"}

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
# BUILD MARKETS
# ============================================================

def build_markets():

    dfs = load_dfs()

    markets = {}

    for name in MARKET_ORDER:

        if name in SKIP_MARKETS:
            continue

        market = Market(
            name,
            dfs[name]
        )

        # Base/autarky equilibrium
        market.find_price()

        markets[name] = market

        print(name, "done")

    return markets


# ============================================================
# DIRECT WELFARE
# ============================================================
#
# Social surplus is:
#
#     total demand benefit
#     -
#     total production cost
#
# This does NOT use any CS/PS methods from markets.py.
#
# quantities[name]["production"]
# quantities[name]["consumption"]
# contain the actual quantities to evaluate.
# ============================================================

def calculate_surplus(
    markets,
    quantities
):

    total_surplus = 0.0

    for name, market in markets.items():

        production = (
            quantities[name]["production"]
        )

        consumption = (
            quantities[name]["consumption"]
        )

        # ----------------------------------------------------
        # Demand benefit
        # ----------------------------------------------------

        demand_min = (
            market.demand_function.x.min()
        )

        demand_benefit, _ = quad(
            market.demand_function,
            demand_min,
            consumption
        )

        # ----------------------------------------------------
        # Production cost
        # ----------------------------------------------------

        supply_min = (
            market.supply_function.x.min()
        )

        production_cost, _ = quad(
            market.supply_function,
            supply_min,
            production
        )

        total_surplus += (
            demand_benefit
            -
            production_cost
        )

    return total_surplus


# ============================================================
# AUTARKY
# ============================================================

def solve_autarky(markets):

    print()
    print("=" * 70)
    print("AUTARKY")
    print("=" * 70)

    autarky_quantities = {}

    for name in MARKET_ORDER:

        if name not in markets:
            continue

        market = markets[name]

        autarky_quantities[name] = {
            "production":
                float(market.quantity),

            "consumption":
                float(market.quantity)
        }

    total_surplus = calculate_surplus(
        markets,
        autarky_quantities
    )

    print()

    for name in MARKET_ORDER:

        if name not in markets:
            continue

        market = markets[name]

        print(
            f"{name:>4} | "
            f"price={market.price:.6f} | "
            f"quantity={market.quantity:.6f}"
        )

    print("-" * 70)

    print(
        f"TOTAL AUTARKY SURPLUS: "
        f"{total_surplus:.6f}"
    )

    return total_surplus


# ============================================================
# CURVE HELPERS
# ============================================================

def get_curve(
    market,
    curve_type
):

    if curve_type == "supply":
        return market.supply

    if curve_type == "demand":
        return market.demand

    raise ValueError(
        "curve_type must be supply or demand"
    )


def get_curve_domain(
    market,
    curve_type
):

    curve = get_curve(
        market,
        curve_type
    )

    return (
        float(curve["quantity"].min()),
        float(curve["quantity"].max())
    )


# ============================================================
# BUILD PWL BLOCKS
# ============================================================

def build_blocks(
    market,
    curve_type
):

    curve = get_curve(
        market,
        curve_type
    )

    quantities = list(
        curve["quantity"]
    )

    prices = list(
        curve["price"]
    )

    blocks = []

    for i in range(
        len(quantities) - 1
    ):

        left = float(
            quantities[i]
        )

        right = float(
            quantities[i + 1]
        )

        price = float(
            prices[i]
        )

        capacity = right - left

        if capacity <= 0:
            continue

        blocks.append({
            "left": left,
            "right": right,
            "capacity": capacity,
            "price": price
        })

    return blocks


# ============================================================
# ADD PWL VARIABLES
# ============================================================
#
# The blocks represent a step function.
#
# They therefore MUST be filled in order.
#
# Example:
#
#     block 0 capacity = 100
#     block 1 capacity = 100
#     block 2 capacity = 100
#
# Valid:
#
#     block 0 = 100
#     block 1 = 50
#     block 2 = 0
#
# Invalid:
#
#     block 0 = 20
#     block 1 = 50
#
# because block 1 cannot be used until block 0
# has been completely filled.
# ============================================================

def add_curve_variables(
    model,
    market,
    curve_type
):

    blocks = build_blocks(
        market,
        curve_type
    )

    variables = []
    completed = []

    for i, block in enumerate(blocks):

        variable = model.addVar(
            lb=0.0,
            ub=block["capacity"],
            name=(
                f"{curve_type}_"
                f"{market.name}_"
                f"{i}"
            )
        )

        variables.append(
            variable
        )

        # ----------------------------------------------------
        # Every block except the last gets a binary variable
        # indicating whether it has been completely filled.
        # ----------------------------------------------------

        if i < len(blocks) - 1:

            binary = model.addVar(
                vtype=GRB.BINARY,
                name=(
                    f"{curve_type}_"
                    f"{market.name}_"
                    f"complete_{i}"
                )
            )

            completed.append(
                binary
            )

            # If this block is marked complete,
            # it must actually be full.
            model.addConstr(
                variable
                >=
                block["capacity"] * binary,
                name=(
                    f"{curve_type}_"
                    f"{market.name}_"
                    f"fill_{i}"
                )
            )

            # If this block is not complete,
            # the next block cannot be used.
            #
            # This is added after all variables exist.
            #
            # It is equivalent to:
            #
            # next_block <= next_capacity * completed
            #

    # --------------------------------------------------------
    # Enforce sequential filling
    # --------------------------------------------------------

    for i in range(
        len(blocks) - 1
    ):

        model.addConstr(
            variables[i + 1]
            <=
            blocks[i + 1]["capacity"]
            *
            completed[i],
            name=(
                f"{curve_type}_"
                f"{market.name}_"
                f"order_{i}"
            )
        )

    model.update()

    return (
        variables,
        blocks
    )


# ============================================================
# ADD TOTAL QUANTITY
# ============================================================

def add_quantity_constraint(
    model,
    market,
    curve_type,
    variables,
    blocks
):

    min_quantity, max_quantity = (
        get_curve_domain(
            market,
            curve_type
        )
    )

    quantity = model.addVar(
        lb=min_quantity,
        ub=max_quantity,
        name=(
            f"{curve_type}_quantity_"
            f"{market.name}"
        )
    )

    model.addConstr(
        quantity
        ==
        min_quantity
        +
        gp.quicksum(variables),
        name=(
            f"{curve_type}_quantity_definition_"
            f"{market.name}"
        )
    )

    return quantity


# ============================================================
# GET NETWORK EDGES
# ============================================================

def get_edges(
    markets,
    constants
):

    edges = []

    seen = set()

    for name_i in MARKET_ORDER:

        if name_i not in markets:
            continue

        i_index = constants.index_dict[
            name_i
        ]

        for name_j in MARKET_ORDER:

            if name_j not in markets:
                continue

            if name_i == name_j:
                continue

            j_index = constants.index_dict[
                name_j
            ]

            if (
                constants.connection_matrix[
                    i_index
                ][
                    j_index
                ]
                != 1
            ):
                continue

            key = tuple(
                sorted(
                    [name_i, name_j]
                )
            )

            if key in seen:
                continue

            seen.add(key)

            edges.append(
                (name_i, name_j)
            )

    return edges


# ============================================================
# TRANSMISSION LOSS
# ============================================================

def get_transmission_loss(
    constants,
    source,
    destination
):

    source_index = constants.index_dict[
        source
    ]

    destination_index = constants.index_dict[
        destination
    ]

    return float(
        constants.transmission_loss_matrix[
            source_index
        ][
            destination_index
        ]
    )


# ============================================================
# BUILD NETWORK MODEL
# ============================================================

def build_network_model(
    markets,
    constants
):

    model = gp.Model(
        "network_equilibrium"
    )

    model.Params.OutputFlag = 0

    production = {}
    consumption = {}

    supply_variables = {}
    demand_variables = {}

    supply_blocks = {}
    demand_blocks = {}

    # --------------------------------------------------------
    # Market quantities
    # --------------------------------------------------------

    for name, market in markets.items():

        (
            supply_variables[name],
            supply_blocks[name]
        ) = add_curve_variables(
            model,
            market,
            "supply"
        )

        production[name] = (
            add_quantity_constraint(
                model,
                market,
                "supply",
                supply_variables[name],
                supply_blocks[name]
            )
        )

        (
            demand_variables[name],
            demand_blocks[name]
        ) = add_curve_variables(
            model,
            market,
            "demand"
        )

        consumption[name] = (
            add_quantity_constraint(
                model,
                market,
                "demand",
                demand_variables[name],
                demand_blocks[name]
            )
        )

    # --------------------------------------------------------
    # Network flows
    # --------------------------------------------------------

    edges = get_edges(
        markets,
        constants
    )

    flow = {}
    direction = {}

    for a, b in edges:

        flow[(a, b)] = model.addVar(
            lb=0.0,
            name=f"flow_{a}_{b}"
        )

        flow[(b, a)] = model.addVar(
            lb=0.0,
            name=f"flow_{b}_{a}"
        )

        direction[(a, b)] = model.addVar(
            vtype=GRB.BINARY,
            name=f"direction_{a}_{b}"
        )

        model.addConstr(
            flow[(a, b)]
            <=
            GRB.INFINITY
            *
            direction[(a, b)],
            name=(
                f"direction_forward_"
                f"{a}_{b}"
            )
        )

        model.addConstr(
            flow[(b, a)]
            <=
            GRB.INFINITY
            *
            (
                1
                -
                direction[(a, b)]
            ),
            name=(
                f"direction_reverse_"
                f"{a}_{b}"
            )
        )

    # --------------------------------------------------------
    # Market balances
    # --------------------------------------------------------

    for name in markets:

        imports = []
        exports = []

        for a, b in edges:

            # a -> b

            if name == b:

                loss = get_transmission_loss(
                    constants,
                    a,
                    b
                )

                imports.append(
                    loss
                    *
                    flow[(a, b)]
                )

            if name == a:

                exports.append(
                    flow[(a, b)]
                )

            # b -> a

            if name == a:

                loss = get_transmission_loss(
                    constants,
                    b,
                    a
                )

                imports.append(
                    loss
                    *
                    flow[(b, a)]
                )

            if name == b:

                exports.append(
                    flow[(b, a)]
                )

        model.addConstr(
            production[name]
            +
            gp.quicksum(imports)
            ==
            consumption[name]
            +
            gp.quicksum(exports),
            name=f"balance_{name}"
        )

    # --------------------------------------------------------
    # WELFARE OBJECTIVE
    # --------------------------------------------------------
    #
    # Maximize:
    #
    #       total demand benefit
    #       -
    #       total supply cost
    #
    # Because the PWL blocks are now forced to be filled
    # sequentially, these block areas correctly represent
    # the integral of the step functions from their minimum
    # observed quantity.
    #
    # No .Pi / .pi is used.
    # --------------------------------------------------------

    objective = 0.0

    for name in markets:

        # ----------------------------------------------------
        # Demand benefit
        # ----------------------------------------------------

        for variable, block in zip(
            demand_variables[name],
            demand_blocks[name]
        ):

            objective += (
                block["price"]
                *
                variable
            )

        # ----------------------------------------------------
        # Supply cost
        # ----------------------------------------------------

        for variable, block in zip(
            supply_variables[name],
            supply_blocks[name]
        ):

            objective -= (
                block["price"]
                *
                variable
            )

    model.setObjective(
        objective,
        GRB.MAXIMIZE
    )

    model.update()

    return (
        model,
        production,
        consumption,
        supply_variables,
        demand_variables,
        flow,
        edges
    )


# ============================================================
# SOLVE NETWORK
# ============================================================

def solve_network(
    markets,
    constants
):

    (
        model,
        production,
        consumption,
        supply_variables,
        demand_variables,
        flow,
        edges
    ) = build_network_model(
        markets,
        constants
    )

    model.optimize()

    if model.Status != GRB.OPTIMAL:

        print(
            "Gurobi status:",
            model.Status
        )

        raise RuntimeError(
            "Network optimization did not "
            "reach optimality."
        )

    return {
        "model": model,
        "production": production,
        "consumption": consumption,
        "supply_variables": supply_variables,
        "demand_variables": demand_variables,
        "flow": flow,
        "edges": edges
    }


# ============================================================
# EXTRACT SOLUTION
# ============================================================

def extract_solution(
    markets,
    constants,
    solution
):

    model = solution["model"]

    production = solution[
        "production"
    ]

    consumption = solution[
        "consumption"
    ]

    flow = solution["flow"]
    edges = solution["edges"]

    results = {
        "objective": model.ObjVal,
        "markets": {},
        "flows": []
    }

    # --------------------------------------------------------
    # Market quantities
    # --------------------------------------------------------

    for name in markets:

        production_value = (
            production[name].X
        )

        consumption_value = (
            consumption[name].X
        )

        results["markets"][name] = {
            "production":
                production_value,

            "consumption":
                consumption_value,

            "net":
                production_value
                -
                consumption_value
        }

    # --------------------------------------------------------
    # Active flows
    # --------------------------------------------------------

    for a, b in edges:

        forward = flow[
            (a, b)
        ].X

        reverse = flow[
            (b, a)
        ].X

        if forward > 1e-6:

            loss = get_transmission_loss(
                constants,
                a,
                b
            )

            results["flows"].append({
                "source": a,
                "destination": b,
                "flow": forward,
                "received":
                    forward * loss,
                "loss": loss
            })

        if reverse > 1e-6:

            loss = get_transmission_loss(
                constants,
                b,
                a
            )

            results["flows"].append({
                "source": b,
                "destination": a,
                "flow": reverse,
                "received":
                    reverse * loss,
                "loss": loss
            })

    return results


# ============================================================
# PRICE SUPPORT
# ============================================================

def supply_price_support(
    market,
    quantity
):

    curve = market.supply

    x = list(
        curve["quantity"]
    )

    y = list(
        curve["price"]
    )

    if quantity <= x[0]:
        return [float(y[0])]

    for i in range(
        len(x) - 1
    ):

        if quantity <= (
            x[i + 1] + 1e-7
        ):

            return [
                float(y[i]),
                float(y[i + 1])
            ]

    return [
        float(y[-1])
    ]


def demand_price_support(
    market,
    quantity
):

    curve = market.demand

    x = list(
        curve["quantity"]
    )

    y = list(
        curve["price"]
    )

    if quantity <= x[0]:
        return [float(y[0])]

    for i in range(
        len(x) - 1
    ):

        if quantity <= (
            x[i + 1] + 1e-7
        ):

            return [
                float(y[i]),
                float(y[i + 1])
            ]

    return [
        float(y[-1])
    ]


# ============================================================
# RECOVER ADJUSTED PRICES
# ============================================================

def recover_prices(
    markets,
    constants,
    network_solution
):

    local_support = {}

    for name, market in markets.items():

        production = (
            network_solution["markets"][name][
                "production"
            ]
        )

        consumption = (
            network_solution["markets"][name][
                "consumption"
            ]
        )

        local_support[name] = {
            "supply":
                supply_price_support(
                    market,
                    production
                ),

            "demand":
                demand_price_support(
                    market,
                    consumption
                )
        }

    lower = {}
    upper = {}

    # --------------------------------------------------------
    # Initial feasible price intervals
    # --------------------------------------------------------

    for name in markets:

        supply_prices = (
            local_support[name]["supply"]
        )

        demand_prices = (
            local_support[name]["demand"]
        )

        lower[name] = min(
            supply_prices
        )

        upper[name] = max(
            demand_prices
        )

        if lower[name] > upper[name]:

            lower[name], upper[name] = (
                upper[name],
                lower[name]
            )

    # --------------------------------------------------------
    # Enforce price relationships across active flows.
    #
    # If i sends to j:
    #
    #     P_i = loss * P_j
    #
    # --------------------------------------------------------

    changed = True

    while changed:

        changed = False

        for active in network_solution["flows"]:

            source = active[
                "source"
            ]

            destination = active[
                "destination"
            ]

            loss = active[
                "loss"
            ]

            if loss <= 0:
                continue

            new_source_lower = (
                loss
                *
                lower[destination]
            )

            new_source_upper = (
                loss
                *
                upper[destination]
            )

            new_destination_lower = (
                lower[source]
                /
                loss
            )

            new_destination_upper = (
                upper[source]
                /
                loss
            )

            old_values = (
                lower[source],
                upper[source],
                lower[destination],
                upper[destination]
            )

            lower[source] = max(
                lower[source],
                new_source_lower
            )

            upper[source] = min(
                upper[source],
                new_source_upper
            )

            lower[destination] = max(
                lower[destination],
                new_destination_lower
            )

            upper[destination] = min(
                upper[destination],
                new_destination_upper
            )

            new_values = (
                lower[source],
                upper[source],
                lower[destination],
                upper[destination]
            )

            if any(
                abs(a - b) > 1e-8
                for a, b in zip(
                    old_values,
                    new_values
                )
            ):

                changed = True

    # --------------------------------------------------------
    # Pick midpoint of remaining interval
    # --------------------------------------------------------

    prices = {}

    for name in markets:

        prices[name] = (
            lower[name]
            +
            upper[name]
        ) / 2.0

    return prices


# ============================================================
# ZERO-FLOW AUTARKY TEST
# ============================================================

def test_zero_flow(
    markets,
    constants,
    autarky_surplus
):

    print()
    print("=" * 70)
    print("ZERO-FLOW AUTARKY FEASIBILITY TEST")
    print("=" * 70)

    (
        model,
        production,
        consumption,
        supply_variables,
        demand_variables,
        flow,
        edges
    ) = build_network_model(
        markets,
        constants
    )

    # --------------------------------------------------------
    # Force every directional flow to zero.
    #
    # This is ONLY a diagnostic test.
    # It is not part of the actual network model.
    # --------------------------------------------------------

    for key in flow:

        model.addConstr(
            flow[key] == 0,
            name=f"zero_flow_{key[0]}_{key[1]}"
        )

    model.optimize()

    if model.Status != GRB.OPTIMAL:

        print(
            "ZERO-FLOW TEST FAILED:"
        )

        print(
            "The network model cannot reproduce "
            "a zero-trade allocation."
        )

        return False

    max_error = 0.0

    zero_flow_quantities = {}

    print()

    for name, market in markets.items():

        q_production = (
            production[name].X
        )

        q_consumption = (
            consumption[name].X
        )

        production_error = (
            q_production
            -
            market.quantity
        )

        consumption_error = (
            q_consumption
            -
            market.quantity
        )

        max_error = max(
            max_error,
            abs(production_error),
            abs(consumption_error)
        )

        zero_flow_quantities[name] = {
            "production":
                q_production,

            "consumption":
                q_consumption
        }

        print(
            f"{name:>4} | "
            f"base={market.quantity:.6f} | "
            f"production={q_production:.6f} | "
            f"consumption={q_consumption:.6f} | "
            f"prod_error={production_error:.8f} | "
            f"cons_error={consumption_error:.8f}"
        )

    zero_flow_surplus = calculate_surplus(
        markets,
        zero_flow_quantities
    )

    print("-" * 70)

    print(
        f"MAX QUANTITY ERROR: "
        f"{max_error:.10f}"
    )

    print(
        f"ZERO-FLOW OBJECTIVE: "
        f"{model.ObjVal:.6f}"
    )

    print(
        f"ZERO-FLOW SURPLUS: "
        f"{zero_flow_surplus:.6f}"
    )

    print(
        f"AUTARKY SURPLUS: "
        f"{autarky_surplus:.6f}"
    )

    print(
        f"SURPLUS DIFFERENCE: "
        f"{zero_flow_surplus - autarky_surplus:.6f}"
    )

    return True


# ============================================================
# BALANCE CHECK
# ============================================================

def check_balances(
    markets,
    network_solution
):

    print()
    print("=" * 70)
    print("BALANCE CHECK")
    print("=" * 70)

    max_error = 0.0

    for name in markets:

        result = (
            network_solution["markets"][name]
        )

        production = (
            result["production"]
        )

        consumption = (
            result["consumption"]
        )

        imports = 0.0
        exports = 0.0

        for active in (
            network_solution["flows"]
        ):

            if active[
                "destination"
            ] == name:

                imports += active[
                    "received"
                ]

            if active[
                "source"
            ] == name:

                exports += active[
                    "flow"
                ]

        lhs = (
            production
            +
            imports
        )

        rhs = (
            consumption
            +
            exports
        )

        error = lhs - rhs

        max_error = max(
            max_error,
            abs(error)
        )

        print(
            f"{name:>4} | "
            f"production={production:.6f} | "
            f"consumption={consumption:.6f} | "
            f"imports={imports:.6f} | "
            f"exports={exports:.6f} | "
            f"error={error:.10f}"
        )

    print("-" * 70)

    print(
        f"MAX BALANCE ERROR: "
        f"{max_error:.10f}"
    )

    return max_error


# ============================================================
# PRINT NETWORK SOLUTION
# ============================================================

def print_network_solution(
    markets,
    network_solution,
    prices
):

    print()
    print("=" * 70)
    print("NETWORK EQUILIBRIUM")
    print("=" * 70)

    print()
    print("MARKETS")
    print("-" * 70)

    for name in MARKET_ORDER:

        if name not in markets:
            continue

        result = (
            network_solution["markets"][name]
        )

        print(
            f"{name:>4} | "
            f"price={prices[name]:.6f} | "
            f"production={result['production']:.6f} | "
            f"consumption={result['consumption']:.6f} | "
            f"net={result['net']:.6f}"
        )

    print()
    print("ACTIVE FLOWS")
    print("-" * 70)

    for active in network_solution["flows"]:

        print(
            f"{active['source']:>4} -> "
            f"{active['destination']:<4} | "
            f"sent={active['flow']:.6f} | "
            f"received={active['received']:.6f} | "
            f"loss={active['loss']:.6f}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Build markets
    # --------------------------------------------------------

    markets = build_markets()

    print("DONE")

    # --------------------------------------------------------
    # Build network
    # --------------------------------------------------------
    np.random.seed(42)
    constants = Constants()

    # --------------------------------------------------------
    # TEST CASE
    #
    # Start with DK/LV only.
    #
    # Once this behaves correctly, replace this with the
    # larger network.
    # --------------------------------------------------------

    # connections = [
    #     ("dk", "lv")
    # ]

    connections = [
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

    for a, b in connections:

        constants.connect(
            markets[a],
            markets[b]
        )

    # --------------------------------------------------------
    # BASE CASE
    # --------------------------------------------------------

    autarky_surplus = solve_autarky(
        markets
    )

    # --------------------------------------------------------
    # ZERO-FLOW TEST
    # --------------------------------------------------------

    test_zero_flow(
        markets,
        constants,
        autarky_surplus
    )

    # --------------------------------------------------------
    # NETWORK EQUILIBRIUM
    # --------------------------------------------------------

    network_solution = solve_network(
        markets,
        constants
    )

    # --------------------------------------------------------
    # Extract quantities and flows
    # --------------------------------------------------------

    extracted = extract_solution(
        markets,
        constants,
        network_solution
    )

    # --------------------------------------------------------
    # Recover adjusted prices
    # --------------------------------------------------------

    prices = recover_prices(
        markets,
        constants,
        extracted
    )

    # --------------------------------------------------------
    # Print equilibrium
    # --------------------------------------------------------

    print_network_solution(
        markets,
        extracted,
        prices
    )

    # --------------------------------------------------------
    # Check physical balances
    # --------------------------------------------------------

    check_balances(
        markets,
        extracted
    )

    # --------------------------------------------------------
    # Calculate actual network surplus
    # --------------------------------------------------------

    network_surplus = calculate_surplus(
        markets,
        extracted["markets"]
    )

    surplus_gain = (
        network_surplus
        -
        autarky_surplus
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        f"Base/autarky surplus:       "
        f"{autarky_surplus:.6f}"
    )

    print(
        f"Network surplus:            "
        f"{network_surplus:.6f}"
    )

    print(
        f"Surplus gain:               "
        f"{surplus_gain:.6f}"
    )

    print(
        f"Surplus gain (%):           "
        f"{100 * surplus_gain / autarky_surplus:.6f}%"
    )