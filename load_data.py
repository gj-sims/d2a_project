
import sys 
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


def load_dfs():

    folder = 'data'

    # Store all resulting dataframes here
    dfs = {}

    for file in os.listdir(folder):

        # Only process .txt files
        if not file.endswith('.txt'):
            continue

        # File name without .txt
        name = os.path.splitext(file)[0]
        if name == 'baltic':
            name = 'lv'
        elif name == 'de_lu':
            name = 'ger'

        # Open file
        with open(os.path.join(folder, file), 'r') as f_in:
            data = f_in.readlines()

        # Initialize df
        df = pd.DataFrame({
            "type": [],
            "price": [],
            "quantity": []
        })

        # Split json
        data_list = data[0].split('},')

        for i in range(len(data_list)):

            # Skip headers
            if i == 0:
                continue


            # Break when we reach the file/dataset name
            if name.upper() in data_list[i].upper():
                break

            # Find Demand Info
            if data_list[i].find("demand") != -1:

                dp = data_list[i][data_list[i].find("demandPrice"):]

                demandPrice = dp[dp.find(':') + 1: dp.find(',')]

                dq = dp[dp.find('demandQuantity'):]

                if data_list[i].find('supply') == -1:
                    demandQuantity = dq[dq.find(':') + 1:]
                else:
                    demandQuantity = dq[dq.find(':') + 1: dq.find(',')]

                demand_row = {
                    'type': 'demand',
                    'price': demandPrice,
                    'quantity': demandQuantity
                }

                df = pd.concat(
                    [df, pd.DataFrame([demand_row])],
                    ignore_index=True
                )

            # Find Supply Info
            if data_list[i].find("supply") != -1:

                sp = data_list[i][data_list[i].find("supplyPrice"):]

                supplyPrice = sp[sp.find(':') + 1: sp.find(',')]

                sq = data_list[i][data_list[i].find("supplyQuantity"):]

                supplyQuantity = sq[sq.find(':') + 1:]

                supply_row = {
                    'type': 'supply',
                    'price': supplyPrice,
                    'quantity': supplyQuantity
                }

                df = pd.concat(
                    [df, pd.DataFrame([supply_row])],
                    ignore_index=True
                )

        # Convert to numeric
        df['quantity'] = pd.to_numeric(
            df['quantity'],
            errors='coerce'
        )

        df['price'] = pd.to_numeric(
            df['price'],
            errors='coerce'
        )

        # Store dataframe using filename as key
        dfs[name] = df

        print(name, 'done')

    print('DONE')

    return dfs


def plot_dfs(dfs):

    fig, axes = plt.subplots(
        3,
        5,
        figsize=(20, 12)
    )

    axes = axes.flatten()

    for ax, (name, df) in zip(axes, dfs.items()):

        supply = (
            df[df["type"] == "supply"]
            .sort_values(["quantity", "price"])
        )

        demand = (
            df[df["type"] == "demand"]
            .sort_values(["quantity", "price"])
        )

        ax.plot(
            supply["quantity"],
            supply["price"],
            marker="o",
            label="supply"
        )

        ax.plot(
            demand["quantity"],
            demand["price"],
            marker="o",
            label="demand"
        )
        
        ax.set_title(name)
        ax.set_xlabel("Quantity")
        ax.set_ylabel("Price")
        ax.legend()
        ax.grid(True)

    # Hide unused subplots
    for ax in axes[len(dfs):]:
        ax.set_visible(False)

    plt.tight_layout()
    plt.show()
    


# I should make a folder for this project and make some oop infrastructure 
# like each market as a market object that can connect given a graph etc.