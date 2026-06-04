# server/ftp_server.py – TẤT CẢ USER DÙNG CHUNG 1 THƯ MỤC (PENDING / APPROVED / DOWNLOADS)

import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# Import từ project của bạn (đảm bảo đúng đường dẫn)
from . import config
from .db import get_conn, dict_cursor

def ensure_dirs(path):
    os.makedirs(path, exist_ok=True)

def create_ftp_users_from_db():
    authorizer = DummyAuthorizer()
    
    # THƯ MỤC CHUNG CHO TẤT CẢ USER
    shared_root = os.path.join(config.FTP_ROOT, "shared")
    ensure_dirs(shared_root)
    ensure_dirs(os.path.join(shared_root, "pending"))
    ensure_dirs(os.path.join(shared_root, "approved"))
    ensure_dirs(os.path.join(shared_root, "downloads"))

    conn = None
    try:
        conn = get_conn()
        cur = dict_cursor(conn)
        cur.execute("SELECT ftp_username, ftp_password FROM users WHERE ftp_username IS NOT NULL")
        rows = cur.fetchall()

        if not rows:
            print("[FTP] Không có user nào trong DB → tạo user test")
            rows = [{"ftp_username": "acc", "ftp_password": "123456"}]

        for row in rows:
            username = row["ftp_username"]
            password = row["ftp_password"]
            
            authorizer.add_user(
                username=username,
                password=password,
                homedir=shared_root,
                perm="elradfmwMT"  # Quyền đầy đủ
            )
            print(f"[FTP] Đã thêm user: {username} (pass: {password[:3]}***) → dùng chung {shared_root}")

    except Exception as e:
        print(f"[FTP ERROR] Lỗi kết nối DB: {e}")
        # Fallback user
        authorizer.add_user("acc", "123456", shared_root, perm="elradfmwMT")
        print("[FTP] Dùng user fallback: acc / 123456")

    finally:
        if conn:
            conn.close()

    return authorizer

def run_ftp(host="0.0.0.0", port=21):
    ensure_dirs(config.FTP_ROOT)
    print("[FTP] Đang load user từ database...")
    authorizer = create_ftp_users_from_db()

    handler = FTPHandler
    handler.authorizer = authorizer
    handler.banner = "Welcome to FTP File Manager - Shared Storage"

    server = FTPServer((host, port), handler)
    print(f"[FTP] Server đang chạy tại {host}:{port}")
    print(f"[FTP] Tất cả user dùng chung: {os.path.join(config.FTP_ROOT, 'shared')}")
    server.serve_forever()

if __name__ == "__main__":
    run_ftp()