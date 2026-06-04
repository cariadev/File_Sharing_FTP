# client/config.py - Session-based FTP credentials

FTP_HOST = "172.0.0.1"     
FTP_PORT = 2121

# định nghĩa rõ HOST cho TCP
HOST = "172.0.0.1"          
TCP_HOST = HOST             
TCP_PORT = 9009
# Session storage - credentials theo user đăng nhập
_current_session = {
    "user_id": None,
    "username": None,
    "ftp_user": None,
    "ftp_pass": None
}


def set_session(user_id: int, username: str, ftp_user: str, ftp_pass: str):
    """
    Lưu thông tin session sau khi login thành công
    
    Args:
        user_id: ID của user trong databasepy -m client.app
        username: Username đăng nhập app
        ftp_user: Username để kết nối FTP server
        ftp_pass: Password để kết nối FTP server
    """
    global _current_session
    _current_session = {
        "user_id": user_id,
        "username": username,
        "ftp_user": ftp_user,
        "ftp_pass": ftp_pass
    }
    print(f"[SESSION] ✅ Session set for: {username} (FTP: {ftp_user})")


def clear_session():
    """Xóa session khi logout"""
    global _current_session
    
    # Clear FTP cache trước khi xóa credentials
    try:
        from .net_ftp import clear_cache
        clear_cache()
    except:
        pass
    
    _current_session = {
        "user_id": None,
        "username": None,
        "ftp_user": None,
        "ftp_pass": None
    }
    print("[SESSION] ✅ Session cleared")


def get_current_user_id():
    """Lấy ID của user hiện tại"""
    return _current_session.get("user_id")


def get_current_username():
    """Lấy username của user hiện tại"""
    return _current_session.get("username")


def get_ftp_user():
    """Lấy FTP username của user hiện tại"""
    ftp_user = _current_session.get("ftp_user")
    if not ftp_user:
        print("[WARNING] FTP user not set in session!")
    return ftp_user


def get_ftp_pass():
    """Lấy FTP password của user hiện tại"""
    ftp_pass = _current_session.get("ftp_pass")
    if not ftp_pass:
        print("[WARNING] FTP password not set in session!")
    return ftp_pass


# Legacy function - giữ để tương thích với code cũ
def set_ftp_credentials(username: str, password: str):
    """
    [DEPRECATED] Sử dụng set_session() thay thế
    Hàm này chỉ update FTP credentials mà không update user info
    """
    global _current_session
    _current_session["ftp_user"] = username
    _current_session["ftp_pass"] = password
    print(f"[SESSION] ⚠️ Legacy set_ftp_credentials() called - use set_session() instead")