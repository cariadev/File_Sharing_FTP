import bcrypt

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(pw: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False
