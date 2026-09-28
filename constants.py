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
        self.transmission_loss_matrix = np.random.uniform(0.35, 1.0, (12, 12))
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

        # if self.connection_matrix[i_index][j_index] == 0:
        #     return 0

        mean_loss = (self.transmission_loss_matrix[i_index][j_index] + self.transmission_loss_matrix[j_index][i_index])/2

        # True is price in exporting market < price in importing market post loss
        if i.price < (j.price * mean_loss):
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
            best_total = None
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
            for k in range(1001):

                mid_price = (min_price + max_price ) / 2

                # balance constraint
                potential_exports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    # for now skip ro and pl
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = (self.transmission_loss_matrix[i_node_index][j_node_index]+self.transmission_loss_matrix[j_node_index][i_node_index])/2
                    is_worth_transfering = self.worth_transfering(i,j)
                    potential_exports += ((1/loss)*(is_connected)*(is_worth_transfering)*(j.inverse_supply(j.price)-j.inverse_demand(j.price)))

                potential_imports = 0
                for j in self.nodes:
                    j_node_index = self.index_dict.get(j.name)
                    # for now skip ro and pl
                    if j.name == 'ro' or j.name == 'pl':
                        continue
                    is_connected = self.connection_matrix[i_node_index][j_node_index]
                    loss = (self.transmission_loss_matrix[i_node_index][j_node_index]+self.transmission_loss_matrix[j_node_index][i_node_index])/2
                    is_worth_transfering = self.worth_transfering(j,i)
                    potential_imports += ((loss)*(is_connected)*(is_worth_transfering)*(j.inverse_demand(j.price) - j.inverse_supply(j.price)))

                
                
                # if total = 0 this price is a solution
                total = i.inverse_supply(mid_price) + potential_exports - i.inverse_demand(mid_price) - potential_imports
                #print(mid_price, total)

                # if (total < 500 and total > -500):
                #     print(
                #         "mid =", mid_price,
                #         "exports =", potential_exports,
                #         "imports =", potential_imports,
                #         "autarky excess =",
                #         i.inverse_supply(mid_price) - i.inverse_demand(mid_price),
                #         "total =", total
                #     )

                if total > -.0001 and total < .0001:
                      if abs(1-mid_price/i.price) > .05:
                            print(f"price found for  {i.name}")
                            i.adj_price = mid_price
                            #print(i.name, min_price, 1-min_price/i.price)
                            break
                elif total < -.0001:
                      min_price = mid_price
                      if best_guess == None or abs(total) < abs(best_total): 
                        best_guess = mid_price
                        best_total = total

                elif total > .0001:
                      max_price = mid_price
                      if best_guess == None or abs(total) < abs(best_total): 
                        best_guess = mid_price
                        best_total = total
                else:
                      print("error")
            print(i.name, best_guess, best_guess/i.price)

            if abs(1-best_guess/i.price) > .05:
                i.adj_price = best_guess
            else:
                i.adj_price = i.price
                #print("good enough", i.name, abs(i.adj_price-i.price))



            #     if best_guess == None or abs(total) < abs(best_total):
            #         # if total > 0:
            #             best_guess = mid_price
            #             best_total = total



            #      if sup >= dem:
            #                         both_max = mid
            #                     else:
            #                         both_min = mid
                
            #                     if both_max - both_min < .0001:
            #                         self.quantity = mid
            #                         self.price = self.demand_function(mid)
            #                         break
                



            #     # maybe a differnt threshold???
            #     if best_guess != None:
            #         if total < 1 and total > -1:

            #             print(f'new equilibrium price found for {i.name}')
            #             if ((best_guess - i.price) > 1) or ((i.price - best_guess) > 1):
            #                 print("price found is a new price")
            #                 i.adj_price = best_guess
            #                 break
            #         else:
            #             # mid_price = random.randint(int(min_price), int(max_price))
            #             #print('hit')
                        
            #             mid_price +=(max_price - min_price )/1000
            #             i.adj_price = i.price
            #     else:
            #         # mid_price = random.randint(int(min_price), int(max_price))
            #         p#rint('hit')
            #         mid_price +=(max_price - min_price )/1000
            #         i.adj_price = i.price

            #     #print(i.name, mid_price, total)
            # perc = 0
            # if best_guess != None:
            #     perc = best_guess/i.price
            # print(i.name, best_guess, perc)
            

  