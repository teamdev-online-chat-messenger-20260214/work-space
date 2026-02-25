# develop-chat-udp
def main():
    rooms = {}
    state = {
        #部屋名:{"host_token":"ホストトークン", "members":{"トークン", "トークン"}}
        "rooms" : rooms,

        # トークン：ユーザー名
        "token_user" : {

        },

        # トークン：（ip:port）
        "token_ip" : {

        },

        #トークン：最終時間
        "last_seen" :{
   
        },

        "failures":{

        }

    }



#import threading

#rooms = {}

"""
rooms = {room1:{"host_token":token11,
                "token_list":{token11:{"ip_address":ipaddress11, 
                                    "user_name":username11, 
                                    "last_seen":last_login11, 
                                    "failure":1}, 
                              token12:{"ipaddress":ipaddress12, 
                                    "username":username12, 
                                    "last_seen":last_login12, 
                                    "failure":2}, 
               },
         room2:{}
        }
"""


#threading.Thread(target=server_room_management.tcp_room_manage(rooms), daemon=True).start()

import socket
import os
import time
import threading
#from pathlib import Path


SERVER_ADDRESS = "127.0.0.1" #変更可能 テスト用のlocalhost 本番時"0.0.0.0"
TCP_PORT = 9001 #TCPとUDPのPORTは定数化
UDP_PORT = 9001
STREAM_RATE = 4096
MESSAGE_OK = "OK"

#STATEを定数化
STATE_REQUEST = 0
STATE_RESPONSE = 1
STATE_COMPLETE = 2


TIMEOUT_SEC = 60
SOCKET_TICK = 20

#============
# TCP_control
#============
def protocol_header(room_name_length, operation, state, data_length):
    return (room_name_length.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1, "big") + data_length.to_bytes(29, "big"))

def tcp_room_manage(rooms):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('Starting up on {} port {}'.format(SERVER_ADDRESS, TCP_PORT))

    sock.bind((SERVER_ADDRESS, TCP_PORT))
    sock.listen(1)

    while True:
        connection, client_address = sock.accept()

        try:
            #receiving information from client.
            header = connection.recv(32)

            room_name_length = int.from_bytes(header[:1], "big")
            operation = int.from_bytes(header[1:2], "big")
            state = int.from_bytes(header[2:3], "big")
            data_length = int.from_bytes(header[3:], "big")

            room_name_bits = connection.recv(room_name_length)
            room_name = room_name_bits.decode("utf-8")
            print('room name: {}'.format(room_name))

             # payload = [username][udp_port]
             #data_lengthからはlen(data)を引くに変更
            arr_user_name_bits = []
            while data_length>0:
                    data = connection.recv(data_length if data_length <= STREAM_RATE else STREAM_RATE)
                    arr_user_name_bits.append(data)
                    data_length -= len(data)
            #####
            #user_name_bits = b''.join(arr_user_name_bits)
            #user_name = user_name_bits.decode('utf-8')
            #print('user name : {}'.format(user_name))
            #######

            #UDP_Portをpayloadに入れた都合で変えてます。
            user_and_port = b''.join(arr_user_name_bits)
            if len(user_and_port) < 2:
                raise Exception("payload is too small")

            user_name_bits = user_and_port[:-2]   # 最後の2バイト以外
            udp_port_bytes = user_and_port[-2:]  # 最後の2バイト

            user_name = user_name_bits.decode('utf-8')
            udp_port = int.from_bytes(udp_port_bytes, "big")

            print('user name : {}'.format(user_name))
            print('udp port : {}'.format(udp_port))

            print('finished receiving information from client.')
            
            #create room
            if operation== 1:
                print('create room')
                #state1
                if room_name in rooms:
                    print('error: room already exists')
                    #operation = 1
                    #Stateは定数化
                    #state = 1
                    error_msg_bits = 'room is already exists'.encode('utf-8')
                    connection.sendall(
                                        protocol_header(len(room_name_bits), operation, STATE_RESPONSE, len(error_msg_bits)) 
                                    + room_name_bits
                                    + error_msg_bits)
                    continue
                
                #state1 
                #response
                print('response-create room')
                #operation = 1
                #Stateは定数化
                #state = 1
                ok_bits = MESSAGE_OK.encode('utf-8')
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, STATE_RESPONSE, len(ok_bits)) 
                    + room_name_bits 
                    + ok_bits
                )
                
                #state2
                #add new room and send token
                token = os.urandom(8).hex()

                rooms[room_name] = {
                    "host_token": token,
                    "token_list": {}
                }

                # token登録
                rooms[room_name]["token_list"][token] = {
                    "ip_address": client_address,
                    "user_name": user_name,
                    "last_seen": time.time(),
                    "failure": 0
                }

                """
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
                """
                print('send token')
                #operation = 1
                #Stateは定数化
                #state = 2
                token_bits = token.encode('utf-8')
                print(token_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, STATE_COMPLETE, len(token_bits)) 
                    + room_name_bits 
                    + token_bits
                )
            
            #join room
            if(operation==2):
                print('join room')
                #state1
                if room_name not in rooms:
                    print("error: room doesn't exit")
                    #operation = 2
                    #state = 1
                    error_msg_bits = "room doesn't exit".encode('utf-8')
                    connection.sendall(
                                        protocol_header(len(room_name_bits), operation, STATE_RESPONSE, len(error_msg_bits)) 
                                    + room_name_bits
                                    + error_msg_bits)
                    connection.close()
                    continue

                #state1
                #response
                print('response-join room')
                #operation = 2
                #state = 1
                ok_bits = MESSAGE_OK.encode('utf-8')
                print(ok_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, STATE_RESPONSE, len(ok_bits)) 
                    + room_name_bits 
                    + ok_bits
                )
                
                #state2
                #send token
                token = os.urandom(8).hex()
                rooms[room_name]["token_list"][token]= {
                            "ip_address":client_address,
                            "user_name":user_name,
                            "last_seen": time.time(),
                            "failure":0
                        }

                print('send token')
                #operation = 2
                #state = 2
                token_bits = token.encode('utf-8')
                print(token_bits)
                connection.sendall(
                    protocol_header(len(room_name_bits), operation, STATE_COMPLETE, len(token_bits)) 
                    + room_name_bits 
                    + token_bits
                )

        except Exception as e:
            print('Error: ' + str(e))

        finally:
            print('closing current connection')
            connection.close()

