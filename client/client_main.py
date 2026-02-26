import socket
import threading
import sys
import os

SERVER_ADDRESS = "127.0.0.1"
TCP_PORT = 9001
UDP_PORT = 9002
MESSAGE_OK = "OK"

CLIENT_UDP_PORT = 10000 + (os.getpid() % 1000)

STATE_REQUEST = 0
STATE_RESPONSE = 1
STATE_COMPLETE = 2

#指定バイト数を必ず受信する関数
def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("connection closed while receiving")
        data += chunk
    return data


def protocol_header(room_name_length, operation, state, data_length):
    return (room_name_length.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + state.to_bytes(1, 'big') + data_length.to_bytes(29, "big"))


# ============
# TCP CONTROL
# ============
def tcp_room_manage():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('connecting to {}'.format(SERVER_ADDRESS, TCP_PORT))

    try:
        sock.connect((SERVER_ADDRESS, TCP_PORT))
    except socket.error as err:
        print(err)
        sys.exit(1)

    try:
        operation_str = input("1:create room  2:join room > ").strip()
        if operation_str not in ("1", "2"):
            print("invalid input")
            return None, None

        operation = int(operation_str)
        room_name = input("room name > ").strip()
        user_name = input("user name > ").strip()

        room_bytes = room_name.encode("utf-8")
        user_bytes = user_name.encode("utf-8")

        udp_port_bytes = CLIENT_UDP_PORT.to_bytes(2, "big")
        payload = user_bytes + udp_port_bytes

        header = protocol_header(len(room_bytes), operation, STATE_REQUEST, len(payload))

        sock.sendall(header)
        sock.sendall(room_bytes)
        sock.sendall(payload)

    
        #RESPONSE受信
        header = recv_exact(sock, 32)
        room_len = int.from_bytes(header[:1], "big")
        op_response = int.from_bytes(header[1:2], "big")
        state = int.from_bytes(header[2:3], "big")
        data_len = int.from_bytes(header[3:], "big")

        #operation一致確認
        if op_response != operation:
            print("invalid operation (response)")
            return None, None

        #state確認
        if state != STATE_RESPONSE:
            print("invalid state (expected RESPONSE)")
            return None, None

        room_name = recv_exact(sock, room_len).decode("utf-8")
        data = recv_exact(sock, data_len).decode("utf-8")

        if data != MESSAGE_OK:
            print("server error:", data)
            return None, None


        #TOKEN受信
        header = recv_exact(sock, 32)
        room_len = int.from_bytes(header[:1], "big")
        op_token = int.from_bytes(header[1:2], "big")
        state = int.from_bytes(header[2:3], "big")
        data_len = int.from_bytes(header[3:], "big")

        #operation一致確認
        if op_token != operation:
            print("invalid operation (token)")
            return None, None

        #COMPLETE確認
        if state != STATE_COMPLETE:
            print("invalid state (expected COMPLETE)")
            return None, None

        room_name = recv_exact(sock, room_len).decode("utf-8")
        token = recv_exact(sock, data_len).decode("utf-8")

        return token, room_name

    except (ConnectionError, socket.timeout) as e:
        print("connection error:", e)
        return None, None

    finally:
        sock.close()


# =============
# UDP CONTROL
# =============
def build_packet(token, room_name, text):
    room_en = room_name.encode("utf-8")
    token_en = token.encode("utf-8")
    msg = text.encode("utf-8")

    packet = (bytes([len(room_en)]) + bytes([len(token_en)]) + room_en + token_en + msg)

    if len(packet) > 4096:
        raise ValueError("packet too long")

    return packet

def receive_loop(sock, stop_event):
    my_name = None

    while not stop_event.is_set():
        try:
            data, _ = sock.recvfrom(4096)
        except OSError:
            break

        if not data:
            continue

        print(data)#デバックコード
        print(data.hex())#デバックコード

        # 通知
        if data.startswith(b"ROOM_CLOSED") or data.startswith(b"DISCONNECTED") or data.startswith(b"SERVER_SHUTDOWN"):
            print(data.decode("utf-8", errors="replace"))
            stop_event.set()
            break

        # UDPチャット解析
        if len(data) < 1:
            continue

        name_len = data[0]
        if len(data) < 1 + name_len:
            continue

        # user = 名前
        user = data[1:1+name_len].decode("utf-8", errors="replace")

        # msg = 残り
        msg = data[1+name_len:].decode("utf-8", errors="replace")

        # ★自分のメッセージは表示しない
        if my_name and user == my_name:
            continue

        print(f"{user}: {msg}")

def start_chat(token, room_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', CLIENT_UDP_PORT))

    stop_event = threading.Event()
    threading.Thread(target=receive_loop, args=(sock, stop_event), daemon=True).start()

    # ★JOINを必ず送る★
    join_packet = build_packet(token, room_name, "@join")
    sock.sendto(join_packet, (SERVER_ADDRESS, UDP_PORT))

    try:
        while not stop_event.is_set():
            text = input("> ")
            if text.strip() == "/quit":
                break

            packet = build_packet(token, room_name, text)
            sock.sendto(packet, (SERVER_ADDRESS, UDP_PORT))

    finally:
        stop_event.set()
        sock.close()
        print("chat ended")

# =============
# UDP CONTROL
# =============
def main():
    token, room_name = tcp_room_manage()

    if not token:
        print("failed")
        return

    print("joined:", room_name)
    start_chat(token, room_name)


if __name__ == "__main__":
    main()