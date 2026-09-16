import socket
def check_status():
    # Tries to connect to persistent local socket
    try:
        s = socket.socket()
        s.connect(('127.0.0.1', 59999))
        s.sendall(b'PASS')
        s.close()
    except Exception:
        pass
    return False
