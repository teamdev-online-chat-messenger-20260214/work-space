
import socket
import threading
import sys
import os


SERVER_ADDRESS = "127.0.0.1" #変更可能 テスト用のlocalhost
TCP_PORT = 9001 #TCPとUDPのPORTは定数化
UDP_PORT = 9001
STREAM_RATE = 4096
MESSAGE_OK = "OK"

#クライアントUDP_PORTを作成。
CLIENT_UDP_PORT = 10000 + (os.getpid() % 1000)
#STATEを定数化
STATE_REQUEST = 0
STATE_RESPONSE = 1
STATE_COMPLETE = 2

#develop-chat-udp
#token = client_room_management.tcp_room_manage()

#============
# TCP_control
#============
def protocol_header(room_name_length, operation, state, data_length):
    return room_name_length.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + state.to_bytes(1, 'big') + data_length.to_bytes(29,"big")

def tcp_room_manage():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('connecting to {}'.format(SERVER_ADDRESS, TCP_PORT))

    try:
        sock.connect((SERVER_ADDRESS, TCP_PORT))
    except socket.error as err:
        print(err)
        sys.exit(1)

    try:
        #input
        operation_str = input('type 1:create room, 2:join room >')
        if operation_str != '1' and operation_str != '2':
            raise Exception('invalid input.')
        operation = int(operation_str)
        room_name = input('type room name: ')
        user_name = input('type user name: ')
        room_name_bits = room_name.encode('utf_8')
        user_name_bits = user_name.encode('utf_8')
        #UDPポート番号を追加。payloadにusernameと合わせてprotocol_headerの最後の引数に代入しています。
        udp_port_bytes = CLIENT_UDP_PORT.to_bytes(2, "big")
        payload = user_name_bits + udp_port_bytes
        #上記にstateを定数化して可読性を高めました。下記のprotocol_headerに直接書き込んでいます。
        #state = 0

        if len(room_name_bits) > pow(2, 8):
            raise Exception('room name is too long.')
        
        if len(payload) > pow(2, 29):
            raise Exception('user name is too long.')
        
        header = protocol_header(len(room_name_bits), operation, STATE_REQUEST, len(payload))

        sock.send(header)
        sock.send(room_name_bits)
        data = payload
        data_length = len(payload)
        while data_length>0:
            print('sending...')
            sock.send(data)
            data_length -= STREAM_RATE

        sock.settimeout(2)

        #response
        try:
            while True:
                header = sock.recv(32)
                room_name_length = int.from_bytes(header[:1], "big")
                operation = int.from_bytes(header[1:2], "big")
                state = int.from_bytes(header[2:3], "big")
                data_length = int.from_bytes(header[3:], "big")
                print('response-operation: {}'.format(operation))
                print('response-state: {}'.format(state))

                room_name_bits = sock.recv(room_name_length)
                room_name = room_name_bits.decode('utf-8')
                print('response-room name: {}'.format(room_name))
                print('response-data length: {}'.format(data_length))

                arr_data_bits = []
                while data_length>0:
                    response_data_bits = sock.recv(data_length if data_length <= STREAM_RATE else STREAM_RATE)
                    arr_data_bits.append(response_data_bits)
                    #-STREAM_RATEから変更
                    data_length -=  len(response_data_bits)

                data = b''.join(arr_data_bits).decode('utf-8')
                #data = data_bits.decode('utf-8')
                print('response-data: {}'.format(data))

                if(data != MESSAGE_OK):
                    print('response-error')
                    break
                #print(data)
                break
        except(TimeoutError):
            print('socket timeout')

        sock.settimeout(2)

        #receive token
        try:
            while True:
                header = sock.recv(32)
                room_name_length = int.from_bytes(header[:1], "big")
                operation = int.from_bytes(header[1:2], "big")
                state = int.from_bytes(header[2:3], "big")
                data_length = int.from_bytes(header[3:], "big")
                print('token-operation: {}'.format(operation))
                print('token-state: {}'.format(state))

                room_name_bits = sock.recv(room_name_length)
                room_name = room_name_bits.decode('utf-8')
                print('token-room name: {}'.format(room_name))
                print('token-data length: {}'.format(data_length))

                arr_data_bits = []
                while data_length>0:
                    response_data_bits = sock.recv(data_length if data_length <= STREAM_RATE else STREAM_RATE)
                    arr_data_bits.append(response_data_bits)
                    data_length -= len(response_data_bits)

                data = b''.join(arr_data_bits).decode('utf-8')
                #data = data_bits.decode('utf-8')
                print('token-data: {}'.format(data))
                
                print(data)
                return data

        except(TimeoutError):
            print('socket timeout')
    finally:
        print('closing socket')
        sock.close()



#============
# UDP_control
#============
              #変更前 token: str, room_name: str, udp_server_ip: int, udp_port: str
def start_chat(token, room_name):
   
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #address = ''
    #port = 0
    #ポート番号は定数を使用
    sock.bind(('', CLIENT_UDP_PORT ))

    #TCPの方で定義済み
    #username = input("username> ").strip()

    threading.Thread(target=receive_loop, args=(sock,), daemon=True).start()
    join_packet = build_packet(token, room_name, "")
    sock.sendto(join_packet, (SERVER_ADDRESS, UDP_PORT))

    try:
        while True:
            text = input(">")
            if text.strip() == "/quit":
                break
            packet = build_packet(token, room_name, text)
            sock.sendto(packet, (SERVER_ADDRESS, UDP_PORT))
    finally:
        sock.close()


def receive_loop(sock):
   while True:
      data, _ = sock.recvfrom(4096)
      #perse_packet関数と合併。
      if not data:
            continue
      n = data[0]
      if 1 + n > len(data):
        continue

      user = data[1:1+n].decode("utf-8", errors="replace")
      msg = data[1+n:].decode("utf-8", errors="replace")

      print(f"{user}: {msg}")
      
      #parsed = parse_packet(data)
      #if parsed:
      #u, m = parsed

'''
def parse_packet(data: bytes):
   if not data:
       return None
   
   n = data[0]
   if 1 + n > len(data):
      return None
   u = data[1:1+n].decode("utf-8", errors="replace")
   m = data[1+n:].decode("utf-8", errors="replace")

   return u,m
'''

def build_packet(token, room_name, text):
   
   room_en = room_name.encode("utf-8")
   token_en = token.encode("utf-8")
   msg = text.encode("utf-8")
   
   #1byte制限があるため不要
   #if len(room_en) > 255:
      #raise ValueError("token too long")
   #if len(token_en) > 255:
      #raise ValueError("token too long")
    
   packet = (bytes([len(room_en)]) + bytes([len(token_en)]) + room_en + token_en + msg)

   if len(packet) > 4096:
      raise ValueError("packet too long")
   
   return packet

#============ 
# MAIN 
#============  
def main():
    token, room_name = tcp_room_manage()
    if token is None:
        print("failed")
        return

    print("joined room")
    start_chat(token, room_name)

if __name__ == "__main__":
    main()

