# Market class
import numpy as np
from scipy.interpolate import interp1d

class Market:
    def __init__(self, name, df):
        # Market Name
        self.name = name

        # Supply df
        self.supply = (
            df[df["type"] == "supply"]
            .sort_values(["quantity", "price"])
            .reset_index(drop=True)
        )
        # Demand df
        self.demand = (
            df[df["type"] == "demand"]
            .sort_values(["quantity", "price"])
            .reset_index(drop=True)
        )
        # Supply Function
        self.supply_function = interp1d(
            self.supply["quantity"],
            self.supply["price"],
            kind="linear"
        )
        # Demand Function
        self.demand_function = interp1d(
            self.demand["quantity"],
            self.demand["price"],
            kind="linear"
        )
        # Connections
        self.connections = set()

        # Equilibrium
        self.price = None
        self.quantity = None
        self.transfers = []

        # Flow Constraints
        self.constr = 'TBD'

        # Location
        self.lat = None
        self.lon = None

    # Should connections be one-way or 2 way?
    def connect(self, Market):
        # Check if connected
        for conn in self.connections:
            if conn[0] == Market:
                return "Existing Connection"
            else:
                self.connections.add([Market, "TBD"])


