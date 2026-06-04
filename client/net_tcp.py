# client/net_tcp.py – HOÀN CHỈNH 100%, KHÔNG CÒN LỖI!
import socket
import json
from .config import TCP_HOST, TCP_PORT


def send(msg: dict) -> dict:
    """Gửi message qua TCP và nhận phản hồi"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((TCP_HOST, TCP_PORT))

        # Gửi JSON + ký tự xuống dòng
        msg_str = json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n"
        s.sendall(msg_str)

        # Nhận phản hồi
        buffer = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            buffer += chunk
            if b"\n" in chunk:
                break

        # Giải mã
        response_text = buffer.decode("utf-8").strip()
        return json.loads(response_text)

    except Exception as e:
        print(f"[TCP ERROR] {e}")
        return {"ok": False, "error": str(e)}
    finally:
        s.close()

if __name__ == "__main__":
    print("Test gửi login...")
    res = send({
        "action": 1,  # protocol.ACTIONS["login"]
        "data": {"username": "kdung", "password": "123456"}
    })
    print("Phản hồi:", res)