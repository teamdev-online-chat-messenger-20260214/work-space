import socket
import os
import time
import threading

SERVER_ADDRESS = "0.0.0.0" #変更可能 テスト用のlocalhost 本番時"0.0.0.0"
TCP_PORT = 9001 #TCPとUDPのPORTは定数化
UDP_PORT = 9002
STREAM_RATE = 4096
MESSAGE_OK = "OK"

#STATEを定数化
STATE_REQUEST = 0
STATE_RESPONSE = 1
STATE_COMPLETE = 2

FAILURE_LIMIT = 3
TIMEOUT_SEC = 6000

#指定バイト数を必ず受信する関数
def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("connection closed while receiving")
        data += chunk
    return data

def create_state():
    return {
        "rooms": {},
        "token_user": {},
        "token_ip": {},
        "last_seen": {},
        "failures": {}
    }

state_lock = threading.Lock() #Lock追加

def build_header(room_size, operation, state, payload_size):
    return (
        room_size.to_bytes(1, "big") +
        operation.to_bytes(1, "big") +
        state.to_bytes(1, "big") +
        payload_size.to_bytes(29, "big")
    )


def parse_header(header):
    room_size = header[0]
    operation = header[1]
    state = header[2]
    payload_size = int.from_bytes(header[3:], "big")
    return room_size, operation, state, payload_size


#============
# TCP_control
#============

def tcp_room_manage(state):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("server starting...")
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#サーバー停止後のポート維持を中止
    server.bind((SERVER_ADDRESS, TCP_PORT))
    print("tcp bind ok")
    server.listen()
    print("tcp listening...")

    while True:
        connection, address = server.accept()
        threading.Thread(target=handle_tcp, args=(connection, state), daemon=True).start()


def handle_tcp(connection, state):
    try:
        header = recv_exact(connection, 32)
        room_size, operation, state_code, payload_size = parse_header(header)

        body = recv_exact(connection, room_size + payload_size)

        room_name = body[:room_size].decode("utf-8", errors="replace")
        payload = body[room_size:]

        # ===== state 0: 初期化 =====
        if state_code != STATE_REQUEST:
            return

        user_name_bytes = payload[:-2]
        user_name = user_name_bytes.decode("utf-8", errors="replace")

        token = os.urandom(8).hex()

        with state_lock:
            # ===== operation 1: create =====
            if operation == 1:

                # 既存ルームチェック
                if room_name in state["rooms"]:
                    error_payload = b"ROOM_EXISTS"
                    header_err = build_header(
                        len(room_name.encode()),
                        operation,
                        STATE_RESPONSE,
                        len(error_payload)
                    )
                    connection.sendall(header_err + room_name.encode() + error_payload)
                    return

                state["rooms"][room_name] = {
                    "host_token": token,
                    "members": {token}
                }
            # ===== operation 2: join =====
            elif operation == 2:

                #存在しない部屋を確認
                if room_name not in state["rooms"]:
                    error_payload = b"NO_ROOM"
                    header_err = build_header(len(room_name.encode()), operation, STATE_RESPONSE, len(error_payload))
                    connection.sendall(header_err + room_name.encode() + error_payload)
                    return

                state["rooms"][room_name]["members"].add(token)

            else:
                return

            # 共通登録
            state["token_user"][token] = user_name
            state["token_ip"][token] = None
            state["last_seen"][token] = time.monotonic()
            state["failures"][token] = 0

        # OK 応答
        status_payload = b"OK"
        header1 = build_header(len(room_name.encode()), operation, STATE_RESPONSE, len(status_payload))
        connection.sendall(header1 + room_name.encode() + status_payload)

        # TOKEN送信
        token_bytes = token.encode()
        header2 = build_header(len(room_name.encode()), operation, STATE_COMPLETE,len(token_bytes))
        connection.sendall(header2 + room_name.encode() + token_bytes)

    except Exception as e:
        print("TCP ERROR:", e)

    finally:
        connection.close()

