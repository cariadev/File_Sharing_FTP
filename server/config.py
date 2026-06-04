# ====== Server config (edit theo máy bạn) ======
DB_HOST = "127.0.0.1"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "fileshare"

TCP_HOST = "0.0.0.0"
TCP_PORT = 9009

FTP_HOST = "0.0.0.0"
FTP_PORT = 2121
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FTP_ROOT = os.path.join(BASE_DIR, "ftp_files")

# OTP
OTP_EXPIRE_MINUTES = 3

# Email (tuỳ chọn nhưng khuyên dùng)
SMTP_ENABLED = True
SMTP_EMAIL = "loanltk.23itb@vku.udn.vn"
SMTP_PASS = "skis huvf jtsg uypx"
