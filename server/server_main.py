import server_room_management,server_chat_management

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

    "token_user" : {
        "t1" : "user1",
        "t2" : "user2",
        "t3" : "user3",
        "t4" : "user4"
    },

    "token_ip" : {
        "t1" : "127.0.0.1",
        "t2" : "127.0.0.1",
        "t3" : "127.0.0.1",
        "t4" : "127.0.0.1"
    },

    "last_seen" :{
        "t1": 0.0,
        "t2": 0.0,
        "t3": 0.0,
        "t4": 0.0,
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
