import socket
import threading
import argparse

# --- Configuration ---
# These can be overridden by command-line arguments
DEFAULT_LOCAL_HOST = "0.0.0.0"  # Listen on all available interfaces
DEFAULT_LOCAL_PORT = 8080      # Port to listen on locally
DEFAULT_REMOTE_HOST = "147.194.66.13" # Target IP or hostname
DEFAULT_REMOTE_PORT = 8080      # Target port

BUFFER_SIZE = 4096 # Bytes to read/write at a time

def forward_data(source_socket, destination_socket, direction_name):
    """
    Reads data from source_socket and sends it to destination_socket.
    Closes both sockets if an error occurs or connection is closed.
    """
    try:
        while True:
            data = source_socket.recv(BUFFER_SIZE)
            if not data:  # Connection closed by the source
                print(f"[*] {direction_name}: Connection closed by source. Closing sockets.")
                break
            # print(f"[*] {direction_name}: Received {len(data)} bytes.")
            destination_socket.sendall(data)
            # print(f"[*] {direction_name}: Sent {len(data)} bytes.")
    except ConnectionResetError:
        print(f"[!] {direction_name}: Connection reset by peer.")
    except BrokenPipeError:
        print(f"[!] {direction_name}: Broken pipe (likely destination closed).")
    except socket.error as e:
        print(f"[!] {direction_name}: Socket error: {e}")
    finally:
        print(f"[*] {direction_name}: Closing sockets.")
        try:
            source_socket.close()
        except socket.error:
            pass # Already closed or error
        try:
            destination_socket.close()
        except socket.error:
            pass # Already closed or error

def handle_client_connection(client_socket, client_address, remote_host, remote_port):
    """
    Handles a new client connection:
    1. Connects to the remote target.
    2. Starts two threads to forward data in both directions.
    """
    print(f"[*] Accepted connection from {client_address[0]}:{client_address[1]}")

    remote_socket = None
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[*] Connecting to remote target {remote_host}:{remote_port}")
        remote_socket.connect((remote_host, remote_port))
        print(f"[*] Connected to remote target {remote_host}:{remote_port}")
    except socket.error as e:
        print(f"[!] Failed to connect to {remote_host}:{remote_port}: {e}")
        client_socket.close()
        if remote_socket:
            remote_socket.close()
        return

    # Start threads for bidirectional data forwarding
    # Client -> Remote
    c2r_thread = threading.Thread(
        target=forward_data,
        args=(client_socket, remote_socket, f"{client_address[0]}:{client_address[1]} -> {remote_host}:{remote_port}")
    )
    # Remote -> Client
    r2c_thread = threading.Thread(
        target=forward_data,
        args=(remote_socket, client_socket, f"{remote_host}:{remote_port} -> {client_address[0]}:{client_address[1]}")
    )

    c2r_thread.daemon = True # Allow main program to exit even if threads are running
    r2c_thread.daemon = True

    c2r_thread.start()
    r2c_thread.start()

    print(f"[*] Forwarding traffic between {client_address[0]}:{client_address[1]} and {remote_host}:{remote_port}")
    # The threads will handle closing sockets.
    # We don't want handle_client_connection to block here, so we let the threads run.
    # If we wanted to wait for them (not typical for a server):
    # c2r_thread.join()
    # r2c_thread.join()
    # print(f"[*] Forwarding threads for {client_address[0]}:{client_address[1]} finished.")

def start_server(local_host, local_port, remote_host, remote_port):
    """
    Starts the listening server.
    """
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow reuse of address
        server_socket.bind((local_host, local_port))
        server_socket.listen(5) # Max backlog of connections
        print(f"[*] Listening on {local_host}:{local_port}")
        print(f"[*] Forwarding traffic to {remote_host}:{remote_port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                # Create a new thread to handle the client connection
                # This allows the server to handle multiple clients simultaneously
                client_handler = threading.Thread(
                    target=handle_client_connection,
                    args=(client_socket, client_address, remote_host, remote_port)
                )
                client_handler.daemon = True
                client_handler.start()
            except socket.error as e:
                print(f"[!] Error accepting connection: {e}")
                # Potentially break if server_socket itself has an issue,
                # but often accept errors are transient or client-side.
            except KeyboardInterrupt:
                print("\n[*] Server shutting down (KeyboardInterrupt).")
                break

    except socket.error as e:
        print(f"[!] Socket error during server setup: {e}")
        print(f"[!] Could not listen on {local_host}:{local_port}. "
              "Check if the port is already in use or if you have permissions.")
    except Exception as e:
        print(f"[!] An unexpected error occurred: {e}")
    finally:
        if server_socket:
            print("[*] Closing server socket.")
            server_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple TCP Port Forwarder")
    parser.add_argument(
        "--local-host",
        type=str,
        default=DEFAULT_LOCAL_HOST,
        help=f"Local host to listen on (default: {DEFAULT_LOCAL_HOST})",
    )
    parser.add_argument(
        "--local-port",
        type=int,
        default=DEFAULT_LOCAL_PORT,
        help=f"Local port to listen on (default: {DEFAULT_LOCAL_PORT})",
    )
    parser.add_argument(
        "--remote-host",
        type=str,
        default=DEFAULT_REMOTE_HOST,
        help=f"Remote host/IP to forward to (default: {DEFAULT_REMOTE_HOST})",
    )
    parser.add_argument(
        "--remote-port",
        type=int,
        default=DEFAULT_REMOTE_PORT,
        help=f"Remote port to forward to (default: {DEFAULT_REMOTE_PORT})",
    )

    args = parser.parse_args()

    start_server(
        args.local_host,
        args.local_port,
        args.remote_host,
        args.remote_port
    )