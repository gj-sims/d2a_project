# ============================================================
# D2A PROJECT
# Systemwide Network Equilibrium using Gurobi
#
# Poland (pl) and Romania (ro) are always skipped.
#
# The existing Market and Constants classes are not modified.
# ============================================================

from load_data import load_dfs
from markets import Market
from constants import Constants

import numpy as np
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt


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
    "ro"
]


# ============================================================
# CREATE PROBLEM
# ============================================================

np.random.seed(42)

problem = Constants()
problem.nodes = []


# ============================================================
# CREATE MARKETS
# ============================================================

def create_nodes():

    dfs = load_dfs()

    for name in dfs:

        if name in SKIP_MARKETS:
            continue

        market = Market(
            name,
            dfs[name]
        )

        problem.nodes.append(market)

        # Autarky equilibrium
        market.find_price()


# ============================================================
# COORDINATES
# ============================================================

def add_coordinates():

    for market in problem.nodes:

        if market.name == "at":
            market.lat = 48.2085
            market.lon = 16.3721

        elif market.name == "be":
            market.lat = 50.8505
            market.lon = 4.3488

        elif market.name == "ger":
            market.lat = 52.5200
            market.lon = 13.4050

        elif market.name == "fr":
            market.lat = 48.8566
            market.lon = 2.3522

        elif market.name == "nl":
            market.lat = 52.37
            market.lon = 4.89

        elif market.name == "dk":
            market.lat = 55.6761
            market.lon = 12.5683

        elif market.name == "fi":
            market.lat = 60.17
            market.lon = 24.94

        elif market.name == "no":
            market.lat = 59.91
            market.lon = 10.75

        elif market.name == "se":
            market.lat = 59.33
            market.lon = 18.06

        elif market.name == "bg":
            market.lat = 42.73
            market.lon = 25.49

        elif market.name == "lv":
            market.lat = 59.437
            market.lon = 24.754


# ============================================================
# CREATE CONNECTION COSTS
# ============================================================

def create_connection_costs():

    for i in problem.nodes:

        for j in problem.nodes:

            if i.name in SKIP_MARKETS:
                continue

            if j.name in SKIP_MARKETS:
                continue

            if i.name == j.name:
                continue

            problem.cost_to_create(i, j)


# ============================================================
# ADD CURRENT NETWORK
# ============================================================

def create_network():
    problem.connect(problem.nodes[0], problem.nodes[1])

    # problem.connect(problem.nodes[7], problem.nodes[9])
    # problem.connect(problem.nodes[7], problem.nodes[3])
    # problem.connect(problem.nodes[3], problem.nodes[8])
    # problem.connect(problem.nodes[8], problem.nodes[6])
    # problem.connect(problem.nodes[6], problem.nodes[0])
    # problem.connect(problem.nodes[2], problem.nodes[0])
    # problem.connect(problem.nodes[0], problem.nodes[5])
    # problem.connect(problem.nodes[6], problem.nodes[4])
    # problem.connect(problem.nodes[4], problem.nodes[10])
    # problem.connect(problem.nodes[4], problem.nodes[1])
    # problem.connect(problem.nodes[10], problem.nodes[1])


# ============================================================
# GET CONNECTIONS
# ============================================================

def get_edges(problem):

    edges = []

    for i in problem.nodes:

        if i.name in SKIP_MARKETS:
            continue

        i_index = problem.index_dict[i.name]

        for j in problem.nodes:

            if j.name in SKIP_MARKETS:
                continue

            if i.name == j.name:
                continue

            j_index = problem.index_dict[j.name]

            if i_index >= j_index:
                continue

            if problem.connection_matrix[i_index][j_index] == 1:

                edges.append(
                    (i.name, j.name)
                )
        #print("------DEBUGGING--------",'EDGES',edges)

    return edges


# ============================================================
# GET STEP BLOCKS
# ============================================================

def get_supply_blocks(market):

    curve = (
        market.supply[
            ["quantity", "price"]
        ]
        .sort_values(
            ["quantity", "price"]
        )
        .drop_duplicates(
            subset=["quantity"],
            keep="last"
        )
        .reset_index(drop=True)
    )

    blocks = []

    for i in range(len(curve) - 1):

        left = float(
            curve.loc[i, "quantity"]
        )

        right = float(
            curve.loc[i + 1, "quantity"]
        )

        price = float(
            curve.loc[i, "price"]
        )

        quantity = right - left

        if quantity > 0:

            blocks.append(
                {
                    "quantity": quantity,
                    "price": price
                }
            )

    return blocks


