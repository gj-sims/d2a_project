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

       # Consumer and Producer Surpluses
    def integrate_step(self, x, y, upper):
        """
        Integrate a step function from x[0] to upper.

        The function assumes:
            y[i] applies from x[i] to x[i+1]

        This matches scipy interp1d(..., kind="previous").
        """
        total = 0

        for i in range(len(x) - 1):
            left = x[i]
            right = min(x[i + 1], upper)

            if right > left:
                total += y[i] * (right - left)

            if x[i + 1] >= upper:
                break

        return total

    def find_consumer_surplus(self, quantity, price):
        """
        Consumer surplus at a given equilibrium quantity and price.
        """
        demand_area = self.integrate_step(
            self.demand["quantity"].to_numpy(),
            self.demand["price"].to_numpy(),
            quantity
        )

        return demand_area - price * quantity

    def find_producer_surplus(self, quantity, price):
        """
        Producer surplus at a given equilibrium quantity and price.
        """
        supply_area = self.integrate_step(
            self.supply["quantity"].to_numpy(),
            self.supply["price"].to_numpy(),
            quantity
        )

        return price * quantity - supply_area

    def plot_surplus(self):
        """
        Plot the exact rectangles used by the surplus calculations.

        The shaded areas correspond directly to the calculations in
        find_consumer_surplus() and find_supplier_surplus().
        """
        if self.quantity is None or self.price is None:
            print("No equilibrium has been found.")
            return

        Q = self.quantity
        P = self.price

        supply_x = self.supply["quantity"].to_numpy()
        supply_y = self.supply["price"].to_numpy()

        demand_x = self.demand["quantity"].to_numpy()
        demand_y = self.demand["price"].to_numpy()

        # Calculate surplus using the actual functions
        consumer_surplus = self.find_consumer_surplus(Q, P)
        supplier_surplus = self.find_producer_surplus(Q, P)

        plt.figure(figsize=(12, 7))

        # Plot supply and demand
        plt.step(
            supply_x,
            supply_y,
            where="post",
            label="Supply"
        )

        plt.step(
            demand_x,
            demand_y,
            where="post",
            label="Demand"
        )

        # ---------------------------------------------------------
        # Consumer surplus
        # ---------------------------------------------------------
        for i in range(len(demand_x) - 1):
            left = demand_x[i]
            right = min(demand_x[i + 1], Q)

            if right <= left:
                break

            height = demand_y[i]

            # Only shade the portion ABOVE equilibrium price
            if height > P:
                plt.fill_between(
                    [left, right],
                    P,
                    height,
                    step="post",
                    alpha=0.3
                )

        # ---------------------------------------------------------
        # Producer surplus
        # ---------------------------------------------------------
        for i in range(len(supply_x) - 1):
            left = supply_x[i]
            right = min(supply_x[i + 1], Q)

            if right <= left:
                break

            height = supply_y[i]

            # Only shade the portion BELOW equilibrium price
            if height < P:
                plt.fill_between(
                    [left, right],
                    height,
                    P,
                    step="post",
                    alpha=0.3
                )

        # Equilibrium price
        plt.axhline(
            P,
            linestyle="--",
            label=f"Equilibrium price = {P:.2f}"
        )

        # Equilibrium quantity
        plt.axvline(
            Q,
            linestyle="--",
            label=f"Equilibrium quantity = {Q:.2f}"
        )

        # Equilibrium point
        plt.scatter(
            [Q],
            [P],
            zorder=5
        )

        # Display surplus values
        plt.text(
            Q * 0.05,
            P * 1.05,
            f"Consumer surplus = {consumer_surplus:.2f}"
        )

        plt.text(
            Q * 0.05,
            P * 0.85,
            f"Producer surplus = {supplier_surplus:.2f}"
        )

        plt.xlabel("Quantity")
        plt.ylabel("Price")
        plt.title(f"{self.name} — Consumer and Producer Surplus")
        plt.legend()
        plt.grid(True)

        plt.show()
    

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

        