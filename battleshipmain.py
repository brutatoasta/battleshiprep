import os
from os import system,name #do i need to import separately?
from os import sleep
##############
"""Global Variables"""
all_ships_dict = {"Carrier": 5 , "Battleship" : 4 , "Cruiser" : 3, "Submarine" : 3 , "Destroyer" : 2}
shot_list = []
ls_all_ships_points = []
##############
"""Set up Pyrebase"""
from libdw import pyrebase
from time import sleep

#add Firebase to application
projectid = "toat-11cda"
dburl = "https://" + projectid + ".firebaseio.com"
authdomain = projectid + ".firebaseapp.com"
apikey = "AIzaSyB7GpY2DNqjiWQeKnTN4Cn-jUu5RTNJMcU"
email = "joshuantw@gmail.com"
password = "password"

#for use with only user based authentication
config = {
    "apiKey": apikey,
    "authDomain": authdomain,
    "databaseURL": dburl,
}
"""
Pyrebase app can use multiple Firebase services such as:
firebase.auth() - Authentication

firebase.database() - Database

firebase.storage() - Storage
"""

firebase = pyrebase.initialize_app(config) #kick things off
auth = firebase.auth() #authentication service
user = auth.sign_in_with_email_and_password(email, password) #creation of first token
db = firebase.database() #database service
user = auth.refresh(user['refreshToken']) #renewal of token as tokens expire hourly
##############
"""generate unique id for each player to differentiate them in database"""
import string
import random
def generate_unique_id():
    letters = string.ascii_lowercase
    id_str = ""
    for i in range(4):
        id_str.join(random.choice(letters))
    return id_str 
##############
"""GUI Setup"""
"""
#initialise board as a 8 x 8 matrix of 0s
import matplotlib.pyplot as plt
board = plt.figure(figsize=[8,8])
board.patch.set_facecolor((1,1,.8))
ax = board.add_subplot(111)

# draw the grid
for x in range(10):
    ax.plot([x, x], [0,9], 'k')
for y in range(10):
    ax.plot([0, 9], [y,y], 'k')

# scale the axis area to fill the whole figure
ax.set_position([0,0,1,1])

# get rid of axes and everything (the figure background will show through)
ax.set_axis_off()

# scale the plot area conveniently (the board is in 0,0..18,18)
ax.set_xlim(-1,10)
ax.set_ylim(-1,10)
plt.show()
"""
##############
#Matching Phase
def ask_player_name():
    name = input("Please enter your name: ")
    print("Your name is: ", name )
    return name

# if player 2 has not joined, player 1 cannot start setting up his board.
"""
generates player 1 id and captures player 2 id. to create a list of player ids
All id are used as keys for database dictionaries
order of local ls_player_id matters but not that of database ls_player_id as
database version is just to exchange player id

"""
def get_id(P1_name):
    P1_id = generate_unique_id()
    print(P1_id)
    ls_player_id = db.child("Player_id").get(user['idToken']).val()
    id_timeout = 0 #max timeout is 15*5 seconds 
    
    #if no players, player 1 joins the game and update the database
    if (ls_player_id == None):
        print("joining game with id")
        db.child("Player_id").set([P1_id], user['idToken'])
    ls_player_id = list( db.child("Player_id").get(user['idToken']).val())
    while (len(ls_player_id) <=2) and (id_timeout <=15) :
        #if player 1 is the only one in the game, wait for player 2 
        if ls_player_id == [P1_id] :
            print("Player 2 has not yet joined.")
            sleep(5)
        #if player 1 is not in the game, but player 2 is, capture player 2 id,
        #player 1 joins the game and update the database
        elif len(ls_player_id) == 1 and ls_player_id != [P1_id]:
            print("Getting P2 id")
            P2_id = ls_player_id[0]
            ls_player_id = [P1_id, P2_id]
            db.child("Player_id").set(ls_player_id, user['idToken'])
        #if both players are in the game, capture player 2 id
        #no need to update the database
        elif len(ls_player_id) == 2 and P1_id in ls_player_id:
            ls_player_id.remove(P1_id)
            P2_id = ls_player_id[0]
            ls_player_id = [P1_id, P2_id]
            break
        else:
            print("get_id() error")
            break
        id_timeout += 1    
    return ls_player_id

def create_dict_player_name(P1_name, ls_player_id):
    P1_id = ls_player_id[0]
    P2_id = ls_player_id[1]
    #query a dictionary from the key "Player_name"
    dict_player_name = db.child("Player_name").get(user['idToken']).val()
    player_name_timeout = 0 #wait for max of 15*5 seconds to get player 2 name

    #if no names, write Player 1 name
    if dict_player_name == None:
        print("Adding Player 1")
        db.child("Player_name").set({P1_id : P1_name}, user['idToken'])
    dict_player_name = dict(db.child("Player_name").get(user['idToken']).val())
    while (len(dict_player_name) <=2) and (player_name_timeout <= 15) :
        if len(dict_player_name) == 1:
            #if player 1 name is inside and player 2 name is not yet written,wait
            if dict_player_name == {P1_id : P1_name}:
                print("Waiting for Player 2")
                sleep(5)
                continue
            #if player 1 name is not inside, but player 2 is
            #write player 1 name
            else:
                print("Player 2 is in the game. Joining game.")
                P2_name = dict_player_name[P2_id]
                dict_player_name = {P1_id : P1_name , P2_id : P2_name}
                db.child("Player_name").set(dict_player_name, user['idToken'])
                
        #if both player name in dictionary, break the while loop
        elif len(dict_player_name) == 2:
            print("both players are already in the game!")
            break
        else:
            print("create_dict_player_name() error")
        player_name_timeout +=1
    print(dict_player_name)    
    #use player 2 id to get player 2 name
    P2_name = dict_player_name.get(P2_id)
    print(P1_name, "is playing with", P2_name)
    return {P1_id : P1_name , P2_id : P2_name}

