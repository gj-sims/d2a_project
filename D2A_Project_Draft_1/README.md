# D2A Project Draft 1: network-constrained market clearing

This folder contains a runnable baseline model for the simplified research question:

> Holding one day's submitted supply and demand schedules fixed, how much social surplus can inter-area electricity trade create, and which fixed transmission constraints prevent further gains?

The main file is `D2A_Electricity_Market_Coupling.ipynb`. It reads the 13 JSON-formatted `.txt` files in `data/`, converts each cumulative bid schedule into bounded incremental bid blocks, and uses Gurobi to solve a joint social-welfare-maximizing linear program.

## Model

For market `i`, supply block `k`, demand block `m`, and interconnector `ij`, the model chooses:

- accepted supply `s[i,k]` in MW;
- accepted demand `d[i,m]` in MW; and
- signed transfer `f[i,j]` in MW.

It maximizes gross willingness to pay minus supply offer cost:

```text
maximize  sum(value[i,m] * d[i,m]) - sum(cost[i,k] * s[i,k])
```

subject to market balance, bid-block limits, and fixed transfer-capacity limits:

```text
supply + imports = demand + exports
0 <= accepted block <= submitted block size
-capacity[i,j] <= flow[i,j] <= capacity[i,j]
```

This is a linear program. It uses the bids as submitted and does not extrapolate beyond any curve's observed quantity range.

## Running the notebook

1. Open a terminal in this folder, or navigate here in Jupyter.
2. Start Jupyter with `jupyter notebook` or `jupyter lab`.
3. Open `D2A_Electricity_Market_Coupling.ipynb`.
4. Run all cells from top to bottom.

The installed Gurobi license is sufficient for the current model. The notebook imports `gurobipy`, `pandas`, `numpy`, and `matplotlib`.

## Configuration

Two cells near the top are intended to be edited:

- `PERIOD_INDEX` selects one of the 96 quarter-hour delivery intervals (`0` through `95`).
- `INTERCONNECTORS` defines the network endpoints and capacity in MW.

The included interconnector table is an illustrative baseline made of round values so that the model runs end-to-end. It is **not** a verified historical capacity dataset. The demonstration applies `ILLUSTRATIVE_CAPACITY_SCALE = 0.5` to the listed base values so that transfer scarcity is visible; set the scale to `1.0` to use the listed values without that reduction. Replace the example with a sourced, date-consistent table before interpreting the numerical results as empirical estimates.

## Outputs

The notebook reports:

- autarky welfare and capacity-constrained network welfare;
- the welfare gain from trade;
- accepted supply and demand by market;
- net exports by market;
- nodal-price dual diagnostics;
- signed interconnector flows and utilization;
- links at a flow limit, the subset that are economically binding, and the marginal value of relaxing their capacities; and
- a comparison with the mean published area price found in each source file.

Prices are in EUR/MWh and quantities are in MW, so the objective is in EUR/hour. The notebook multiplies by `0.25` when reporting welfare for a 15-minute interval.

## Important interpretation limits

This draft is a capacitated transport model, not a full physical electricity-grid model. It does not yet include:

- AC or DC power-flow laws and loop flows;
- electrical losses;
- unit commitment or ramping;
- reserves and reliability constraints;
- nonconvex or linked bids;
- endogenous transmission investment; or
- strategic changes in bidding caused by a grid expansion.

Those are deliberate exclusions. The baseline first identifies the value of trade and the transmission links whose fixed capacities are scarce. A later model can add investment decisions or grid physics after this core market-clearing implementation has been validated.

## Recommended next analysis

Run all 96 periods, multiply every period's EUR/hour outcome by 0.25 hours, and aggregate the resulting daily welfare gains. Recurring binding links are stronger expansion candidates than a link that binds in only one snapshot.
