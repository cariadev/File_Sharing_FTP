import socket, json
from admin.config import TCP_HOST, TCP_PORT

def send(msg: dict) -> dict:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((TCP_HOST, TCP_PORT))

        s.sendall((json.dumps(msg) + "\n").encode("utf-8"))

        data = s.recv(4096).decode("utf-8")
        s.close()

        if not data.strip():
            return {"ok": False, "error": "Empty response from server"}

        return json.loads(data.strip())

    except Exception as e:
        return {"ok": False, "error": str(e)}
