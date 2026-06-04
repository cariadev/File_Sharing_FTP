import random
from datetime import datetime, timedelta
from . import config
from .db import get_conn, dict_cursor
from .auth import hash_password 

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def send_email(to_email: str, otp: str) -> None:
    if not config.SMTP_ENABLED or not to_email:
        return
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(f"OTP xác nhận mua file: {otp}\nHiệu lực: {config.OTP_EXPIRE_MINUTES} phút.")
    msg["Subject"] = "Xác nhận giao dịch mua file"
    msg["From"] = config.SMTP_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.SMTP_EMAIL, config.SMTP_PASS)
        s.send_message(msg)

def create_and_send(user_id: int, file_id: int, user_email: str) -> str:
    otp = generate_otp()
    expire = datetime.now() + timedelta(minutes=config.OTP_EXPIRE_MINUTES)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO otp_codes (user_id, file_id, otp, expire_at) VALUES (%s,%s,%s,%s)",
        (user_id, file_id, otp, expire),
    )
    conn.commit()
    cur.close()
    conn.close()

    send_email(user_email, otp)
    return otp  # trả về để server có thể debug/ghi log (client không nên dùng)
