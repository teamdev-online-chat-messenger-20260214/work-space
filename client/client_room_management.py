import socket
import sys
import os

SERVER_ADDRESS = "0.0.0.0"
SERVER_PORT = 9001
STREAM_RATE = 4096
MESSAGE_OK = "OK"

def protocol_header(room_name_length, operation, state, data_length):
    return room_name_length.to_bytes(1, 'big') + operation.to_bytes(1, 'big') + state.to_bytes(1, 'big') + data_length.to_bytes(29,"big")

def tcp_room_manage():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('connecting to {}'.format(SERVER_ADDRESS, SERVER_PORT))

    try:
        sock.connect((SERVER_ADDRESS, SERVER_PORT))
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
        state = 0

        if len(room_name_bits) > pow(2, 8):
            raise Exception('room name is too long.')
        
        if len(user_name_bits) > pow(2, 29):
            raise Exception('user name is too long.')
        
        header = protocol_header(len(room_name_bits), operation, state, len(user_name_bits))

        sock.send(header)
        sock.send(room_name_bits)
        data = user_name_bits
        data_length = len(user_name_bits)
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
                    data_length -= STREAM_RATE

                data_bits = b''.join(arr_data_bits)
                data = data_bits.decode('utf-8')
                print('response-data: {}'.format(data))

                if(data != MESSAGE_OK):
                    print('response-error')
                    break
                
                print(data)
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
                    data_length -= STREAM_RATE

                data_bits = b''.join(arr_data_bits)
                data = data_bits.decode('utf-8')
                print('token-data: {}'.format(data))
                
                print(data)
                return data

        except(TimeoutError):
            print('socket timeout')
    finally:
        print('closing socket')
        sock.close()
