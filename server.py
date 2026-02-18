# This program was modified by [Harry Joseph] / [N00881767 ID]

import socket
import argparse
import struct

TYPE_DATA = b'D'
TYPE_ACK = b'A'
TYPE_EOF = b'E'

HEADER_FORMAT = '!cI'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def parse_packet(packet):
    if len(packet) < HEADER_SIZE:
        return None, None, b''
    packet_type, sequence_number = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
    payload = packet[HEADER_SIZE:]
    return packet_type, sequence_number, payload


def make_ack(sequence_number):
    return struct.pack(HEADER_FORMAT, TYPE_ACK, sequence_number)

def run_server(port, output_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save received data to '{output_file}'.")
    sock.bind(server_address)

    try:
        while True:
            output_handle = None
            expected_seq_num = 0
            reorder_buffer = {}
            active_sender = None

            while True:
                data, addr = sock.recvfrom(4096)

                packet_type, seq_num, payload = parse_packet(data)
                if packet_type is None:
                    continue

                if active_sender is None and packet_type in (TYPE_DATA, TYPE_EOF):
                    active_sender = addr
                    print("==== Start of reception ====")
                    output_handle = open(output_file, 'wb')
                    print(f"[*] First packet received from {addr}. File opened for writing as '{output_file}'.")

                if addr != active_sender:
                    continue

                if packet_type == TYPE_DATA:
                    if seq_num == expected_seq_num:
                        output_handle.write(payload)
                        expected_seq_num += 1

                        while expected_seq_num in reorder_buffer:
                            output_handle.write(reorder_buffer.pop(expected_seq_num))
                            expected_seq_num += 1

                        sock.sendto(make_ack(seq_num), addr)
                    elif seq_num > expected_seq_num:
                        if seq_num not in reorder_buffer:
                            reorder_buffer[seq_num] = payload
                        ack_seq = expected_seq_num - 1
                        if ack_seq >= 0:
                            sock.sendto(make_ack(ack_seq), addr)
                    else:
                        sock.sendto(make_ack(seq_num), addr)

                elif packet_type == TYPE_EOF:
                    if seq_num == expected_seq_num:
                        sock.sendto(make_ack(seq_num), addr)
                        print(f"[*] End of file signal received from {addr}. Closing.")
                        break
                    else:
                        ack_seq = expected_seq_num - 1
                        if ack_seq >= 0:
                            sock.sendto(make_ack(ack_seq), addr)

            if output_handle:
                output_handle.close()
            print("==== End of reception ====")
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()
        print("[*] Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Receiver with Reordering Buffer")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")