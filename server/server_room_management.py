import socket
import os
import time
from pathlib import Path

SERVER_ADDRESS = "0.0.0.0"
SERVER_PORT = 9001
STREAM_RATE = 4096
MESSAGE_OK = "OK"




def protocol_header(room_name_length, operation, state, data_length):
    return room_name_length.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + state.to_bytes(1, 'big') + data_length.to_bytes(29,"big")

def tcp_room_manage(rooms):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('Starting up on {} port {}'.format(SERVER_ADDRESS, SERVER_PORT))

    sock.bind((SERVER_ADDRESS, SERVER_PORT))
    sock.listen(1)

    while True:

        connection, client_address = sock.accept()

        try:
            #receiveing information from client. 
            header = connection.recv(32)

            room_name_length = int.from_bytes(header[:1], "big")
            operation = int.from_bytes(header[1:2], "big")
            state = int.from_bytes(header[2:3], "big")
            data_length = int.from_bytes(header[3:], "big")

            print('operation: {}'.format(operation))
            print('state: {}'.format(state))

            room_name_bits = connection.recv(room_name_length)
            room_name = room_name_bits.decode('utf-8')
            print('room name: {}'.format(room_name))

            arr_user_name_bits = []
            while data_length>0:
                    data = connection.recv(data_length if data_length <= STREAM_RATE else STREAM_RATE)
                    arr_user_name_bits.append(data)
                    data_length -= STREAM_RATE

            user_name_bits = b''.join(arr_user_name_bits)
            user_name = user_name_bits.decode('utf-8')
            print('user name : {}'.format(user_name))
                    
            print('finished receiving information from client.')
            
            #create room
            if(operation==1):
                print('create room')
                #state1
                if(room_name in rooms):
                    print('error: room already exists')
                    operation = 1
                    state = 1
                    error_msg_bits = 'room is already exists'.encode('utf-8')
                    connection.sendall(
                                        protocol_header(len(room_name_bits), operation, state, len(error_msg_bits)) 
                                    + room_name_bits
                                    + error_msg_bits)
                    connection.close()
                    continue
                
                #state1 
                #response
                print('resonse-create room')
                operation = 1
                state = 1
                ok_bits = MESSAGE_OK.encode('utf-8')
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, state, len(ok_bits)) 
                    + room_name_bits 
                    + ok_bits
                )
                
                #state2
                #add new room and send token
                token = os.urandom(8).hex()
                rooms[room_name] = {
                    "host_token":token,
                    "token_list":{
                        token:{
                            "ip_address":client_address,
                            "user_name":user_name,
                            "last_seen": time.time(),
                            "failure":0
                        }
                    }
                }
                print('send token')
                operation = 1
                state = 2
                token_bits = token.encode('utf-8')
                print(token_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, state, len(token_bits)) 
                    + room_name_bits 
                    + token_bits
                )
            
            #join room
            if(operation==2):
                print('join room')
                #state1
                if not(room_name in rooms):
                    print("error: room doesn't exit")
                    operation = 2
                    state = 1
                    error_msg_bits = "room doesn't exit".encode('utf-8')
                    connection.sendall(
                                        protocol_header(len(room_name_bits), operation, state, len(error_msg_bits)) 
                                    + room_name_bits
                                    + error_msg_bits)
                    connection.close()
                    continue

                #state1
                #response
                print('resonse-join room')
                operation = 2
                state = 1
                ok_bits = MESSAGE_OK.encode('utf-8')
                print(ok_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, state, len(ok_bits)) 
                    + room_name_bits 
                    + ok_bits
                )
                
                #state2
                #send token
                token = os.urandom(8).hex()
                rooms[room_name]["tokenlist"][token]= {
                            "ip_address":client_address,
                            "user_name":user_name,
                            "last_seen": time.time(),
                            "failure":0
                        }

                print('send token')
                operation = 2
                state = 2
                token_bits = token.encode('utf-8')
                print(token_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, state, len(token_bits)) 
                    + room_name_bits 
                    + token_bits
                )

        except Exception as e:
            print('Error: ' + str(e))

        finally:
            print('closing curret connection')
            connection.close()