def get_demand_blocks(market):

    curve = (
        market.demand[
            ["quantity", "price"]
        ]
        .sort_values(
            ["quantity", "price"]
        )
        .drop_duplicates(
            subset=["quantity"],
            keep="last"
        )
        .reset_index(drop=True)
    )

    blocks = []

    for i in range(len(curve) - 1):

        left = float(
            curve.loc[i, "quantity"]
        )

        right = float(
            curve.loc[i + 1, "quantity"]
        )

        price = float(
            curve.loc[i, "price"]
        )

        quantity = right - left

        if quantity > 0:

            blocks.append(
                {
                    "quantity": quantity,
                    "price": price
                }
            )

    return blocks


# ============================================================
# CALCULATE WELFARE FROM BLOCKS
# ============================================================

def calculate_block_welfare(market):

    supply_blocks = get_supply_blocks(market)
    demand_blocks = get_demand_blocks(market)

    quantity = market.quantity

    demand_value = 0.0
    supply_cost = 0.0

    remaining = quantity

    for block in demand_blocks:

        if remaining <= 0:
            break

        accepted = min(
            remaining,
            block["quantity"]
        )

        demand_value += (
            block["price"]
            *
            accepted
        )

        remaining -= accepted

    remaining = quantity

    for block in supply_blocks:

        if remaining <= 0:
            break

        accepted = min(
            remaining,
            block["quantity"]
        )

        supply_cost += (
            block["price"]
            *
            accepted
        )

        remaining -= accepted
        #print("------DEBUGGING------",market.name,demand_value-supply_cost)

    return demand_value - supply_cost


# ============================================================
# CALCULATE TOTAL AUTARKY SURPLUS
# ============================================================

def calculate_autarky_surplus():

    surplus = 0.0

    for market in problem.nodes:

        if market.name in SKIP_MARKETS:
            continue
        surplus += calculate_block_welfare(market)
    

    return surplus

# ============================================================
# CALCULATE MARKET PRICE FROM BLOCK
# ============================================================

def get_market_price(market, supply_blocks, demand_blocks, supply_vars, demand_vars):
    name = market.name

    marginal_supply = None
    marginal_demand = None

    # Find partially used supply block
    for b, block in enumerate(supply_blocks[name]):
        used = supply_vars[name][b].X
        capacity = block["quantity"]

        if used > 1e-6 and used < capacity - 1e-6:
            marginal_supply = block["price"]
            break

    # Find partially used demand block
    for b, block in enumerate(demand_blocks[name]):
        used = demand_vars[name][b].X
        capacity = block["quantity"]

        if used > 1e-6 and used < capacity - 1e-6:
            marginal_demand = block["price"]
            break

    # If both sides have a marginal block, use their midpoint
    if marginal_supply is not None and marginal_demand is not None:
        return (marginal_supply + marginal_demand) / 2

    # Otherwise use whichever marginal block exists
    if marginal_supply is not None:
        return marginal_supply

    if marginal_demand is not None:
        return marginal_demand

    return None


# ============================================================
# PLOT AND VALIDATE BLOCK-BASED AUTARKY SURPLUS
# ============================================================

