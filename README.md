## 19669 Final Project -- Gabriel Sims and Daniel Branstetter

# Overview

How can energy market investments be optimally allocated when constrained by a budget?

We model European energy markets as a network of supply and demand nodes with transportation loss and restricted flow capacity. Supply and demand data comes from Nord Pool. We use an MILP to optimize the network under economic principles by maximizing surplus. We iteratively add the surplus maximizing investment in a greedy fashion, either connecting markets or upgrading existing connections, until a budget is reached. The sensitivity to initial network configuration is analyzed by rerunning the process with 10 network configuration variations. 

The analysis confirms that in line with economic principles prices begin to converge following investment, find a combination of building new edges and upgrading existing edges as optimal, and note sharply decreasing marginal surplus gains for each investment. 

This analysis provides insight for decision makers making global energy decision and provides a framework for collective action.

# Program Flow

All relevant files are in the D2A_Project_Draft_2 Folder

In D2A_Project_Draft_2:
The data folder contains a text file with JSON data for each energy market. 
d2a_draft_2.ipynb contains the code that loads the data, runs the MILP, greedy search, and provides insights.
simulation_WIP contains the code to run 10 different network configurations and provides insights(multiple_networks.ipynb) and print maps of different networks (map.py). 

the ignore folder contains old components of the project, supplimental analysis, and other files. The other drafts act similarly. We decided to leave them as reference.