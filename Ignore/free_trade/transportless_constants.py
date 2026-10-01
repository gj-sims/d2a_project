from __future__ import annotations

import math
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from markets import Market


class transportless_constants:
    def __init__(self):
        self.connection_matrix = np.zeros([12, 12])
        self.index_dict = {
            'dk': 0,
            'lv': 1,
            'ger': 2,
            'fr': 3,
            'se': 4,
            'no': 5,
            'nl': 6,
            'at': 7,
            'be': 8,
            'bg': 9,
            'fi': 10,
            'ro': 11,
            'pl': 12,
        }
        # Transportless: all losses are 1.
        self.transmission_loss_matrix = np.ones([12, 12])
        self.cost_to_create_matrix = np.zeros([12, 12])
        self.nodes = []

    def connect(self, i: Market, j: Market):
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        self.connection_matrix[i_index][j_index] = 1
        self.connection_matrix[j_index][i_index] = 1

    def worth_transfering(self, i: Market, j: Market):
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        mean_loss = (
            self.transmission_loss_matrix[i_index][j_index]
            + self.transmission_loss_matrix[j_index][i_index]
        ) / 2

        if i.price < (j.price * mean_loss):
            return 1
        else:
            return 0

    def distance(self, i: Market, j: Market):
        i_rad_lat = i.lat * (math.pi / 180)
        j_rad_lat = j.lat * (math.pi / 180)
        i_rad_lon = i.lon * (math.pi / 180)
        j_rad_lon = j.lon * (math.pi / 180)
        delta_phi = j_rad_lat - i_rad_lat
        delta_lam = j_rad_lon - i_rad_lon
        mean_phi = (j_rad_lat + j_rad_lon) / 2
        dist = 6371 * math.sqrt(delta_phi**2 + (math.cos(mean_phi) * delta_lam) ** 2)
        return dist

    def cost_to_create(self, i: Market, j: Market):
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        self.cost_to_create_matrix[i_index][j_index] = int(1.6 * self.distance(i, j))
        return

    def network_adjust(self):
        for i in self.nodes:
            best_guess = None
            best_total = None
            if i.name == 'ro' or i.name == 'pl':
                continue

            min_price = max(i.supply["price"].min(), i.demand["price"].min())
            if min_price < 0:
                min_price = 0
            max_price = min(i.supply["price"].max(), i.demand["price"].max())
            i_node_index = self.index_dict.get(i.name)

            for _ in range(1001):
                mid_price = (min_price + max_price) / 2
                potential_exports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = (
                        self.transmission_loss_matrix[i_node_index][j_node_index]
                        + self.transmission_loss_matrix[j_node_index][i_node_index]
                    ) / 2
                    is_worth_transfering = self.worth_transfering(i, j)
                    potential_exports += (
                        (1 / loss)
                        * (is_connected)
                        * (is_worth_transfering)
                        * (j.inverse_supply(j.price) - j.inverse_demand(j.price))
                    )

                potential_imports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = (
                        self.transmission_loss_matrix[i_node_index][j_node_index]
                        + self.transmission_loss_matrix[j_node_index][i_node_index]
                    ) / 2
                    is_worth_transfering = self.worth_transfering(j, i)
                    potential_imports += (
                        loss
                        * (is_connected)
                        * (is_worth_transfering)
                        * (j.inverse_demand(j.price) - j.inverse_supply(j.price))
                    )

                total = i.inverse_supply(mid_price) + potential_exports - i.inverse_demand(mid_price) - potential_imports

                if total > -0.0001 and total < 0.0001:
                    if abs(1 - mid_price / i.price) > 0.05:
                        print(f"price found for  {i.name}")
                        i.adj_price = mid_price
                        break
                elif total < -0.0001:
                    min_price = mid_price
                    if best_guess is None or abs(total) < abs(best_total):
                        best_guess = mid_price
                        best_total = total
                elif total > 0.0001:
                    max_price = mid_price
                    if best_guess is None or abs(total) < abs(best_total):
                        best_guess = mid_price
                        best_total = total
                else:
                    print("error")
            print(i.name, best_guess, best_guess / i.price)

            if abs(1 - best_guess / i.price) > 0.05:
                i.adj_price = best_guess
            else:
                i.adj_price = i.price


TransportlessConstants = transportless_constants

__all__ = ["transportless_constants", "TransportlessConstants"]