#============
# UDP_control
#============

#主の流れ
def start_udp(state: dict):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    #server_address = '127.0.0.1'
    #server_port = 9001

    sock.bind((SERVER_ADDRESS, UDP_PORT))
    sock.settimeout(SOCKET_TICK)

    while True:
        print('\nwaiting to receive message')

        try:
            data, address = sock.recvfrom(4096)
            
        except socket.timeout:
            cleanup_timeouts(state)
            continue
            
        parsed = parse_from_client(data)
        if parsed is None:
            continue

        room_name, token, message = parsed
        state.setdefault("last_seen", {})[token] = time.monotonic()

        if not check_room_host(state, room_name):
            continue



#ユーザーから受け取ったデータをパースする
def parse_from_client(data: bytes):
    if not data or len(data) < 2:
        return None
    
    room_len = data[0]
    token_len = data[1]
    msg = 2

    if room_len + token_len + msg > len(data):
        return None

    room_name = data[msg: msg + room_len].decode("utf-8", errors="replace")
    token = data[msg + room_len: msg + room_len + token_len].decode("utf-8", errors="replace")
    message = data[msg + room_len + token_len:].decode("utf-8", errors="replace")

    return room_name, token, message

#ホストがルームに存在するか確認
def check_room_host(state: dict, room_name: str) -> bool:

    rooms = state.get("rooms", {})
    room = rooms.get(room_name)

    if room is None:
        return False
    
    host = room.get("host_token")
    members = room.get("members", set())

    return host is not None and host in members

#mainのlast_seenからタイムアウトになったユーザー削除・ユーザーがホストの場合ルームを閉じる
def cleanup_timeouts(state: dict) -> None:

    now = time.time()
    rooms = state.get("rooms", {})

    for room_name, room in rooms.items():
        tokens = room.get("token_list", {})

        expired = []

        # タイムアウト判定
        for token, info in tokens.items():
            last = info.get("last_seen", 0)

            if now - last > TIMEOUT_SEC:
                expired.append(token)

        # 期限切れ削除
        for token in expired:
            tokens.pop(token, None)

    # state.last_seen（UDP受信側）も掃除
    last_seen = state.get("last_seen", {})
    expired_global = []

    for token, t in last_seen.items():
        if now - t > TIMEOUT_SEC:
            expired_global.append(token)

    for token in expired_global:
        last_seen.pop(token, None)

# ============================
# main
# ============================
def main():
    rooms = {}
    state = {"rooms": rooms}

    threading.Thread(target=tcp_room_manage, args=(rooms,), daemon=True).start()
    threading.Thread(target=start_udp, args=(state,), daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()


