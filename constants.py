import numpy as np
from markets import Market
import math

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
    

    def connect(self, i: Market, j : Market):
        # Get indexes
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        # Connect both ways
        self.connection_matrix[i_index][j_index] = 1
        self.connection_matrix[j_index][i_index] = 1

    # Constraint: Only transfer if profitable
    # \forall x_ij \in conn_matrix == 1, p_i < (\delta * p_j)
    # Fn returns true if transfer is profitable and false if not connected or unprofitable to transfer
    def worth_transfering(self, i: Market, j: Market):
        # Get indexes
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)

        # Not connected
        if self.connection_matrix[i][j] == 0:
            return False

        # True is price in exporting market < price in importing market post loss
        if i.price < (j.price * self.self.transmission_loss_matrix[i][j]):
            return True
        else:
            return False

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

    def cost_to_create(self, i: Market, j: Market):
        #print(i.name,j.name)
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        self.cost_to_create_matrix[i_index][j_index] = int(1.6 * self.distance(i,j))
        return 



# test = Constants()
# print(test.transmission_loss_matrix)