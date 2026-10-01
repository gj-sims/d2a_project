# Market class
import numpy as np
from scipy.interpolate import interp1d
from scipy.integrate import IntegrationWarning, quad
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar
import warnings


warnings.filterwarnings("ignore", category=IntegrationWarning)


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

        # Equilibrium
        self.price = None
        self.quantity = None

        self.adj_price = None
        self.adj_quantity = None

        # Location
        self.lat = None
        self.lon = None

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
