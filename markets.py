# Market class
import numpy as np
from scipy.interpolate import interp1d
from scipy.integrate import quad
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar


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


    def find_consumer_surplus(self):
        # Find minimum domain
        min = self.demand_function.x.min()

        # Integrate functoin
        integral_value, error = quad(self.demand_function,
                                      min,
                                        self.quantity)

        # Subtract area below price
        non_surplus_area = (self.quantity - min) * self.price
        consumer_surplus = integral_value - non_surplus_area

        return consumer_surplus



    def find_producer_surplus(self):
       # Find price at minimum value
       min_y = self.supply_function.y.min()
       min_x = self.supply_function.x.min()

       if min_y >= 0:
           # Find surplus area
           surplus_area = (self.quantity-min_x) * self.price
           # Subtract integral
           integral_value, error = quad(self.supply_function,
                                        min_x,
                                        self.quantity)
           producer_surplus = surplus_area - integral_value
       else:
           # Shift up so graph is only in Q1
           shifted_supply = lambda x: self.supply_function(x) + -min_y
           # Find surplus area
           surplus_area = (self.quantity-min_x) * (self.price - min_y)
           # Subtract integral
           integral_value, error = quad(shifted_supply,
                                        min_x,
                                        self.quantity)
           producer_surplus = surplus_area - integral_value

       return producer_surplus

    
    def plot_consumer_surplus(self):
        min_quantity = self.demand_function.x.min()
        Q = self.quantity
        P = self.price

        total_area = 0
        surplus_area = 0

        plt.figure(figsize=(12, 7))

        # Plot demand
        x = self.demand_function.x
        y = self.demand_function.y

        plt.step(
            x,
            y,
            where="post",
            label="Demand"
        )

        # Sum and display the rectangles
        for i in range(len(x) - 1):

            left = x[i]
            right = min(x[i + 1], Q)

            if right <= left:
                continue

            height = y[i]
            width = right - left

            # Area under demand curve
            rectangle_area = width * height
            total_area += rectangle_area

            # Surplus portion of this rectangle
            if height > P:
                surplus_rectangle = width * (height - P)
                surplus_area += surplus_rectangle

                plt.fill_between(
                    [left, right],
                    P,
                    height,
                    step="post",
                    alpha=0.3
                )

            # Show the individual rectangle boundary
            plt.plot(
                [left, right, right],
                [height, height, height],
                linestyle=":",
                alpha=0.5
            )

            if right >= Q:
                break

        # Rectangle below equilibrium price
        non_surplus_area = (Q - min_quantity) * P

        # This should equal your find_consumer_surplus()
        calculated_surplus = total_area - non_surplus_area

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

        plt.scatter(
            [Q],
            [P],
            zorder=5
        )

        plt.text(
            min_quantity,
            P,
            f"  CS = {calculated_surplus:.2f}"
        )

        plt.xlabel("Quantity")
        plt.ylabel("Price")
        plt.title(f"{self.name} — Consumer Surplus")
        plt.legend()
        plt.grid(True)

        plt.show()

        print(f"Area under demand:       {total_area:.4f}")
        print(f"Area below price:        {non_surplus_area:.4f}")
        print(f"Consumer surplus:        {calculated_surplus:.4f}")
        print(f"find_consumer_surplus(): {self.find_consumer_surplus():.4f}")

    def plot_producer_surplus(self):
        min_y = self.supply_function.y.min()
        min_x = self.supply_function.x.min()

        Q = self.quantity
        P = self.price

        # Shift supply curve if it has negative values
        if min_y < 0:
            shift = -min_y
            shifted_supply = lambda x: self.supply_function(x) + shift
        else:
            shift = 0
            shifted_supply = self.supply_function

        x = self.supply_function.x
        y = self.supply_function.y

        rectangle_integral = 0
        rectangle_surplus = 0

        plt.figure(figsize=(12, 7))

        # Supply curve
        plt.step(
            x,
            y,
            where="post",
            label="Supply"
        )

        # --------------------------------------------------
        # Rectangles
        # --------------------------------------------------
        for i in range(len(x) - 1):

            left = x[i]
            right = min(x[i + 1], Q)

            if right <= left:
                continue

            width = right - left
            height = y[i]

            # Area under the original supply curve
            rectangle_integral += height * width

            # Producer surplus rectangle:
            # area between supply price and equilibrium price
            rectangle_area = (P - height) * width
            rectangle_surplus += rectangle_area

            plt.fill_between(
                [left, right],
                height,
                P,
                step="post",
                alpha=0.3
            )

            if right >= Q:
                break

        # --------------------------------------------------
        # Quad calculation
        # --------------------------------------------------
        quad_ps = self.find_producer_surplus()

        # Difference between rectangle and quad
        delta = rectangle_surplus - quad_ps

        # --------------------------------------------------
        # Equilibrium price
        # --------------------------------------------------
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

        # --------------------------------------------------
        # Display values
        # --------------------------------------------------
        print(f"PS from rectangles: {rectangle_surplus:.6f}")
        print(f"PS from quad:       {quad_ps:.6f}")
        print(f"Delta:              {delta:.6f}")

        plt.xlabel("Quantity")
        plt.ylabel("Price")
        plt.title(f"{self.name} — Producer Surplus")
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
            # There must exist a matrix of the connection
            # Using that matrix I would need to add to the list of connections for each market object
            # Then I would need to get the transmission loss, 
            # set up a system of equations using transmission loss and the inverted functions, and find price
            # resubtitute respectively to find the quantity
            # calculate the new surplus and the delta surplus
            # Then redo this all in a way gurobi can handle
            # Then add Daniels part


            return

        