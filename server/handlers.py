# handlers.py
import uuid
import os
import fitz  # PyMuPDF
import base64
import shutil
import traceback
from datetime import datetime
from decimal import Decimal

import shared.protocol as protocol
from shared import protocol as proto  # để dùng protocol.ok(), protocol.err()

from .models import (
    register_user, login_user, list_approved_files, create_upload_record,
    get_balance, purchase_financials, history_purchases,
    admin_list_users, admin_list_pending_files, admin_user_activity
)
from .otp import create_and_send
from .db import get_conn, dict_cursor
from . import config
from .session import SESSIONS


# ================== HỖ TRỢ ==================
def _get_user_from_token(token: str):
    return SESSIONS.get(token)


def _is_admin(uid: int) -> bool:
    if not uid:
        return False
    conn = get_conn()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT role FROM users WHERE id=%s", (uid,))
        row = cur.fetchone()
        return bool(row and row["role"] == "admin")
    finally:
        conn.close()


# ================== PREVIEW PDF (3 trang đầu) ==================
def handle_preview(data: dict) -> dict:
    filename = data.get("filename")
    if not filename:
        return proto.err("Thiếu tên file")

    possible_paths = [
        os.path.join(config.FTP_ROOT, "shared", "pending", filename),
        os.path.join(config.FTP_ROOT, "shared", "approved", filename),
        os.path.join(config.FTP_ROOT, "shared", "downloads", filename),
    ]

    file_path = None
    for p in possible_paths:
        if os.path.exists(p):
            file_path = p
            print(f"[PREVIEW] Found: {p}")
            break

    if not file_path:
        return proto.err("File không tồn tại trên server")

    try:
        doc = fitz.open(file_path)
        if doc.page_count == 0:
            return proto.err("PDF rỗng")

        images = []
        for page_no in range(min(3, doc.page_count)):
            page = doc.load_page(page_no)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
            images.append(img_b64)

        doc.close()
        return proto.ok({"preview": images})

    except Exception as e:
        print("[PREVIEW ERROR]\n" + traceback.format_exc())
        return proto.err(f"Không thể xem trước: {str(e)}")


# ================== THỐNG KÊ DOANH THU CHO ADMIN ==================
def admin_revenue_stats() -> tuple[bool, dict | str]:
    conn = get_conn()
    cur = dict_cursor(conn)
    try:
        stats = {}

        print("[REVENUE] Bắt đầu tính thống kê")

        # Tổng doanh thu
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM purchases")
        stats["total_revenue"] = float(cur.fetchone()["total"])

        # Hoa hồng admin & uploader
        cur.execute("SELECT COALESCE(SUM(admin_share), 0) AS admin, COALESCE(SUM(uploader_share), 0) AS uploader FROM purchases")
        row = cur.fetchone()
        stats["admin_earnings"] = float(row["admin"])
        stats["uploader_earnings"] = float(row["uploader"])

        # Số giao dịch
        cur.execute("SELECT COUNT(*) AS cnt FROM purchases")
        stats["total_transactions"] = int(cur.fetchone()["cnt"])

        # Doanh thu hôm nay
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS today FROM purchases WHERE DATE(created_at) = CURDATE()")
        stats["today_revenue"] = float(cur.fetchone()["today"])

        # Doanh thu tháng này (bạn đang hiển thị $0)
        cur.execute("SELECT COALESCE(SUM(amount), 0) AS month FROM purchases WHERE YEAR(created_at) = YEAR(CURDATE()) AND MONTH(created_at) = MONTH(CURDATE())")
        stats["month_revenue"] = float(cur.fetchone()["month"])

        # Lịch sử giao dịch gần đây
        print("[REVENUE] Đang query recent_transactions...")
        cur.execute("""
            SELECT 
                p.created_at,
                f.filename,
                u1.username AS uploader,
                u2.username AS buyer,
                p.amount
            FROM purchases p
            JOIN files f ON f.id = p.file_id
            JOIN users u1 ON u1.id = f.uploader_id
            JOIN users u2 ON u2.id = p.buyer_id
            ORDER BY p.created_at DESC
            LIMIT 50
        """)
        recent_transactions = cur.fetchall()
        print(f"[REVENUE] Tìm thấy {len(recent_transactions)} giao dịch gần đây")

        for t in recent_transactions:
            t["amount"] = float(t["amount"])
            t["admin_fee"] = round(t["amount"] * 0.2, 2)

        stats["recent_transactions"] = recent_transactions

        print("[REVENUE] Thống kê hoàn tất")
        return True, stats

    except Exception as e:
        print("[REVENUE STATS ERROR]", str(e))
        import traceback
        traceback.print_exc()
        return False, str(e)
    finally:
        conn.close()
