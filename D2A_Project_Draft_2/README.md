# D2A Project Draft 2: physics-based losses and transmission investment

This README describes [`d2a_draft_2.ipynb`](./d2a_draft_2.ipynb), a notebook for studying welfare-maximizing electricity-market coupling with approximate physical transmission losses and candidate network investments.

The notebook uses one selected quarter-hour of submitted market bids. It compares autarky, the configured starting network, and (when enabled) a network built up through a greedy search over new links and conductor upgrades.

## Model

For each bidding area, the market-clearing model selects accepted supply and demand bid blocks. Interconnector flows are constrained by transfer capacities, and market balances account for power lost in transmission.

For an edge of length `L` and conductor radius `r`, the baseline resistance is estimated as:

```text
A = πr²
R = ρL/A
```

Under the notebook's balanced three-phase convention, sent power and resistive losses are:

```text
P_sent = √3 V_line I PF
P_loss = 3 I²R
P_received = P_sent - P_loss
```

The quadratic loss curve is approximated piecewise-linearly for optimization. These equations and the route-length approximation are modeling assumptions, not a substitute for a validated AC power-flow model.

The investment search considers:

- **New links**, priced using the configured distance-based benchmark of £1.6 million/km.
- **Conductor upgrades** on existing links, modeled as a one-step increase in conductor area and transfer capacity. The illustrative upgrade rate is 40% of the new-line benchmark, or £0.64 million/km, multiplied by the estimated link length.

The greedy search repeatedly selects the affordable action with the highest incremental welfare gain until its budget or stopping criteria are reached. It is a heuristic, not a guarantee of a globally optimal investment portfolio.

## Running the notebook

1. Start Jupyter Notebook or JupyterLab from the repository root.
2. Open `d2a_draft_2.ipynb`.
3. Run the cells from top to bottom.

The notebook reads the 13 JSON-formatted `.txt` market files from the repository's `data/` directory. It uses `gurobipy` to solve the optimization models, along with `numpy`, `pandas`, and `matplotlib`. A working Gurobi installation and license are required.

The full greedy search can require many optimization solves. Set `RUN_GREEDY_SEARCH = False` in its configuration cell to run the market-clearing and reporting portions without performing that search.

## Configuration

The main editable settings are near the top of the notebook:

- `PERIOD_INDEX` selects one of the 96 quarter-hour periods (`0` through `95`).
- `INTERCONNECTORS` defines the example links, endpoint areas, and baseline transfer capacities.
- Market coordinates and electrical assumptions configure approximate distances, resistance, voltage, current limits, power factor, and upgrade size.
- `NEW_LINE_COST_MILLION_GBP_PER_KM` and `WIRE_UPGRADE_COST_FRACTION_OF_NEW_LINE` define the illustrative investment-cost assumptions.
- `RUN_GREEDY_SEARCH` controls whether the full investment search is run.

The included network, coordinates, line parameters, and costs are illustrative. Replace them with sourced, date-consistent market and engineering data before treating numerical results as empirical estimates.

## Outputs

The notebook reports and visualizes:

- autarky and network-constrained welfare;
- transmission flows and modeled losses;
- the greedy investment history, budget, and spending when the search is enabled;
- welfare before and after investment; and
- nodal prices for autarky, the starting network, and the final network.

Prices are in EUR/MWh and quantities in MW, so market welfare is reported in EUR/hour. The notebook also reports the corresponding 15-minute welfare by multiplying hourly welfare by `0.25`. Investment budgets and costs are in million GBP. These currencies are not directly comparable: a benefit-cost analysis needs a stated GBP/EUR exchange rate and a consistent capital-cost/lifetime treatment.

## Important interpretation limits

- The coordinates estimate straight-line link lengths; they do not represent routed construction distances.
- Electrical parameters, transfer capacities, and investment costs are illustrative rather than verified project data.
- Piecewise-linear resistive losses approximate, rather than exactly reproduce, the quadratic loss equation.
- The transport-style network does not represent full AC power flows, voltage constraints, or loop flows.
- The greedy search considers one selected period and can miss better portfolios; a multi-period or exact investment formulation may select different actions.
- The model does not include unit commitment, reserves, reliability constraints, construction lead times, or changes in bidding behavior.

## Suggested next analysis

Run market clearing across all 96 quarter-hours and aggregate the 15-minute welfare outcomes. Then test whether promising links and conductor upgrades recur across periods, and evaluate them with sourced engineering costs, exchange rates, and asset-lifetime assumptions.