def plot_block_surplus(market):

    Q = market.quantity
    P = market.price

    supply_blocks = get_supply_blocks(market)
    demand_blocks = get_demand_blocks(market)

    plt.figure(figsize=(12, 7))

    plt.step(
        market.demand_function.x,
        market.demand_function.y,
        where="post",
        label="Demand"
    )

    plt.step(
        market.supply_function.x,
        market.supply_function.y,
        where="post",
        label="Supply"
    )

    demand_value = 0
    demand_quantity = 0
    consumer_surplus = 0

    print()
    print("DEMAND BLOCKS")

    for block in demand_blocks:

        block_price = block["price"]
        block_quantity = block["quantity"]

        remaining = Q - demand_quantity

        if remaining <= 0:
            break

        accepted = min(
            block_quantity,
            remaining
        )

        if accepted <= 0:
            continue

        left = demand_quantity
        right = demand_quantity + accepted

        demand_value += (
            accepted
            *
            block_price
        )

        block_cs = (
            accepted
            *
            (block_price - P)
        )

        if block_price > P:

            consumer_surplus += block_cs

            plt.fill_between(
                [left, right],
                P,
                block_price,
                step="post",
                alpha=0.3
            )

        plt.plot(
            [left, right],
            [block_price, block_price],
            linestyle=":",
            alpha=0.5
        )

        demand_quantity += accepted

        print(
            f"Price={block_price:.4f} | "
            f"Quantity={accepted:.4f} | "
            f"CS={max(block_cs, 0):.4f}"
        )

    supply_cost = 0
    supply_quantity = 0
    producer_surplus = 0

    print()
    print("SUPPLY BLOCKS")

    for block in supply_blocks:

        block_price = block["price"]
        block_quantity = block["quantity"]

        remaining = Q - supply_quantity

        if remaining <= 0:
            break

        accepted = min(
            block_quantity,
            remaining
        )

        if accepted <= 0:
            continue

        left = supply_quantity
        right = supply_quantity + accepted

        supply_cost += (
            accepted
            *
            block_price
        )

        block_ps = (
            accepted
            *
            (P - block_price)
        )

        if block_price < P:

            producer_surplus += block_ps

            plt.fill_between(
                [left, right],
                block_price,
                P,
                step="post",
                alpha=0.3
            )

        plt.plot(
            [left, right],
            [block_price, block_price],
            linestyle=":",
            alpha=0.5
        )

        supply_quantity += accepted

        print(
            f"Price={block_price:.4f} | "
            f"Quantity={accepted:.4f} | "
            f"PS={max(block_ps, 0):.4f}"
        )

    block_total_surplus = (
        consumer_surplus
        +
        producer_surplus
    )

    block_welfare = (
        demand_value
        -
        supply_cost
    )

    quad_cs = market.find_consumer_surplus()
    quad_ps = market.find_producer_surplus()
    quad_total = quad_cs + quad_ps

    plt.axhline(
        P,
        linestyle="--",
        label=f"Equilibrium price = {P:.2f}"
    )

    plt.axvline(
        Q,
        linestyle="--",
        label=f"Equilibrium quantity = {Q:.2f}"
    )

    plt.scatter(
        [Q],
        [P],
        zorder=5
    )

    print()
    print("=" * 70)
    print(
        f"{market.name} AUTARKY SURPLUS VALIDATION"
    )
    print("=" * 70)

    print()
    print("BLOCK METHOD")
    print("-" * 70)

    print(
        f"Consumer surplus:       "
        f"{consumer_surplus:.6f}"
    )

    print(
        f"Producer surplus:       "
        f"{producer_surplus:.6f}"
    )

    print(
        f"Total surplus:          "
        f"{block_total_surplus:.6f}"
    )

    print()
    print("BLOCK WELFARE CHECK")
    print("-" * 70)

    print(
        f"Demand value:           "
        f"{demand_value:.6f}"
    )

    print(
        f"Supply cost:            "
        f"{supply_cost:.6f}"
    )

    print(
        f"Demand value - cost:    "
        f"{block_welfare:.6f}"
    )

    print()
    print("ORIGINAL QUAD METHOD")
    print("-" * 70)

    print(
        f"Consumer surplus:       "
        f"{quad_cs:.6f}"
    )

    print(
        f"Producer surplus:       "
        f"{quad_ps:.6f}"
    )

    print(
        f"Total surplus:          "
        f"{quad_total:.6f}"
    )

    print()
    print("COMPARISON")
    print("-" * 70)

    print(
        f"Block total:            "
        f"{block_total_surplus:.6f}"
    )

    print(
        f"Quad total:             "
        f"{quad_total:.6f}"
    )

    print(
        f"Block - Quad:           "
        f"{block_total_surplus - quad_total:.6f}"
    )

    print("=" * 70)

    demand_max = max(
        market.demand_function.y
    )

    supply_min = min(
        market.supply_function.y
    )

    plt.text(
        Q * 0.35,
        P + (demand_max - P) * 0.15,
        f"CS = {consumer_surplus:.2f}",
        fontsize=11
    )

    plt.text(
        Q * 0.35,
        P - (P - supply_min) * 0.15,
        f"PS = {producer_surplus:.2f}",
        fontsize=11
    )

    plt.xlabel("Quantity")
    plt.ylabel("Price")

    plt.title(
        f"{market.name} — "
        f"Block-Based Autarky Surplus"
    )

    plt.legend()
    plt.grid(True)

    plt.show()