#退出処理
def kick_token(state, sock, token, reason):
    with state_lock:

        address = state.get("token_ip", {}).get(token)

        if address:
            sock.sendto(f"DISCONNECTED: {reason}".encode("utf-8"), address)

        closed_rooms = []

        for room_name, room in list(state["rooms"].items()):  # ★ list必須
            room["members"].discard(token)
            #ホスト削除
            if room.get("host_token") == token:
                closed_rooms.append(room_name)
            #ルーム削除、全員に通知
        for room_name in closed_rooms:
            room = state["rooms"].get(room_name)
            if not room:
                continue

            for member_token in room["members"]:
                address = state["token_ip"].get(member_token)
                if address:
                    sock.sendto(f"ROOM_CLOSED: {room_name}". encode(), address)

            del state["rooms"][room_name]

        state["token_user"].pop(token, None)
        state["last_seen"].pop(token, None)
        state["token_ip"].pop(token, None)
        state["failures"].pop(token, None)


def cleanup_timeouts(state: dict, sock: socket.socket):
    while True:
        now = time.monotonic()
        with state_lock:
            for token, last in list(state["last_seen"].items()):
                if now - last > TIMEOUT_SEC:
                    print(f"timeout: {token}")
                    kick_token(state, sock, token, "timeout")
        time.sleep(5)


def notify_server_shutdown(state, sock):
    with state_lock:
        for  address in state["token_ip"].values():
            if address:
                sock.sendto("SERVER_SHUTDOWN".encode(),address)

#============
# UDP_control
#============
def start_udp(state, sock):
    while True:
        try:
            data, address = sock.recvfrom(STREAM_RATE)
        except socket.timeout:
            continue

        parsed = parse_from_client(data)
        if parsed is None:
            continue

        room_name, token, message = parsed

        with state_lock:  # Lock追加
            if token not in state["token_user"]:
                continue

            state["last_seen"][token] = time.monotonic()

            failures = state["failures"]
            token_ip = state["token_ip"]
            saved = token_ip.get(token)

            if saved is None:
                if message != "@join":
                    failures[token] += 1
                    if failures[token] >= FAILURE_LIMIT:
                        kick_token(state, sock, token, "failure")
                    continue

                token_ip[token] = address
                failures[token] = 0

            else:
                if saved[0] != address[0]:
                    failures[token] += 1
                    if failures[token] >= FAILURE_LIMIT:
                        kick_token(state, sock, token, "failure")
                    continue

                failures[token] = 0
                token_ip[token] = address

            room = state["rooms"].get(room_name)
            if room is None:
                continue
            #生存確認
            state["last_seen"][token] = time.monotonic()

            if message == "@join":
                room["members"].add(token)
                continue

            members = room["members"]

            if token not in members:
                continue

            sender = state["token_user"].get(token, token)
            out = message.encode("utf-8")

            name_bytes = sender.encode("utf-8")
            packet = bytes([len(name_bytes)]) + name_bytes + out

            for t in members:
                if t == token:
                    continue
                addr = state["token_ip"].get(t)
                if addr:
                    sock.sendto(packet, addr)

#ユーザーから受け取ったデータをパースする
def parse_from_client(data: bytes):
    if not data or len(data) < 2:
        return None
    
    room_len = data[0]
    token_len = data[1]
    msg = 2

    if len(data) < 2 + room_len + token_len:
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

# ============================
# main
# ============================
def main():
    state = create_state()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # ★ 修正: mainで作成
    udp_sock.bind((SERVER_ADDRESS, UDP_PORT))
    udp_sock.settimeout(1.0)

    threading.Thread(target=tcp_room_manage, args=(state,), daemon=True).start()
    threading.Thread(target=start_udp, args=(state, udp_sock), daemon=True).start()
    threading.Thread(target=cleanup_timeouts,args=(state, udp_sock),daemon=True).start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
            print("\nServer shutting down...")

            notify_server_shutdown(state, udp_sock)  #全員通知
            time.sleep(1)
            udp_sock.close()

if __name__ == "__main__":
    main()