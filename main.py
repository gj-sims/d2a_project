# Main for D2A Project
from load_data import load_dfs
import markets

nodes = []


def create_nodes():
    dfs = load_dfs()
    for df in dfs:
        market = Market(df, dfs[df])
        nodes.append(market)
print(nodes)