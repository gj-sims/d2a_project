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
        #self.transmission_loss_matrix = np.random.uniform(0.35, 1.0, (12, 12))
        # self.transmission_loss_matrix = np.ones([12,12])
        self.cost_to_create_matrix = np.zeros([12,12])
        self.nodes = []


        # 1. Generate the initial random matrix
        raw_matrix = np.random.uniform(0.5, 1.0, (12, 12))

        # 2. Make it symmetric by averaging it with its transpose
        self.transmission_loss_matrix = (raw_matrix + raw_matrix.T) / 2
    

    def connect(self, i: Market, j : Market):
        # Get indexes
        i_index = self.index_dict.get(i.name)
        j_index = self.index_dict.get(j.name)
        # Connect both ways
        self.connection_matrix[i_index][j_index] = 1
        self.connection_matrix[j_index][i_index] = 1


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

   
            

  