# ============================================================
# TRANSMISSION LOSS
# ============================================================

def get_loss(problem, i_name, j_name):

    i = problem.index_dict[i_name]
    j = problem.index_dict[j_name]

    loss = (
        problem.transmission_loss_matrix[i][j]
        +
        problem.transmission_loss_matrix[j][i]
    ) / 2.0
    #print("-----debugging------",i_name, j_name, loss)
    return float(loss)


# ============================================================
# SOLVE NETWORK EQUILIBRIUM
# ============================================================

def solve_network_equilibrium(
    markets,
    constants,
    verbose=True
):

    # --------------------------------------------------------
    # Always remove Poland and Romania
    # --------------------------------------------------------

    markets = [
        market
        for market in markets
        if market.name not in SKIP_MARKETS
    ]

    print("\n" + "=" * 80)
    print("SOLVING NETWORK EQUILIBRIUM")
    print("=" * 80)

    # ========================================================
    # 1. BUILD SUPPLY / DEMAND BLOCKS
    # ========================================================

    supply_blocks = {}
    demand_blocks = {}

    for market in markets:
        supply_blocks[market.name] = (
            get_supply_blocks(market)
        )

        demand_blocks[market.name] = (
            get_demand_blocks(market)
        )

        print(
            f"{market.name}: "
            f"{len(supply_blocks[market.name])} "
            f"supply blocks, "
            f"{len(demand_blocks[market.name])} "
            f"demand blocks"
        )

    

    # ========================================================
    # 2. GET EXISTING EDGES
    # ========================================================

    edges = []

    for i in range(len(markets)):

        for j in range(i + 1, len(markets)):

            i_index = constants.index_dict[
                markets[i].name
            ]

            j_index = constants.index_dict[
                markets[j].name
            ]

            if constants.connection_matrix[
                i_index
            ][
                j_index
            ] == 1:

                name_i = markets[i].name
                name_j = markets[j].name

                loss = (
                    constants.transmission_loss_matrix[
                        i_index
                    ][
                        j_index
                    ]
                    +
                    constants.transmission_loss_matrix[
                        j_index
                    ][
                        i_index
                    ]
                ) / 2.0

                edges.append({
                    "i": i,
                    "j": j,
                    "name_i": name_i,
                    "name_j": name_j,
                    "loss": loss
                })

    print("\nNETWORK EDGES USED BY SOLVER")

    for edge in edges:

        print(
            f"{edge['name_i']} <-> "
            f"{edge['name_j']} "
            f"| loss = {edge['loss']}"
        )

    # ========================================================
    # 3. BUILD MILP
    # ========================================================

    model = gp.Model(
        "network_equilibrium"
    )

    if not verbose:
        model.Params.OutputFlag = 0

    supply_vars = {}
    demand_vars = {}

    for market in markets:

        name = market.name

        supply_vars[name] = []
        demand_vars[name] = []

        for b, block in enumerate(
            supply_blocks[name]
        ):

            x = model.addVar(
                lb=0,
                ub=block["quantity"],
                name=f"supply_{name}_{b}"
            )

            supply_vars[name].append(x)

        for b, block in enumerate(
            demand_blocks[name]
        ):

            x = model.addVar(
                lb=0,
                ub=block["quantity"],
                name=f"demand_{name}_{b}"
            )

            demand_vars[name].append(x)

    # ========================================================
    # 4. FLOW VARIABLES
    # ========================================================

    flow_ij = {}
    flow_ji = {}
    direction = {}

    for e, edge in enumerate(edges):

        i = edge["i"]
        j = edge["j"]

        name_i = edge["name_i"]
        name_j = edge["name_j"]

        flow_ij[e] = model.addVar(
            lb=0,
            ub=20000,
            name=f"flow_{name_i}_{name_j}"
        )

        flow_ji[e] = model.addVar(
            lb=0,
            ub=20000,
            name=f"flow_{name_j}_{name_i}"
        )

        direction[e] = model.addVar(
            vtype=GRB.BINARY,
            name=f"direction_{name_i}_{name_j}"
        )

        model.addConstr(
            flow_ij[e]
            <=
            20000 * direction[e],
            name=f"direction_forward_{e}"
        )

        model.addConstr(
            flow_ji[e]
            <=
            20000 * (1 - direction[e]),
            name=f"direction_backward_{e}"
        )

    # ========================================================
    # 5. NODE BALANCES
    # ========================================================

    balance_constraints = {}

    for market_index, market in enumerate(markets):

        name = market.name

        local_supply = gp.quicksum(
            supply_vars[name]
        )

        local_demand = gp.quicksum(
            demand_vars[name]
        )

        imports = gp.LinExpr()
        exports = gp.LinExpr()

        for e, edge in enumerate(edges):

            if edge["i"] == market_index:

                exports += flow_ij[e]

                imports += (
                    edge["loss"]
                    *
                    flow_ji[e]
                )

            elif edge["j"] == market_index:

                exports += flow_ji[e]

                imports += (
                    edge["loss"]
                    *
                    flow_ij[e]
                )

        balance_constraints[name] = model.addConstr(
            local_supply + imports
            ==
            local_demand + exports,
            name=f"balance_{name}"
        )


    # ========================================================
    # 6. OBJECTIVE
    # ========================================================

    objective = gp.LinExpr()

    for market in markets:

        name = market.name

        # Demand value
        for b, block in enumerate(
            demand_blocks[name]
        ):

            objective += (
                block["price"]
                *
                demand_vars[name][b]
            )

        # Supply cost
        for b, block in enumerate(
            supply_blocks[name]
        ):

            objective -= (
                block["price"]
                *
                supply_vars[name][b]
            )

    model.setObjective(
        objective,
        GRB.MAXIMIZE
    )

    # ========================================================
    # 7. SOLVE MILP
    # ========================================================

    print("\n" + "-" * 80)
    print("SOLVING WELFARE MAXIMIZATION MILP")
    print("-" * 80)

    model.optimize()

    if model.Status != GRB.OPTIMAL:

        print(
            "MODEL STATUS:",
            model.Status
        )

        return None

    

    print("\nMILP SOLVED")

    print(
        f"Objective / Total Surplus = "
        f"{model.ObjVal:,.4f}"
    )
    print("\n" + "=" * 80)
    # print("MARGINAL BLOCKS")
    # print("=" * 80)

    # for market in markets:

    #     name = market.name

    #     print(f"\n{name}")

    #     print("SUPPLY")
    #     for b, block in enumerate(supply_blocks[name]):

    #         variable = supply_vars[name][b]

    #         if variable.X > 1e-6:
    #             print(
    #                 f"  block {b}: "
    #                 f"price={block['price']:.6f}, "
    #                 f"used={variable.X:.6f}, "
    #                 f"capacity={block['quantity']:.6f}"
    #             )

    #     print("DEMAND")
    #     for b, block in enumerate(demand_blocks[name]):

    #         variable = demand_vars[name][b]

    #         if variable.X > 1e-6:
    #             print(
    #                 f"  block {b}: "
    #                 f"price={block['price']:.6f}, "
    #                 f"used={variable.X:.6f}, "
    #                 f"capacity={block['quantity']:.6f}"
    #             )

    # ========================================================
    # 8. PRINT LOCAL PRODUCTION / CONSUMPTION
    # ========================================================

    print("\n" + "-" * 80)
    print("LOCAL PRODUCTION / CONSUMPTION")
    print("-" * 80)

    for market in markets:

        name = market.name

        production = sum(
            x.X
            for x in supply_vars[name]
        )

        consumption = sum(
            x.X
            for x in demand_vars[name]
        )

        print(
            f"{name:>4} | "
            f"production = {production:12,.4f} | "
            f"demand = {consumption:12,.4f} | "
            f"net = "
            f"{production - consumption:12,.4f}"
        )

    # ========================================================
    # 9. PRINT FLOWS FROM MILP
    # ========================================================

    print("\n" + "-" * 80)
    print("NETWORK FLOWS")
    print("-" * 80)

    for e, edge in enumerate(edges):

        forward = flow_ij[e].X
        backward = flow_ji[e].X

        if forward > 1e-6:

            received = (
                forward
                *
                edge["loss"]
            )

            print(
                f"{edge['name_i']} -> "
                f"{edge['name_j']} | "
                f"sent = {forward:12,.4f} | "
                f"received = {received:12,.4f} | "
                f"loss = "
                f"{1 - edge['loss']:.4f}"
            )

        elif backward > 1e-6:

            received = (
                backward
                *
                edge["loss"]
            )

            print(
                f"{edge['name_j']} -> "
                f"{edge['name_i']} | "
                f"sent = {backward:12,.4f} | "
                f"received = {received:12,.4f} | "
                f"loss = "
                f"{1 - edge['loss']:.4f}"
            )

        else:

            print(
                f"{edge['name_i']} <-> "
                f"{edge['name_j']} | "
                f"NO FLOW"
            )

    # ========================================================
    # 10. FIX THE MILP SOLUTION
    #
    # This is the important change.
    #
    # model.fixed() creates a continuous model with all
    # integer variables fixed to the values found by the MILP.
    #
    # The resulting model can therefore be solved as an LP,
    # giving us valid dual values for the balance constraints.
    # ========================================================

    print("\n" + "-" * 80)
    print(
        "FIXING MILP DIRECTIONS "
        "AND RE-SOLVING AS LP"
    )
    print("-" * 80)

    fixed_model = model.fixed()

    if fixed_model is None:

        print(
            "Could not create fixed LP."
        )

        return None

    fixed_model.Params.OutputFlag = (
        1 if verbose else 0
    )

    fixed_model.Params.Presolve = 0
    fixed_model.Params.Method = 1

    fixed_model.optimize()

    if fixed_model.Status != GRB.OPTIMAL:

        print(
            "LP STATUS:",
            fixed_model.Status
        )

        return None

        # ============================================================
    # CONNECTED EQUILIBRIUM CHECK
    # ============================================================

    print("\nCONNECTED EQUILIBRIUM CHECK")
    print("=" * 70)

    for name in ["dk", "lv"]:

        print(f"\n{name.upper()}")

        print("SUPPLY MARGINAL BLOCKS:")

        for b, block in enumerate(supply_blocks[name]):

            used = supply_vars[name][b].X
            capacity = block["quantity"]

            if used > 1e-6 and used < capacity - 1e-6:
                print(
                    f"  block {b}: "
                    f"price={block['price']:.6f}, "
                    f"used={used:.6f}, "
                    f"capacity={capacity:.6f}"
                )

        print("DEMAND MARGINAL BLOCKS:")

        for b, block in enumerate(demand_blocks[name]):

            used = demand_vars[name][b].X
            capacity = block["quantity"]

            if used > 1e-6 and used < capacity - 1e-6:
                print(
                    f"  block {b}: "
                    f"price={block['price']:.6f}, "
                    f"used={used:.6f}, "
                    f"capacity={capacity:.6f}"
                )

    print("=" * 70)

    print("\nLP SOLVED")

    print(
        f"LP Objective = "
        f"{fixed_model.ObjVal:,.4f}"
    )

    # ============================================================
