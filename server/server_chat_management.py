import socket

import time

TIMEOUT_SEC = 60
SOCKET_TICK = 20
FAILURE_LIMIT = 3          
CLEANUP_INTERVAL_SEC = 5  


#主の流れ
def start_udp(state: dict):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    server_address = '127.0.0.1'
    server_port = 9001

    sock.bind((server_address, server_port))
    sock.settimeout(1.0)
    state.setdefault("failures", {})
    last_cleanup = time.monotonic()


    while True:
        #print('\nwaiting to receive message')

        now = time.monotonic()
        if now - last_cleanup >= CLEANUP_INTERVAL_SEC:
            cleanup_timeouts(state, sock)
            last_cleanup = now

        try:
            data, address = sock.recvfrom(4096)
            
        except socket.timeout:
            continue
            
        parsed = parse_from_client(data)
        if parsed is None:
            continue

        room_name, token, message = parsed        
        state.setdefault("last_seen", {})[token] = time.monotonic()
        
        
        failures = state.setdefault("failures", {})
        token_ip = state.setdefault("token_ip", {})   
        saved = token_ip.get(token)

        if saved is None:
            if message != "@join":
                failures[token] = failures.get(token, 0) + 1
                if failures[token] >= FAILURE_LIMIT:
                    kick_token(state, sock, token, "failure")
                continue
            token_ip[token] = address
            failures[token] = 0
        else:
        # IP不一致は失敗（要件）→ 必ずここで終わる
            if saved[0] != address[0]:
                failures[token] = failures.get(token, 0) + 1
                if failures[token] >= FAILURE_LIMIT:
                    kick_token(state, sock, token, "failure")
                continue

            # IP一致なら成功：失敗回数リセット＆最新port更新
            failures[token] = 0
            token_ip[token] = address


        rooms = state.get("rooms", {})
        room = rooms.get(room_name)
        if room is None:
            continue

        if message == "@join":
            room.setdefault("members",set()).add(token)
            state.setdefault("token_ip", {})[token] = address
            state.setdefault("failures", {})[token] = 0
            continue

        if not check_room_host(state, room_name):
            continue

        members = room.get("members", set())

        #サーバー→クライアントへ
        sender = state.get("token_user", {}).get(token, token)
        out = f"{sender}: {message}".encode("utf-8")

        for t in members:
            if t == token:
                continue
            addr = state.get("token_ip", {}).get(t) 
            if addr:
                sock.sendto(out, addr)



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
def cleanup_timeouts(state: dict, sock: socket.socket) -> None:
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
        kick_token(state, sock, token, "timeout")
        last_seen.pop(token, None)
        state.get("token_ip", {}).pop(token, None)
        #state.get("token_user", {}).pop(token, None)
        state.get("failures", {}).pop(token, None) 

    #ホストが存在しないルームをリストに追加
    closed_room = []
    for room_name, room in rooms.items():
        host = room.get("host_token")
        members = room.get("members", set())
        if host is None or host not in members:
            closed_room.append(room_name)

    for room_name in closed_room:
        rooms.pop(room_name, None)

def kick_token(state: dict, sock: socket.socket, token: str, reason: str):
    addr = state.get("token_ip", {}).get(token)
    if addr:
        sock.sendto(f"DISCONNECTED: {reason}".encode("utf-8"), addr)

    for room in state.get("rooms", {}).values():
        room.get("members", set()).discard(token)

    state.get("last_seen", {}).pop(token, None)
    state.get("token_ip", {}).pop(token, None)
    state.get("failures", {}).pop(token, None)



