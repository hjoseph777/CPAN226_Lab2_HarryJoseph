# This program was modified by [Harry Joseph] / [N00881767 ID]

import socket
import argparse
import os
import struct

TYPE_DATA = b'D'
TYPE_ACK = b'A'
TYPE_EOF = b'E'

HEADER_FORMAT = '!cI'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

CHUNK_SIZE = 4000
ACK_TIMEOUT_SECONDS = 0.03
MAX_RETRIES = 1000


def make_packet(packet_type, sequence_number, payload=b''):
    return struct.pack(HEADER_FORMAT, packet_type, sequence_number) + payload


def parse_ack(packet):
    if len(packet) < HEADER_SIZE:
        return None, None
    packet_type, sequence_number = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
    return packet_type, sequence_number


def send_with_retransmit(sock, server_address, packet, expected_ack_seq):
    attempts = 0
    while attempts < MAX_RETRIES:
        attempts += 1
        sock.sendto(packet, server_address)
        try:
            response, _ = sock.recvfrom(1024)
            packet_type, ack_sequence = parse_ack(response)
            if packet_type == TYPE_ACK and ack_sequence == expected_ack_seq:
                return True
        except socket.timeout:
            continue
    return False

def run_client(target_ip, target_port, input_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(ACK_TIMEOUT_SECONDS)
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port} using Stop-and-Wait RDT")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        sock.close()
        return

    try:
        sequence_number = 0

        with open(input_file, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                
                if not chunk:
                    break

                data_packet = make_packet(TYPE_DATA, sequence_number, chunk)
                packet_ok = send_with_retransmit(sock, server_address, data_packet, sequence_number)
                if not packet_ok:
                    print(f"[!] Failed to deliver packet seq={sequence_number} after retries.")
                    return

                sequence_number += 1

        eof_packet = make_packet(TYPE_EOF, sequence_number)
        eof_ok = send_with_retransmit(sock, server_address, eof_packet, sequence_number)
        if not eof_ok:
            print("[!] Failed to deliver EOF packet after retries.")
            return

        print("[*] File transmission complete.")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reliable UDP File Sender (Stop-and-Wait)")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)