# ================== DUYỆT / TỪ CHỐI FILE ==================
def _admin_set_file_status(file_id: int, status: str, admin_id: int) -> dict:
    conn = get_conn()
    try:
        cur = dict_cursor(conn)

        cur.execute("SELECT filename, stored_path FROM files WHERE id=%s", (file_id,))
        row = cur.fetchone()
        if not row:
            return proto.err("File không tồn tại")

        filename = row["filename"]
        old_path = row["stored_path"]

        # Cập nhật trạng thái
        cur.execute("""
            UPDATE files 
            SET status=%s, approved_at=NOW(), approved_by=%s 
            WHERE id=%s
        """, (status, admin_id, file_id))

        if status == "approved":
            source = os.path.join(config.FTP_ROOT, old_path)
            new_rel = os.path.join("shared", "approved", filename)
            dest = os.path.join(config.FTP_ROOT, new_rel)

            os.makedirs(os.path.dirname(dest), exist_ok=True)

            if os.path.exists(source):
                shutil.move(source, dest)
                print(f"[APPROVED] Moved {source} → {dest}")
                cur.execute("UPDATE files SET stored_path=%s WHERE id=%s", (new_rel.replace("\\", "/"), file_id))
            else:
                print(f"[WARN] File không tồn tại: {source}")

        conn.commit()
        return proto.ok({}, "Thao tác thành công")

    except Exception as e:
        conn.rollback()
        print("[ADMIN FILE STATUS ERROR]", e)
        traceback.print_exc()
        return proto.err("Lỗi hệ thống")
    finally:
        conn.close()


# ================== XỬ LÝ CHÍNH ==================
def handle(msg: dict) -> dict:
    try:
        action = msg.get("action")
        data = msg.get("data", {})

        # 1. Preview - không cần đăng nhập
        if action == protocol.ACTIONS.get("preview"):
            return handle_preview(data)

        # 2. Public actions
        if action == protocol.ACTIONS["register"]:
            ok, res = register_user(
                data.get("username"),
                data.get("password"),
                data.get("email"),
                data.get("role", "user")
            )
            return proto.ok({"user_id": res}) if ok else proto.err(res)

        if action == protocol.ACTIONS["login"]:
            ok, result = login_user(data.get("username"), data.get("password"))
            if not ok:
                return proto.err(result)
            token = str(uuid.uuid4())
            SESSIONS[token] = result["user_id"]
            result["token"] = token
            return proto.ok(result)

        if action == protocol.ACTIONS["list_files"]:
            return proto.ok({"files": list_approved_files()})

        # 3. Cần đăng nhập
        token = data.get("token")
        user_id = _get_user_from_token(token)
        if not user_id:
            return proto.err("Token không hợp lệ hoặc đã hết hạn")

        # === CÁC ACTION CẦN TOKEN ===
        if action == protocol.ACTIONS["balance"]:
            return proto.ok({"balance": get_balance(user_id)})

        if action == protocol.ACTIONS["create_upload_record"]:
            filename = data.get("filename")
            if not filename:
                return proto.err("Thiếu tên file")
            fid = create_upload_record(
                uploader_id=user_id,
                filename=filename,
                stored_path=f"shared/pending/{filename}",
                is_free=data.get("is_free", True),
                price=float(data.get("price", 0)),
                size_bytes=data.get("size_bytes", 0)
            )
            return proto.ok({"file_id": fid})

        if action == protocol.ACTIONS["purchase_request"]:
            file_id = data.get("file_id")
            conn = get_conn()
            cur = dict_cursor(conn)
            cur.execute("SELECT email FROM users WHERE id=%s", (user_id,))
            row = cur.fetchone()
            conn.close()
            email = row["email"] if row else None
            create_and_send(user_id, file_id, email)
            return proto.ok({}, "OTP đã được gửi")

        if action == protocol.ACTIONS["purchase_confirm"]:
            otp = str(data.get("otp", "")).strip()
            file_id = data.get("file_id")

            conn = get_conn()
            cur = dict_cursor(conn)
            cur.execute("""
                SELECT id, otp, expire_at FROM otp_codes
                WHERE user_id=%s AND file_id=%s AND used=0
                ORDER BY id DESC LIMIT 1
            """, (user_id, file_id))
            otp_row = cur.fetchone()

            if not otp_row:
                conn.close()
                return proto.err("OTP không hợp lệ")
            if otp_row["otp"] != otp:
                conn.close()
                return proto.err("OTP sai")
            if datetime.now() > otp_row["expire_at"]:
                conn.close()
                return proto.err("OTP đã hết hạn")

            cur.execute("UPDATE otp_codes SET used=1 WHERE id=%s", (otp_row["id"],))
            conn.commit()
            conn.close()

            ok, msg = purchase_financials(user_id, file_id)
            return proto.ok({}, msg) if ok else proto.err(msg)

        # NẠP TIỀN – QUAN TRỌNG NHẤT
        if action == "topup":
            amount = float(data.get("amount", 0))
            if amount <= 0:
                return proto.err("Số tiền không hợp lệ")

            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
                cur.execute("INSERT INTO topups (user_id, amount, details) VALUES (%s, %s, 'Nạp tiền vào tài khoản')", (user_id, amount))
                conn.commit()
                print(f"[TOPUP SUCCESS] User {user_id} nạp {amount}đ → balance = {get_balance(user_id)}")
                return proto.ok({"new_balance": get_balance(user_id)})
            except Exception as e:
                conn.rollback()
                print("[TOPUP ERROR]", e)
                traceback.print_exc()
                return proto.err("Nạp tiền thất bại")
            finally:
                conn.close()

        # LỊCH SỬ GIAO DỊCH ĐẦY ĐỦ
        if action == "history_transactions":
            transactions = history_transactions(user_id)
            return proto.ok({"transactions": transactions})

        if action == protocol.ACTIONS["history_purchases"]:
            return proto.ok({"items": history_purchases(user_id)})

        # ADMIN ACTIONS
        if not _is_admin(user_id):
            return proto.err("Bạn không có quyền admin")

        if action == protocol.ACTIONS["admin_list_users"]:
            return proto.ok({"users": admin_list_users()})

        if action == protocol.ACTIONS["admin_list_pending_files"]:
            return proto.ok({"files": admin_list_pending_files()})

        if action == protocol.ACTIONS["admin_user_activity"]:
            target_id = data.get("user_id")
            return proto.ok({"items": admin_user_activity(target_id)})

        if action == protocol.ACTIONS["admin_approve_file"]:
            file_id = data.get("file_id")
            return _admin_set_file_status(file_id, "approved", user_id)

        if action == protocol.ACTIONS["admin_reject_file"]:
            file_id = data.get("file_id")
            return _admin_set_file_status(file_id, "rejected", user_id)

        if action == protocol.ACTIONS.get("admin_revenue_stats"):
            ok, result = admin_revenue_stats()
            return proto.ok({"stats": result}) if ok else proto.err(result)

        return proto.err("Action không hỗ trợ")

    except Exception as e:
        print("[SERVER CRASH]", str(e))
        traceback.print_exc()
        return proto.err("Lỗi server nội bộ")
    