# 11. CALCULATE CONNECTED MARKET PRICES
# ============================================================

# Start with autarky prices for every market.
# Markets that do not participate in network trade will keep
# their original price.

    for market in markets:
        market.adj_price = market.price


    # ------------------------------------------------------------
    # Find markets that actually have network flow
    # ------------------------------------------------------------

    for e, edge in enumerate(edges):

        i = edge["i"]
        j = edge["j"]

        name_i = edge["name_i"]
        name_j = edge["name_j"]

        forward_flow = flow_ij[e].X
        backward_flow = flow_ji[e].X

        loss = edge["loss"]


        # --------------------------------------------------------
        # i -> j
        # --------------------------------------------------------

        if forward_flow > 1e-6:

            print(
                f"CONNECTED EDGE: {name_i} -> {name_j} "
                f"flow = {forward_flow:.6f}"
            )

            # Find the marginal supply block at the exporting node
            marginal_supply = None

            for b, block in enumerate(supply_blocks[name_i]):

                used = supply_vars[name_i][b].X
                capacity = block["quantity"]

                if used > 1e-6 and used < capacity - 1e-6:
                    marginal_supply = block["price"]
                    break

            # Find the marginal demand block at the importing node
            marginal_demand = None

            for b, block in enumerate(demand_blocks[name_j]):

                used = demand_vars[name_j][b].X
                capacity = block["quantity"]

                if used > 1e-6 and used < capacity - 1e-6:
                    marginal_demand = block["price"]
                    break


            # ----------------------------------------------------
            # If we have a marginal block on both sides,
            # use their midpoint as the connected equilibrium
            # price at the importing node.
            # ----------------------------------------------------

            if marginal_supply is not None and marginal_demand is not None:

                price_j = (
                    marginal_supply / loss
                    + marginal_demand
                ) / 2

                price_i = loss * price_j

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


            elif marginal_supply is not None:

                price_i = marginal_supply
                price_j = price_i / loss

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


            elif marginal_demand is not None:

                price_j = marginal_demand
                price_i = loss * price_j

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


        # --------------------------------------------------------
        # j -> i
        # --------------------------------------------------------

        elif backward_flow > 1e-6:

            print(
                f"CONNECTED EDGE: {name_j} -> {name_i} "
                f"flow = {backward_flow:.6f}"
            )

            # Find marginal supply block at exporting node j
            marginal_supply = None

            for b, block in enumerate(supply_blocks[name_j]):

                used = supply_vars[name_j][b].X
                capacity = block["quantity"]

                if used > 1e-6 and used < capacity - 1e-6:
                    marginal_supply = block["price"]
                    break

            # Find marginal demand block at importing node i
            marginal_demand = None

            for b, block in enumerate(demand_blocks[name_i]):

                used = demand_vars[name_i][b].X
                capacity = block["quantity"]

                if used > 1e-6 and used < capacity - 1e-6:
                    marginal_demand = block["price"]
                    break


            if marginal_supply is not None and marginal_demand is not None:

                price_i = (
                    marginal_supply / loss
                    + marginal_demand
                ) / 2

                price_j = loss * price_i

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


            elif marginal_supply is not None:

                price_j = marginal_supply
                price_i = price_j / loss

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


            elif marginal_demand is not None:

                price_i = marginal_demand
                price_j = price_i / loss

                markets[i].adj_price = price_i
                markets[j].adj_price = price_j


    # ============================================================
    # PRICE / FLOW DIAGNOSTIC
    # ============================================================

    print("\nPRICE / FLOW DIAGNOSTIC")
    print("-" * 80)

    for market in markets:

        name = market.name

        production = sum(
            supply_vars[name][b].X
            for b in range(len(supply_vars[name]))
        )

        consumption = sum(
            demand_vars[name][b].X
            for b in range(len(demand_vars[name]))
        )

        imports = 0
        exports = 0

        for e, edge in enumerate(edges):

            if edge["name_i"] == name:
                exports += flow_ij[e].X
                imports += edge["loss"] * flow_ji[e].X

            elif edge["name_j"] == name:
                exports += flow_ji[e].X
                imports += edge["loss"] * flow_ij[e].X

        print(
            f"{name:>3} | "
            f"autarky P = {market.price:10.4f} | "
            f"connected P = {market.adj_price:10.4f} | "
            f"prod = {production:10.4f} | "
            f"cons = {consumption:10.4f} | "
            f"imports = {imports:10.4f} | "
            f"exports = {exports:10.4f}"
        )
    # ========================================================
    # 12. FINAL NODE BALANCE CHECK
    # ========================================================

    print("\n" + "-" * 80)
    print("NODE BALANCE CHECK")
    print("-" * 80)

    for market_index, market in enumerate(markets):

        name = market.name

        production = 0.0
        consumption = 0.0

        for b in range(
            len(supply_blocks[name])
        ):

            variable = fixed_model.getVarByName(
                f"supply_{name}_{b}"
            )

            production += variable.X

        for b in range(
            len(demand_blocks[name])
        ):

            variable = fixed_model.getVarByName(
                f"demand_{name}_{b}"
            )

            consumption += variable.X

        imports = 0.0
        exports = 0.0

        for e, edge in enumerate(edges):

            forward_variable = fixed_model.getVarByName(
                f"flow_{edge['name_i']}_{edge['name_j']}"
            )

            backward_variable = fixed_model.getVarByName(
                f"flow_{edge['name_j']}_{edge['name_i']}"
            )

            forward = forward_variable.X
            backward = backward_variable.X

            if edge["i"] == market_index:

                exports += forward

                imports += (
                    edge["loss"]
                    *
                    backward
                )

            elif edge["j"] == market_index:

                exports += backward

                imports += (
                    edge["loss"]
                    *
                    forward
                )

        lhs = production + imports
        rhs = consumption + exports

        print(
            f"{name:>4} | "
            f"supply + imports = "
            f"{lhs:12,.4f} | "
            f"demand + exports = "
            f"{rhs:12,.4f} | "
            f"difference = "
            f"{lhs - rhs:12,.8f}"
        )

    # ========================================================
    # 13. FINAL NETWORK SURPLUS
    # ========================================================

    post_surplus = fixed_model.ObjVal

    pre_surplus = calculate_autarky_surplus()

    print("\n" + "=" * 80)
    print("FINAL SURPLUS COMPARISON")
    print("=" * 80)

    print(
        f"Autarky surplus = "
        f"{pre_surplus:,.6f}"
    )

    print(
        f"Network surplus = "
        f"{post_surplus:,.6f}"
    )

    print(
        f"Surplus change  = "
        f"{post_surplus - pre_surplus:,.6f}"
    )

    print("=" * 80)

    # Return the LP because its objective and duals correspond
    # to the equilibrium prices we just calculated.
    return fixed_model


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Create markets
    # --------------------------------------------------------

    if len(problem.nodes) == 0:
        create_nodes()

    # --------------------------------------------------------
    # Print indexes
    # --------------------------------------------------------

    print()

    for i in range(
        len(problem.nodes)
    ):

        print(
            i,
            problem.nodes[i].name
        )

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    add_coordinates()

    # --------------------------------------------------------
    # Connection costs
    # --------------------------------------------------------

    create_connection_costs()

    # --------------------------------------------------------
    # Existing network
    # --------------------------------------------------------

    create_network()

    # --------------------------------------------------------
    # Autarky surplus
    # --------------------------------------------------------

    pre_surplus = calculate_autarky_surplus()

    print()

    print(
        "AUTARKY SURPLUS:",
        pre_surplus
    )

    # --------------------------------------------------------
    # Show existing connections
    # --------------------------------------------------------

    print()
    print("EXISTING CONNECTIONS")

    edges = get_edges(problem)

    for i_name, j_name in edges:

        loss = get_loss(
            problem,
            i_name,
            j_name
        )

        print(
            i_name,
            "<->",
            j_name,
            "| loss =",
            loss
        )

    # --------------------------------------------------------
    # SOLVE SYSTEMWIDE EQUILIBRIUM
    # --------------------------------------------------------

    model = solve_network_equilibrium(
        problem.nodes,
        problem
    )

    if model is None:

        print()
        print("NETWORK EQUILIBRIUM COULD NOT BE SOLVED.")

        raise SystemExit

    # --------------------------------------------------------
    # Compare prices
    # --------------------------------------------------------

    print()
    print("-" * 80)
    print("EQUILIBRIUM PRICE CHANGES")
    print("-" * 80)

    print(
        f"{'Market':>6} | "
        f"{'Autarky':>12} | "
        f"{'Connected':>12} | "
        f"{'Change':>12} | "
        f"{'% Change':>10}"
    )

    print("-" * 80)

    for market in problem.nodes:

        if market.name in SKIP_MARKETS:
            continue

        autarky_price = market.price
        connected_price = market.adj_price

        price_change = (
            connected_price
            -
            autarky_price
        )

        if autarky_price != 0:

            percent_change = (
                price_change
                /
                autarky_price
            ) * 100

        else:

            percent_change = 0

        print(
            f"{market.name:>6} | "
            f"{autarky_price:12.4f} | "
            f"{connected_price:12.4f} | "
            f"{price_change:12.4f} | "
            f"{percent_change:9.2f}%"
        )

    print()
    print("DONE")

 