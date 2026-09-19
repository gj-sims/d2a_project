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

        # Inverse Supply Function:
        supply_inverse = (
            self.supply
            .groupby("price")["quantity"]
            .max()
            .sort_index()
        )

        self.inverse_supply = interp1d(
            supply_inverse.index,
            supply_inverse.values,
            kind="previous",
            bounds_error=False,
            fill_value=(supply_inverse.iloc[0], supply_inverse.iloc[-1])
        )

        # Inverse Demand Function: 
        demand_inverse = (
            self.demand
            .groupby("price")["quantity"]
            .max()
            .sort_index()
        )

        self.inverse_demand = interp1d(
            demand_inverse.index,
            demand_inverse.values,
            kind="previous",
            bounds_error=False,
            fill_value=(demand_inverse.iloc[0], demand_inverse.iloc[-1])
        )

        # Connections
        self.connections = set()

        # Equilibrium
        self.price = None
        self.quantity = None
        self.transfers = []

        # Flow Constraints
        self.constr = 'TBD'
        self.random_placeholder = np.random.default_rng()

        # Location
        self.lat = None
        self.lon = None

    # Should connections be one-way or 2 way?
    def connect(self, market):
        # Check if connected
        for conn in self.connections:
            if conn[0] == market:
                return "Existing Connection"
            else:
                self.connections.add([market, "TBD"])
                return f"{self.name} connected to {market.name}"

    # Plot functions
    def plot_functions(self, input="quantity"):

        supply = self.supply
        demand = self.demand

        plt.figure(figsize=(10, 6))

        if input == "quantity":
            # Quantity -> Price
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
                self.supply_function(supply_x),
                where="post",
                label="Supply function"
            )

            plt.step(
                demand_x,
                self.demand_function(demand_x),
                where="post",
                label="Demand function"
            )

            plt.xlabel("Quantity")
            plt.ylabel("Price")

        elif input == "price":
            # Price -> Quantity
            supply_x = np.linspace(
                supply["price"].min(),
                supply["price"].max(),
                1000
            )

            demand_x = np.linspace(
                demand["price"].min(),
                demand["price"].max(),
                1000
            )

            plt.step(
                supply_x,
                self.inverse_supply(supply_x),
                where="post",
                label="Inverse supply"
            )

            plt.step(
                demand_x,
                self.inverse_demand(demand_x),
                where="post",
                label="Inverse demand"
            )

            plt.xlabel("Price")
            plt.ylabel("Quantity")

        else:
            raise ValueError("input must be either 'quantity' or 'price'")

        plt.title(self.name)
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
            # Connected market EQ, also need to determine who gets to transfer first probably
            # for m in self.connections:
            #     if self.price > m[0].price * self.random_placeholder.random():
            #         # Transfer
            #         supply() - demand() 

            return


        