def history_transactions(user_id: int):
    conn = get_conn()
    cur = dict_cursor(conn)
    transactions = []

    try:
        # 1. Nạp tiền
        try:
            cur.execute("""
                SELECT 'topup' as type, created_at, amount, details
                FROM topups WHERE user_id=%s ORDER BY created_at DESC
            """, (user_id,))
            for row in cur.fetchall():
                transactions.append({
                    "type": "topup",
                    "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "amount": float(row["amount"]),
                    "details": row["details"] or "Nạp tiền vào tài khoản"
                })
        except Exception as e:
            if "topups" in str(e):
                print("[INFO] Bảng topups chưa tồn tại → bỏ qua")
            else:
                raise

        # 2. Mua file
        cur.execute("""
            SELECT 'purchase' as type, p.created_at, p.amount, f.filename
            FROM purchases p
            JOIN files f ON f.id = p.file_id
            WHERE p.buyer_id=%s
            ORDER BY p.created_at DESC
        """, (user_id,))
        for row in cur.fetchall():
            transactions.append({
                "type": "purchase",
                "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "amount": -float(row["amount"]),
                "details": f"Mua file: {row['filename']}"
            })

        # 3. Nhận hoa hồng
        cur.execute("""
            SELECT 'earning' as type, p.created_at, p.uploader_share as amount, f.filename, u.username as buyer
            FROM purchases p
            JOIN files f ON f.id = p.file_id
            JOIN users u ON u.id = p.buyer_id
            WHERE f.uploader_id=%s AND p.uploader_share > 0
            ORDER BY p.created_at DESC
        """, (user_id,))
        for row in cur.fetchall():
            transactions.append({
                "type": "earning",
                "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "amount": float(row["amount"]),
                "details": f"Nhận hoa hồng từ {row['buyer']} mua '{row['filename']}'"
            })

        transactions.sort(key=lambda x: x["created_at"], reverse=True)
        return transactions

    except Exception as e:
        print("[HISTORY ERROR]", e)
        traceback.print_exc()
        return []
    finally:
        conn.close()