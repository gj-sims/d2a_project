import numpy as np
from markets import Market
import math
import random

class Constants:
    def __init__(self):
        self.connection_matrix = np.zeros([12,12])
        self.index_dict = {'dk': 0,
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
                           'pl': 12}
        # Placeholder matrix
        ## this isn't right since it needs to be edge specific not direction-connection specific
        self.transmission_loss_matrix = np.random.uniform(0.5, 1.0, (12, 12))
        self.cost_to_create_matrix = np.zeros([12,12])
        self.nodes = []
    

    def connect(self, i: Market, j : Market):
        # Get indexes
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        # Connect both ways
        self.connection_matrix[i_index][j_index] = 1
        self.connection_matrix[j_index][i_index] = 1

    # # Constraint: Only transfer if profitable
    # # \forall x_ij \in conn_matrix == 1, p_i < (\delta * p_j)
    # # Fn returns true if transfer is profitable and false if not connected or unprofitable to transfer
    def worth_transfering(self, i: Market, j: Market):
        # Get indexes
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)

        # True is price in exporting market < price in importing market post loss
        if i.price < (j.price * self.transmission_loss_matrix[i_index][j_index]):
            return 1
        else:
            return 0

    # Finds distance between 2 markets
    def distance(self, i: Market, j: Market):
        #in km
        i_rad_lat = i.lat*(math.pi/180)
        j_rad_lat = j.lat*(math.pi/180)
        i_rad_lon = i.lon*(math.pi/180)
        j_rad_lon = j.lon*(math.pi/180)
        delta_phi = j_rad_lat - i_rad_lat
        delta_lam = j_rad_lon - i_rad_lon
        mean_phi = (j_rad_lat+j_rad_lon)/2
        dist =  6371*math.sqrt(delta_phi**2+(math.cos(mean_phi)*delta_lam)**2)
        #print('dist',dist)
        return dist

    # calculates cost to create new edge
    def cost_to_create(self, i: Market, j: Market):
        #print(i.name,j.name)
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        self.cost_to_create_matrix[i_index][j_index] = int(1.6 * self.distance(i,j))
        # https://www.nationalgrid.com/document/282876/download <- 1.6 figure
        return 

    # Uses connections to update equibibrium points
    def network_adjust(self):
        # loop through every node
        for i in self.nodes:
            best_guess = None
            # for now skip ro and pl
            if i.name == 'ro' or i.name == 'pl':
                continue

            new_price = 0
            min_price = max(i.supply["price"].min(), i.demand["price"].min())
            if min_price < 0:
                min_price = 0
            max_price = min(i.supply["price"].max(), i.demand["price"].max())
            i_node_index = self.index_dict.get(i.name)

            #bounds of those included in equation?
            min_x = None
            max_x = None

            # mid_price = (min_price + max_price)/2
            mid_price = min_price
            for k in range(100001):
                

                # balance constraint
                potential_exports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    # for now skip ro and pl
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = self.transmission_loss_matrix[i_node_index][j_node_index]
                    is_worth_transfering = self.worth_transfering(i,j)
                    potential_exports += (1/loss)*(is_connected)*(is_worth_transfering)*(j.inverse_supply(mid_price)-j.inverse_demand(mid_price))

                potential_imports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    # for now skip ro and pl
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = self.transmission_loss_matrix[i_node_index][j_node_index]
                    is_worth_transfering = self.worth_transfering(j,i)
                    potential_imports += (loss)*(is_connected)*(is_worth_transfering)*(j.inverse_demand(mid_price) - j.inverse_supply(mid_price))
                    
                # if total = 0 this price is a solution
                total = i.inverse_supply(mid_price) + potential_exports - i.inverse_demand(mid_price) - potential_imports
                #print(mid_price, total)

                if total < 1 and total > -1:
                    print(f'new equilibrium price found for {i.name}')
                    if mid_price - i.price > 1 or i.price - mid_price > 1:
                        print("price found is a new price")
                    break
                else:
                    # mid_price = random.randint(int(min_price), int(max_price))
                    mid_price +=(max_price - min_price )/100000

                if best_guess == None or total < best_guess:
                    if total > 0:
                        best_guess = mid_price
            if best_guess == None:
                i.adj_price = i.price
            i.adj_price = best_guess
            print(i.name, best_guess)

  