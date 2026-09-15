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

