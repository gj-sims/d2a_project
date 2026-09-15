# Market class
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

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
            kind="previous"
        )
        # Demand Function
        self.demand_function = interp1d(
            self.demand["quantity"],
            self.demand["price"],
            kind="previous"
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

    # Plot functions
    def plot_functions(market):

        supply = market.supply
        demand = market.demand

        plt.figure(figsize=(10, 6))

        # Evaluate the functions across their domains
        supply_x = np.linspace(
            supply["quantity"].min(),
            supply["quantity"].max(),
            1000
        )

        demand_x = np.linspace(
            demand["quantity"].min(),
            demand["quantity"].max(),
            1000
        )

        plt.step(
            supply_x,
            market.supply_function(supply_x),
            where="post",
            label="Supply function"
        )

        plt.step(
            demand_x,
            market.demand_function(demand_x),
            where="post",
            label="Demand function"
        )

        plt.xlabel("Quantity")
        plt.ylabel("Price")
        plt.title(market.name)
        plt.legend()
        plt.grid(True)

        plt.show()

    def find__consumer_surplus():
        return

    def find_supplier_surplus():
        return
    

    def find_price(self):
        # Find Price in Auturky
        if len(self.connections) == 0:
            # Choose smaller range
            sup_max = self.supply["quantity"].max()
            sup_min = self.supply["quantity"].min()
            dem_max = self.demand["quantity"].max()
            dem_min = self.demand["quantity"].min()
            both_max = min(dem_max, sup_max)
            both_min = max(dem_min, sup_min)

            # Iteratively compare and shift guess towards equilibrium
            mid = (both_max+both_min)/2
            sup = self.supply_function(mid)
            dem = self.demand_function(mid)
            i = 0
            for j in range(30):

                mid = (both_max + both_min) / 2

                sup = self.supply_function(mid)
                dem = self.demand_function(mid)

                if sup >= dem:
                    both_max = mid
                else:
                    both_min = mid

                if both_max - both_min < 1:
                    break

                self.quantity = mid
                self.price = self.demand_function(mid)
                i+= 1
            if i < 30:
                self.quantity = mid
                self.price = self.demand_function(mid)
                print(f"Equilibrium Found for {self.name}")
            else: 
                print(f"Equilibrium not found for {self.name} in time")
        else:
            # Connected market EQ
            return


        