# d2a_project


load_data.py returns a dictionary of dataframes for each file in the data folder

markets.py is a class with atrtibutes like supply, demand, price, etc. for each node

constants.py is system level with a connection matrix, a function that connects, etc.

main.py calls load_data to initialize the markets, creates a constants instance, and sets setting up connections to run the analysis.

At this point, nothing handles gurobi or the physics of transmission loss