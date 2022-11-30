#Code that runs to control the esp32 and get the capacity. Both this file and the 
#telegram bot file will be running concurrently. The csv file and the telegram bot 
#reads from that file

from attr import ib
from numpy import true_divide
import paho.mqtt.client as mqtt
import pandas as pd
import time
from datetime import datetime
import requests #for sending messages to the debugging bot
import urllib.parse
import traceback

#Files we will manipulate
csv_records = 'DHCapacityRecords.csv'
capacity_text_file = 'capacity.txt'

door_mapping = {
    # 'mac_address': 'door_name'
}

door_connection_time = {
    # 'mac_address' : time connected
}

#Store here and update the CSV and textfile
storage = {
    'Time':[],
    'Door':[],
    'Number':[],
    'Summation':[]
}

def telegram_bot_sendtext(bot_message):
    
    bot_message = urllib.parse.quote(bot_message, safe="") # Encode message to URL-safe text
    bot_token = 'LOG_BOT_TOKEN' #Bot Token for bot to send messages
    bot_chatID = 'LOG_GROUP_ID' #Group ID for group where debugging emssages are sent
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&text=' + bot_message

    try:
        response = requests.get(send_text, timeout=1)
        print("Telegram debug message sent:", response.text)
    except:
        print("Telegram debug message error:")
        traceback.print_exc()

    return "Message Sent"

#Update File functions
def update_cap(cap):
    with open(capacity_text_file,"w") as f:
        f.write(str(cap))
    
    text = "Text File Capacity Updated to " + str(cap)
    telegram_bot_sendtext(text)

def is_storage_empty():
    for headers in storage.keys():
        if storage[headers] != []:
            return False

    return True

def update_txt():
    df = pd.read_csv(csv_records,index_col = 0)

    #At the same time as updating the csv, i update a text file that stores the last capacity. And we read it.
    #lower memory and faster than reading the csv file from scratch
    data = pd.DataFrame(storage)
    if(is_storage_empty()):
        text = "CSV file not updated because storage is empty"
        telegram_bot_sendtext(text)
        return
    try:
        last_capacity = data.iloc[-1,-1]
        update_cap(last_capacity)
    except IndexError:
        # this function was called when storage is empty,
        # so last capacity does not exist
        last_capacity = 0
        update_cap(last_capacity)

    new_df = pd.concat([df,data], ignore_index = True)
    new_df.to_csv(csv_records)

    for headers in storage.keys(): #clear dictionary
        storage[headers] = []

