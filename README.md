# d2a_project


Updated 10/1/26

## Overview:
This repository analyses a energy market network to find the social surplus maximizing investments while constrained by a budget. The analysis can be run by running gurobi_v3_outer.py.


## OOP Initializaiotn
Nodes represent countries and are stored as market objects which have supply and demand dataframes and step-functions, latitude and longitude coordinates of the capital city, and a function to plot supply and demand curves. Poland and Romania has some issues being loaded so are not in the model but can be added if desirable. JSON data from Nord Pool for each market is in the data folder.
The constants class handles the overall network with matrices for connections, costs to create each edge, and transmission loss. The cost to create matrix mutliplies the distance between lat/lon by 1.6(million/km), transmission loss are randomly generated numbers, and a connect function adds to the binary connection matrix. 

## MILP and Greedy Search 
The analysis has an inner and outer loop. The inner loop is a MILP with Gurobi that takes a network of connection finds Auturky surplus and the adjusted surplus from trade. The MILP uses blocks from the market dataframes as constraints that are sequentially filled, has a non-negativity constraint on flow, and balance constraints of imports and exports. The objective function maximizes surplus under these conditions which simulate market clearing behavior. This can be intuitively validated with print statements that provide the connections, prices, changes in consumption, imports, exports, etc. I also validated this by comparing the model to free trade. In free trade with no loss curves can be aggregated with world price and quantity calculated then applied to each node. Setting the transmission loss matrix to all 1s and solving the inner loop with a network that connects all markets yields the same world price and imports/exports for each node.

The outer node applies a greedy approach to search for optimal investment. It takes a multiplier of the largest edge to create as the budget, a maximum number of iterations, and list of connections. The model tests all candidate edge connections, uses the inner loop and MILP to find the surplus gain, then adds the edge with the greatest gain to the network and iterates until the final budget is reached or adding edges no longer increases surplus. For each iteration the cost, surplus, and gain of each edge checked is reported. It is important to acknowledge that although costs for each edges are incorporated in the greedy approach, they aren't minimized in any way; only gain to social surplus is maximized until the budget is reached. We can change that if desirable.

gurobi_v3_inner.py is the inner loop and gurobi_v3_outer.py is the outer loop. The ignore folder has a bunch of temporary things I tried when creating this.


## Adding More Realistic Constraints
Some of the physics elements we discussed can be applied at different stages of this process. Transmission loss can be changed in the constants class and any other matrix can be added as desired. Constraints like heating or capacity can be applied as Gurobi constraints or directly to the dataframes that inform supply and demand curves. We can also change the search strategy as desired.


## AI Usage
I tried this by pairwise clearing balance constraints and iterating until it stopped. Unfortunately I'm not smart enough to to this stably in Gurobi, so a lot of this was created iteratively in conjunction with AI. But I've validated the code to the best of my ability and I'm pretty sure that's fine with the project/course. The Gurobi formulation has more constraints than my original formulation given the block-based approach, so I tried to have it show the mathematical formulation of the whole process. That file is in the ignore folder called analysis_explanation_chat.tex and is a lot clearer in LaTeX for reference. Lmk if you have any questions.

- Gabe