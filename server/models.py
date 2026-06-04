from datetime import datetime
from .db import get_conn, dict_cursor, tuple_cursor
from .auth import hash_password, verify_password
import os
from . import config


def register_user(username, password, email, role="user"):
    conn = get_conn()
    try:
        cur = dict_cursor(conn)

        # Kiểm tra trùng
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return False, "Username đã tồn tại"

        # Hash mật khẩu
        hashed_pw = hash_password(password)

        # Tạo FTP account
        ftp_username = username
        ftp_password = password  # để raw thì FTP mới đăng nhập được

        # Lưu DB
        cur.execute("""
            INSERT INTO users (username, password_hash, email, role, ftp_username, ftp_password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, hashed_pw, email, role, ftp_username, ftp_password))

        conn.commit()

        # Tạo folder FTP
        user_dir = os.path.join(config.FTP_ROOT, "users", ftp_username)
        os.makedirs(user_dir, exist_ok=True)

        print(f"[FTP] Created folder: {user_dir}")

        return True, cur.lastrowid

    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def login_user(username, password):
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    conn.close()
    if not row or not verify_password(password, row["password_hash"]):
        return (False, "Sai tài khoản hoặc mật khẩu")
    return (True, {"user_id": row["id"], "role": row["role"], "balance": float(row["balance"]), "email": row.get("email")})

def list_approved_files():
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("""
        SELECT f.id, f.filename, f.is_free, f.price, f.size_bytes, u.username AS uploader
        FROM files f JOIN users u ON u.id=f.uploader_id
        WHERE f.status='approved'
        ORDER BY f.uploaded_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def create_upload_record(uploader_id, filename, stored_path, is_free, price, size_bytes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO files (uploader_id, filename, stored_path, is_free, price, size_bytes, status)
        VALUES (%s,%s,%s,%s,%s,%s,'pending')
    """, (uploader_id, filename, stored_path, 1 if is_free else 0, price, size_bytes))
    file_id = cur.lastrowid
    cur.execute("INSERT INTO upload_events (file_id,uploader_id,action) VALUES (%s,%s,'created')",
                (file_id, uploader_id))
    conn.commit()
    conn.close()
    return file_id

def get_balance(user_id):
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("SELECT balance FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return float(row["balance"]) if row else 0.0

def purchase_financials(buyer_id, file_id):
    conn = get_conn()
    cur = dict_cursor(conn)

    # Lấy tài khoản admin thật
    cur.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    admin_row = cur.fetchone()
    admin_id = admin_row["id"] if admin_row else None

    if not admin_id:
        conn.close()
        return (False, "Không tìm thấy admin để nhận hoa hồng")

    # Lấy file info
    cur.execute("SELECT uploader_id, price FROM files WHERE id=%s AND status='approved'", (file_id,))
    f = cur.fetchone()
    if not f:
        conn.close()
        return (False, "File chưa được duyệt hoặc không tồn tại")

    price = float(f["price"])
    uploader_id = f["uploader_id"]

    # Check tiền
    cur.execute("SELECT balance FROM users WHERE id=%s", (buyer_id,))
    b = cur.fetchone()
    if not b or float(b["balance"]) < price:
        conn.close()
        return (False, "Số dư không đủ")

    # Chia 80/20
    uploader_share = round(price * 0.8, 2)
    admin_share = round(price * 0.2, 2)

    cur2 = conn.cursor()

    # Trừ buyer
    cur2.execute("UPDATE users SET balance=balance-%s WHERE id=%s", (price, buyer_id))

    # Cộng seller
    cur2.execute("UPDATE users SET balance=balance+%s WHERE id=%s", (uploader_share, uploader_id))

    # Cộng admin thực sự
    cur2.execute("UPDATE users SET balance=balance+%s WHERE id=%s", (admin_share, admin_id))

    # Ghi lịch sử
    cur2.execute("""
        INSERT INTO purchases (buyer_id,file_id,amount,uploader_share,admin_share)
        VALUES (%s,%s,%s,%s,%s)
    """, (buyer_id, file_id, price, uploader_share, admin_share))

    conn.commit()
    conn.close()
    return (True, "Đã trừ tiền và ghi lịch sử giao dịch")

def history_purchases(user_id):
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("""
        SELECT p.id, p.created_at, p.amount, f.filename
        FROM purchases p JOIN files f ON f.id=p.file_id
        WHERE p.buyer_id=%s ORDER BY p.created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def admin_list_users():
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("SELECT id, username, role, balance, created_at FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def admin_list_pending_files():
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("""
      SELECT f.id, f.filename, f.is_free, f.price, f.size_bytes, u.username AS uploader, f.uploaded_at
      FROM files f JOIN users u ON u.id=f.uploader_id
      WHERE f.status='pending' ORDER BY f.uploaded_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def admin_user_activity(user_id):
    conn = get_conn()
    cur = dict_cursor(conn)
    cur.execute("""
      SELECT 'upload' AS kind, f.id AS ref_id, f.filename, f.status, f.uploaded_at AS at
      FROM files f WHERE f.uploader_id=%s
      UNION ALL
      SELECT 'purchase' AS kind, p.id AS ref_id, f.filename, 'n/a' AS status, p.created_at AS at
      FROM purchases p JOIN files f ON f.id=p.file_id
      WHERE p.buyer_id=%s
      ORDER BY at DESC
    """, (user_id, user_id))
    rows = cur.fetchall()
    conn.close()
    return rows
def admin_revenue_stats():
    conn = get_conn()
    cur = dict_cursor(conn)
    
    # Tổng doanh thu toàn hệ thống (tổng tiền buyer đã trả)
    cur.execute("SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM purchases")
    total = cur.fetchone()["total_revenue"]
    
    # Doanh thu hôm nay
    today = datetime.now().date()
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS today_revenue 
        FROM purchases 
        WHERE DATE(created_at) = %s
    """, (today,))
    today_revenue = cur.fetchone()["today_revenue"]
    
    # Số giao dịch
    cur.execute("SELECT COUNT(*) AS total_transactions FROM purchases")
    total_transactions = cur.fetchone()["total_transactions"]
    
    # Số file đã bán (có ít nhất 1 lượt mua)
    cur.execute("""
        SELECT COUNT(DISTINCT file_id) AS files_sold 
        FROM purchases
    """)
    files_sold = cur.fetchone()["files_sold"]
    
    # Top 5 uploader kiếm nhiều nhất (tùy chọn)
    cur.execute("""
        SELECT u.username, COALESCE(SUM(p.uploader_share), 0) AS earnings
        FROM purchases p 
        JOIN files f ON f.id = p.file_id 
        JOIN users u ON u.id = f.uploader_id
        GROUP BY u.id, u.username
        ORDER BY earnings DESC LIMIT 5
    """)
    top_earners = cur.fetchall()
    
    conn.close()
    
    return {
        "total_revenue": float(total),
        "today_revenue": float(today_revenue),
        "total_transactions": int(total_transactions),
        "files_sold": int(files_sold),
        "top_earners": [
            {"username": e["username"], "earnings": float(e["earnings"])}
            for e in top_earners
        ]
    }