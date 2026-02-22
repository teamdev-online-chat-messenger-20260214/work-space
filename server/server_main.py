import server_room_management,server_chat_management
import threading

rooms = {}

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


threading.Thread(target=server_room_management.tcp_room_manage(rooms), daemon=True).start()

