# Main for D2A Project
from load_data import load_dfs
from markets import Market
from constants import Constants

problem = Constants()
problem.nodes = []



# Initialize Markets
def create_nodes():
    dfs = load_dfs()

    # Initialize Probelms
    for df in dfs:
        if df == 'pl':
            continue

        # Create Market
        market = Market(df, dfs[df])
        problem.nodes.append(market)

        # Find Auturky Prices
        market.find_price()


def add_coordinates():
    # ignoring pl and ro for now
    for market in problem.nodes:
        if market.name == 'at':
            market.lat = 48.2085
            market.lon = 16.3721
        elif market.name == 'be':
            market.lat = 50.8505
            market.lon = 4.3488
        elif market.name == 'ger':
            market.lat = 52.5200
            market.lon = 13.4050
        elif market.name == 'fr':
            market.lat = 48.8566
            market.lon = 2.3522
        elif market.name == 'nl':
            market.lat = 52.37
            market.lon = 4.89
        elif market.name == 'dk':
            market.lat = 55.6761
            market.lon = 12.5683
        elif market.name == 'fi':
            market.lat = 60.17
            market.lon = 24.94
        elif market.name =='no':
            market.lat = 59.91
            market.lon = 10.75
        elif market.name == 'se':
            market.lat =  59.33
            market.lon = 18.06
        elif market.name == 'bg':
            market.lat = 42.73
            market.lon = 25.49
        elif market.name == 'lv': # Estonia capital
            market.lat =  59.437
            market.lon = 24.754




# Initialze Markets
if len(problem.nodes) == 0:
    create_nodes()

# Print node indexes for reference
for i in range(len(problem.nodes)):
    print(i,problem.nodes[i].name)

# Add coordinates
add_coordinates()

# Add cost to create connections
for i in problem.nodes:
    for j in problem.nodes:
        if ((i.name == 'pl') or (j.name == 'pl')):
            continue
        elif ((i.name == 'ro') or (j.name == 'ro')):
            continue
        elif (i.name != j.name):
            problem.cost_to_create(i,j)

#print("CREATE MATRIX",problem.cost_to_create_matrix)

# Make Some Connections
problem.connect(problem.nodes[7],problem.nodes[9])
problem.connect(problem.nodes[7],problem.nodes[3])
problem.connect(problem.nodes[3],problem.nodes[8])
problem.connect(problem.nodes[8],problem.nodes[6])
problem.connect(problem.nodes[6],problem.nodes[0])
problem.connect(problem.nodes[2],problem.nodes[0])
problem.connect(problem.nodes[0],problem.nodes[5])
problem.connect(problem.nodes[6],problem.nodes[4])
problem.connect(problem.nodes[4],problem.nodes[10])
problem.connect(problem.nodes[4],problem.nodes[1])
problem.connect(problem.nodes[10],problem.nodes[1])

pre_surplus = 0
for market in problem.nodes:
    if market.name == 'ro' or market.name == 'pl':
        continue
    pre_surplus += market.find_consumer_surplus() + market.find_producer_surplus()
print("SURPLUSS:", pre_surplus)

print(problem.connection_matrix)

for i in range(len(problem.connection_matrix)):
    for j in range(len(problem.connection_matrix)):
        if problem.connection_matrix[i][j] == 1:
            for mar_1 in problem.nodes:
                for mar_2 in problem.nodes:
                    if problem.index_dict.get(mar_1.name) == i and  problem.index_dict.get(mar_2.name) == j:
                        print(mar_1.name, mar_2.name, problem.worth_transfering(mar_1,mar_2), '|', mar_1.price, mar_2.price, 
                              problem.transmission_loss_matrix[problem.index_dict.get(mar_1.name)][ problem.index_dict.get(mar_2.name)] )


problem.network_adjust()

post_surplus = 0
for market in problem.nodes:
    if market.name == 'ro' or market.name == 'pl':
            continue
    post_surplus += market.find_consumer_surplus() + market.find_producer_surplus()
print("SURPLUSS:", post_surplus)


print("DID THIS WORK (NO!)", post_surplus-pre_surplus)

# for market in problem.nodes:
#     market.plot_functions("quantity")
#     market.plot_functions("price")
    

# #Current total surplus
# total_surplus = 0
# for market in nodes:
#     print(market.name)
#     print("TOTAL SURPLUS", total_surplus)
#     if market.name == 'ro':
#         continue

#     print(market.name, market.find_producer_surplus())
#     total_surplus+= int(market.find_producer_surplus())
#     total_surplus+= int(market.find_consumer_surplus())


# NEED TO INITIALIZE PROBLEM



# for market in nodes:
#     print(market.name, market.find_producer_surplus())
#     market.plot_producer_surplus()

# for market in nodes:
#     print(market.name, market.price)



# #Vibecoding didn't work I need to do myself
# for market in nodes:
#     CS = market.find_consumer_surplus(market.quantity, market.price)
#     PS = market.find_producer_surplus(market.quantity, market.price)
#     print(market.name, f"Consumer Surplus: {CS}", f"Producer Surplus: {PS}")

# # this is the wrong approach I need to write the LP I'm headed towards
# for market in nodes:
#     market.plot_surplus()

# '''

# decision variables:

# edges -- in {0,1}


# max delta_w: 

# subject to

# existing_connections:

# budget:

# transmission loss:

# supply x demand fuctions:

# flow constraint: sum_ji

# decision variables:

# x_ij in connection_matrix for node i -> j
# p_i is auturky price in market i
# q_i is auturky quantity in market i
# tr_i is transmission loss in market i
# cp_i is connected price
# cq_i is connected quantity

# for all x_ij = 1, p_i < p_j * tr_i => connection update

# p_i = fn_d(q_i) = fn_s(q_i)  ---- but I need to include the flow
# '''

# constr: s_i(p)+Q+Q =demand eq where binary flags are there if transfering mmakes sense










# '''