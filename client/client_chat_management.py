import socket
import threading

def start_chat(token: str, room_name: str, udp_server_ip: int, udp_port: str):
   
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    address = ''
    port = 0
    sock.bind((address, port))

    username = input("username> ").strip()

    threading.Thread(target=receive_loop, args=(sock,), daemon=True).start()
    join_packet = build_packet(token, room_name)
    sock.sendto(join_packet, (udp_server_ip, udp_port))

    try:
        while True:
            text = input(">")
            if text.strip() == "/quit":
                break
            packet = build_packet(username, text)
            sock.sendto(packet, (udp_server_ip, udp_port))
    finally:
        sock.close()


def receive_loop(sock):
   while True:
      data, _ = sock.recvfrom(4096)
      parsed = parse_packet(data)
      if parsed:
         u, m = parsed

def parse_packet(data: bytes):
   if not data:
       return None
   
   n = data[0]
   if 1 + n > len(data):
      return None
   u = data[1:1+n].decode("utf-8", errors="replace")
   m = data[1+n:].decode("utf-8", errors="replace")

   return u,m


def build_packet(token: str, room_name: str, text:str):
   
   room_en = room_name.encode("utf-8")
   token_en = token.encode("utf-8")
   msg = text.encode("utf-8")
   
   if len(room_en) > 255:
      raise ValueError("token too long")
   if len(token_en) > 255:
      raise ValueError("token too long")
    
   packet = bytes([len(room_en)]) + bytes([len(token_en)]) + room_en + token_en + msg

   if len(packet) > 4096:
      raise ValueError("packet too long")
   
   return packet
        