def update_connection():
    text = "Connection Status" #send telegram message on the connection status
    time_now = datetime.now()

    try:
        for mac_address in door_connection_time.keys(): #print time last connected in minutes
            text += "\n" + mac_address +": " + str( (time_now - door_connection_time[mac_address]).seconds //60)
    except:
        print("There is something wrong with updating of connections :( ")
    
    telegram_bot_sendtext(text)

def update_records(time,door,number,*summation):
    
    if summation == ():
        if storage['Summation'] == []:
            summation = number
        else:
            summation = number + storage['Summation'][-1]
    else:
        summation = summation[0]
    
    storage['Time'].append(time)
    storage['Door'].append(door)
    storage['Number'].append(number)
    storage['Summation'].append(int(summation)) #it became a float during testing, this is to make sure it is an integer

# MQTT CODE START
def MQTT_on_connect(client, userdata, flags, rc):  # The callback for when the client connects to the broker
    print("MQTT connected with result code {0}".format(str(rc)))  # Print result of connection attempt
    client.subscribe("dh_topic/#")  # Subscribe to the topic

def MQTT_on_message(client, userdata, msg):  # The callback for when a PUBLISH message is received from the server.
    current_formatted_time = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    print("MQTT Message received", current_formatted_time, ":", msg.topic, str(msg.payload))  # Print a received msg

    # Get name and device mac from the topic
    topic_components = str(msg.topic).split('/')
    topic_name = topic_components[1]
    device_mac = topic_components[2]
    if len(topic_components) >= 4:
        extra_info = topic_components[3]

    # Map MAC address to door name
    if device_mac in door_mapping:
        door = door_mapping[device_mac]
    else:
        door = device_mac

    if topic_name == 'test':
        print("=> ESP32 has just connected:" + device_mac + " IP: " + extra_info)
        telegram_bot_sendtext("=> ESP32 has just connected:" + device_mac + " IP: " + extra_info)
        

    elif topic_name == 'increment':
        print("=> Door increment:" + device_mac)
        update_records(current_formatted_time, door, 1)
        telegram_bot_sendtext("=> Door increment:" + device_mac)

    elif topic_name == 'decrement':
        print("=> Door decrement:" + device_mac)
        update_records(current_formatted_time, door, -1)
        telegram_bot_sendtext("=> Door decrement:" + device_mac)

    elif topic_name == 'connection':
        print("=> Sensor alive:" + device_mac)
        
    elif topic_name == 'reconnect':
        text = "=> Reconnect time:" + device_mac + " -> " + extra_info + "ms"
        print(text)
        telegram_bot_sendtext(text)
    
    
    door_connection_time[device_mac] = datetime.now() #record time connected each time it recieves a topic from a certain mac address

def MQTT_start():
    client = mqtt.Client("digi_mqtt_test")  # Create instance of client with client ID “digi_mqtt_test”
    client.on_connect = MQTT_on_connect  # Define callback function for successful connection
    client.on_message = MQTT_on_message  # Define callback function for receipt of a message
    client.connect('127.0.0.1', 1883) # Connect to localhost server
    # client.loop_forever()  # runs the networking daemon in the current thread
    client.loop_start() # starts a new thread in the background to run the network loop

# MQTT CODE END

if __name__ == '__main__':
    
    update_timings_mins = []
    update_interval = 10
    for i in range(0,60,update_interval):
        update_timings_mins.append(i) #find out when to update the text file to show the desired capacity

    reset_timings_hours = [6,11,17,22] #find out when to reset the capacity to zero

    
    update_min_index = 0
    min_cycle_finished = True #if the min > 55, then the cycle has finished 
    max_min_index = len(update_timings_mins) -1 #the maximum the index can go to is minus 1 of the length
    current_time_mins = time.localtime().tm_min 
    for i in range(max_min_index + 1): 
        if update_timings_mins[i] > current_time_mins: # the only case it will not hit is when min > 55
            update_min_index = i #update_timings[i] gives us the next time to update the file
            min_cycle_finished = False
            break

    #do same for hours
    reset_hour_index = 0
    reset_cycle_finished = True
    max_hour_index = len(reset_timings_hours) - 1
    current_time_hours = time.localtime().tm_hour
    for i in range(max_hour_index + 1):
        if reset_timings_hours[i] > current_time_hours:
            reset_hour_index = i
            reset_cycle_finished = False
            break


    MQTT_start()
    text = "DH Capacity System has been setup"
    telegram_bot_sendtext(text)

    while True:
        current_time = time.localtime()
        hour = current_time.tm_hour
        min = current_time.tm_min

        #update txt file
        if( (update_timings_mins[update_min_index] == min) and (min_cycle_finished == False) ):
            if(update_min_index == max_min_index ):
                update_min_index = 0
                min_cycle_finished = True
            else:
                update_min_index += 1
            
            update_txt()
            update_connection()
            print("Text file has been updated at minute " + str(min))        
        elif(min == 0):
            min_cycle_finished = False #reset flag as one round has been finsihed



        #reset numbers at certain timings
        if( (reset_timings_hours[reset_hour_index] == hour) and (reset_cycle_finished == False) ):
            if(reset_hour_index == max_hour_index ):
                reset_hour_index = 0
                reset_cycle_finished = True
            else:
                reset_hour_index += 1
            
            update_records(
                        datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), #time
                        "RESET", #door
                        0, #number 
                        0 #summation //reset
                    )
            text = "DH Capacity has been reset to zero"
            telegram_bot_sendtext(text)        
        elif(hour == 0):
            reset_cycle_finished = False #reset flag as one round has been finsihed

        
        
        # Sleep to reduce CPU time usage
        time.sleep(1)


        

        




