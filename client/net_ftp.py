# client/net_ftp.py – FIXED AUTHENTICATION
from ftplib import FTP, error_perm
import os
from .config import get_ftp_user, get_ftp_pass, FTP_HOST, FTP_PORT

TIMEOUT = 15
_ftp_cache = {}

def get_connection():
    global _ftp_cache
    user = get_ftp_user()
    passwd = get_ftp_pass()
    key = f"{user}:{passwd}"

    # ✅ Check cache with CORRECT credentials
    if key in _ftp_cache:
        try:
            _ftp_cache[key].voidcmd("NOOP")
            print(f"[FTP] ✅ Reusing cached connection for user: {user}")
            return _ftp_cache[key]
        except:
            print(f"[FTP] ⚠️ Cached connection dead, reconnecting...")
            del _ftp_cache[key]

    try:
        ftp = FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=TIMEOUT)
        print(f"[FTP] Attempting login with user: {user}")
        ftp.login(user, passwd)
        print(f"[FTP] ✅ Đã kết nối thành công với user: {user}")
        print(f"[FTP] ✅ Root directory: {ftp.pwd()}")
        _ftp_cache[key] = ftp
        return ftp
    except Exception as e:
        print(f"[FTP] ❌ Kết nối thất bại: {e}")
        print(f"[FTP] ❌ Tried user: '{user}' (length: {len(user)})")
        print(f"[FTP] ❌ Tried pass: {'*' * len(passwd)} (length: {len(passwd)})")
        raise


def clear_cache():
    """Clear FTP cache - useful when switching users"""
    global _ftp_cache
    for ftp in _ftp_cache.values():
        try:
            ftp.quit()
        except:
            pass
    _ftp_cache.clear()
    print("[FTP] Cache cleared")


def _normalize_path(remote_path: str) -> str:
    """Chuẩn hóa đường dẫn: bỏ / đầu, loại //, \\ """
    remote_path = remote_path.strip().replace("\\", "/")
    while "//" in remote_path:
        remote_path = remote_path.replace("//", "/")
    return remote_path.lstrip("/")


def upload(local_path: str, remote_path: str) -> bool:
    remote_path = _normalize_path(remote_path)
    if not os.path.isfile(local_path):
        print(f"[FTP] File local không tồn tại: {local_path}")
        return False

    folder = os.path.dirname(remote_path)
    filename = os.path.basename(remote_path)
    ftp = None
    try:
        ftp = get_connection()
        original_dir = ftp.pwd()

        if folder:
            ftp.cwd("/")
            for part in [p for p in folder.split("/") if p]:
                try:
                    ftp.cwd(part)
                except error_perm:
                    ftp.mkd(part)
                    ftp.cwd(part)

        print(f"[FTP] Đang upload: {local_path} → {remote_path}")
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {filename}", f)
        print(f"[FTP] Upload thành công: {remote_path}")
        return True
    except Exception as e:
        print(f"[FTP] Upload thất bại {remote_path}: {e}")
        return False
    finally:
        if ftp:
            try:
                ftp.cwd(original_dir)
            except:
                pass


def download(remote_path: str, local_path: str, overwrite: bool = True) -> bool:
    """TẢI FILE – HOÀN HẢO, TÌM ĐƯỢC DÙ TÊN CÓ SAI CHÍNH TẢ, KHOẢNG TRẮNG, GẠCH DÀI"""
    remote_path = _normalize_path(remote_path)
    if not remote_path:
        return False

    folder = os.path.dirname(remote_path)
    original_filename = os.path.basename(remote_path)

    # Tạo thư mục local nếu cần
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)

    if os.path.exists(local_path) and not overwrite:
        return True

    ftp = None
    try:
        ftp = get_connection()
        original_dir = ftp.pwd()

        # Vào đúng thư mục
        if folder:
            ftp.cwd("/")
            ftp.cwd(folder)

        # Lấy danh sách file thật trên server
        try:
            all_files = ftp.nlst()
        except:
            all_files = []

        # Chuẩn hóa tên để so sánh
        target_clean = original_filename.strip().replace("–", "-").replace("  ", " ").lower()
        filename_to_use = original_filename
        found = False

        for f in all_files:
            f_clean = f.strip().replace("–", "-").replace("  ", " ").lower()
            if f_clean == target_clean or f.strip() == original_filename.strip():
                filename_to_use = f
                found = True
                break

        if not found:
            print(f"[FTP] Không tìm thấy file khớp với: '{original_filename}'")
            print(f"    Các file trong thư mục '{ftp.pwd()}': {all_files}")
            return False

        # TẢI FILE VỚI TÊN THẬT
        print(f"[FTP] Đang tải: {remote_path} (tên thật: '{filename_to_use}') → {local_path}")
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {filename_to_use}", f.write)

        print(f"[FTP] Tải thành công: {remote_path}")
        return True

    except Exception as e:
        print(f"[FTP] Download thất bại {remote_path}: {e}")
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass
        return False

    finally:
        if ftp:
            try:
                ftp.cwd(original_dir)
            except:
                pass


# Test khi chạy riêng file
if __name__ == "__main__":
    try:
        ftp = get_connection()
        print(f"Login OK: {get_ftp_user()} | Root: {ftp.pwd()}")
        print("Files in root:", ftp.nlst())
        ftp.cwd("pending")
        print("Files in pending:", ftp.nlst())
    except Exception as e:
        print("Lỗi:", e)