

from server_chat_management import start_udp

def main():
    state = {
        "rooms" : {
            "roomA" : {
                "host_token":"t1",
                "members":{"t1", "t2"},
                },
            "roomB" : {
                "host_token":"t3",
                "members": {"t3", "t4"}}
        },

        # トークン：ユーザー名
        "token_user" : {

        },

        # トークン：（ip:port）
        "token_ip" : {

        },

        #トークン：最終じ時間
        "last_seen" :{
   
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

