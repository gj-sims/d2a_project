# Main for D2A Project
from load_data import load_dfs
from markets import Market

nodes = []


# Initialize Markets
def create_nodes():
    dfs = load_dfs()

    # Initialize Probelms
    for df in dfs:
        if df == 'pl':
            continue

        # Create Market
        market = Market(df, dfs[df])
        nodes.append(market)

        # Find Auturky Prices
        market.find_price()



if len(nodes) == 0:
    create_nodes()

for market in nodes:
    print(market.name, market.price)

for market in nodes:
    market.plot_functions("quantity")


# this is the wrong approach I need to write the LP I'm headed towards

'''

decision variables:

edges -- in {0,1}


max delta_w: 

subject to

existing_connections:

budget:

transmission loss:

supply x demand fuctions:

flow constraint: sum_ji

decision variables:

x_ij in connection_matrix for node i -> j
p_i is auturky price in market i
q_i is auturky quantity in market i
tr_i is transmission loss in market i
cp_i is connected price
cq_i is connected quantity

for all x_ij = 1, p_i < p_j * tr_i => connection update

p_i = fn_d(q_i) = fn_s(q_i)  ---- but I need to include the flow 








'''