##############
#Setup Phase
class Point:
    def __init__(self, initX, initY):
        self.x = initX
        self.y = initY

def check_valid_point(point_str, thing):
    #returns False if string is in invalid format, True if valid.
    if (len(point_str) != 2) or (point_str[0].upper() not in "ABCDEFGHJK") or (point_str[1] not in "0123456789"):
        print("Please enter valid coordinates! e.g. B1")
        return False
        #Check if thing is within the board using ASCII index
    elif (ord(point_str[0]) > 75 or ord(point_str[0]) < 65 or ord(point_str[1]) > 57 or ord(point_str[1]) < 48): 
        print(thing, " is out of board!")
        return False
    else:
        return True
        
def place_stern(ship_name):
    stern_bool = False
    
    while stern_bool == False :
        stern_str = input("Where would you like the stern of your {} to be? e.g. A0. 'I' is not valid.".format(ship_name))#A0
        stern_bool = check_valid_point(stern_str, "Stern") #check if string is garbage
        if stern_bool == True:
            return Point( stern_str[0].upper() , stern_str[1] )
            #returns stern coordinates as a Point object

def generate_ship_sections(stern, ship_name, size ):
    direction_bool = False
    ls_points = [stern]
    
    while direction_bool == False:
        #Generating ships points based on direction
        direction = input("Which direction would you like your {} to face? [N/S/E/W] ".format(ship_name))
        direction = direction.upper()
        if direction in "NSEW":
            for i in range(1, size):
                if direction == "N":
                    ls_points.append(Point(stern.x, chr(ord(stern.y) - i)))
                elif direction == "W":
                    ls_points.append(Point(chr(ord(stern.x) + i) , stern.y))
                elif direction == "S":
                    ls_points.append(Point(stern.x, chr(ord(stern.y) + i)))
                elif direction == "E":
                    ls_points.append(Point(chr(ord(stern.x) - i) , stern.y))
            direction_bool = True
        else:
            print("Please type [N/S/E/W]!")
            direction_bool = False
            
    return ls_points

def check_ship_sections(ship_name, ls_points):
    points_valid = True
    #use ASCII numbering to check
    for point in ls_points:
        #if point is out of board, break for loop
        point_str = point.x + point.y
        if not check_valid_point(point_str, ship_name):
            points_valid = False
            break
        #check if point conflicts with another ship's points
        elif point in ls_all_ships_points:
            print(ship_name, " overlaps an existing ship!")
            points_valid = False
            break
        else:
            continue
    return points_valid


def place_ship(ship_name):
    global all_ships_dict
    global ls_all_ships_points # necessary to check if current ship conflicts with previously placed ship
    size = all_ships_dict.get(ship_name) #get ship's size from dictionary
    stern = place_stern(ship_name) #ask player for stern position
    
    ship_placed = False      
    while ship_placed == False:
        #generate list of ship points based on known stern and requested direction
        ls_points = generate_ship_sections(stern, ship_name, size)
        
        #check if the ships points are valid based on the known board and known ships
        points_valid = check_ship_sections(ship_name, ls_points)
        #if any of the ship's points are invalid, points_valid = False and the for loop breaks, restarting the while loop
        #If the for loop doesn't break, all ship points are valid and we set direction_bool to True to break the while loop
        if points_valid:
            ship_placed = True

    print("Ship placed!") #tell the player the ship is placed
    
    for i in ls_points: #add the ship's points to list of known ships points
        ls_all_ships_points.append(i)
    #maybe I dont need to return anything cos i just write it to database
    return [ship_name, ls_points]

#Takes a list of ship name and list of ship points
#Writes list of points to database for key: ship type, value is a dictionary with key as player id and value as list of ship coordinates
def write_ship(ship, P1_id):
    ship_name = ship[0]
    ls_points = ship[1]
    #gets the current dictionary for that ship_name
    ship_dict = db.child(ship_name).get(user['idToken']).val()

    if ship_dict == None:
        print("There are currently no ships.")
        ship_dict = {P1_id : ls_points}
    else:
        print("There are currently {} ships.".format(len(ship_dict)))
    ship_dict[P1_id] = ls_points
    db.child(ship_name).set(ship_dict, user['idToken'])
    print("{} written to {}!".format(ship_dict, ship_name))
    #returns nothing


##############        

##############        
def main():
    #initialise board
    board = get_zero_matrix(10,10)

    #Matching Phase
    #Ask for player name
    P1_name = ask_player_name()
    ls_player_id = get_id(P1_name)
    dict_player_name = create_dict_player_name(P1_name, ls_player_id)

    #Setup Phase
    print("SETUP PHASE: BEGIN!")
    #max timeout for Setup phase, after which it exits the game to reduce calls on database
    #timeouts need to be in place_ship()
    for ship_name in all_ships_dict:
        ship = place_ship(ship_name)
        write_ship(ship, P1_id)

    
    while P2_ready == False:
        sleep(5)
        print("Waiting on Player 2...")

    #War Phase
    start_id = choose_start(ls_player_id)
    game_not_over = True
    while game_not_over:
        #Choose who go first
        
        pass



