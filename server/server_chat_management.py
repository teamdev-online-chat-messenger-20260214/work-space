import socket

import time

TIMEOUT_SEC = 60
SOCKET_TICK = 20

#主の流れ
def start_udp(state: dict):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    server_address = '127.0.0.1'
    server_port = 9001

    sock.bind((server_address, server_port))
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
def cleanup_timeouts(state: dict)-> None:
    now = time.monotonic()
    last_seen = state.get("last_seen", {})
    rooms = state.get("rooms", {})

    #期限切れメンバーを探す
    expired_token= []
    for token, t in last_seen.items():
        if now - t > TIMEOUT_SEC:
            expired_token.append(token)
    
    if not expired_token:
        return
    
    #各ルームから期限切れメンバー削除
    for room in rooms.values():
        members = room.get("members", set())
        for token in expired_token:
            members.discard(token)
    
    #last_seen,token_ip,token_userからも削除する
    for token in expired_token:
        last_seen.pop(token, None)
        state.get("token_ip", {}).pop(token, None)
        state.get("token_user", {}).pop(token, None)

    #ホストが存在しないルームをリストに追加
    closed_room = []
    for room_name, room in rooms.items():
        host = room.get("host_token")
        if host is None:
            closed_room.append(room_name)
            continue

        host_last = last_seen.get(host, 0.0)
        if now - host_last > TIMEOUT_SEC:
            closed_room.append(room_name)
    
    for room_name in closed_room:
        rooms.pop(room_name, None)

