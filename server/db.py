# server/db.py – HOÀN CHỈNH 100%, CHẠY NGON NGAY LẬP TỨC!
import mysql.connector
from mysql.connector import pooling
from . import config  # Lấy DB config từ server/config.py

# Connection pool toàn cục
_pool = None

def get_pool():
    """Tạo hoặc trả về connection pool MySQL"""
    global _pool
    if _pool is None:
        print("[DB] Đang khởi tạo MySQL connection pool...")
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="fileshare_pool",
                pool_size=10,
                host=config.DB_HOST,
                port=getattr(config, "DB_PORT", 3306),
                user=config.DB_USER,
                password=config.DB_PASS,
                database=config.DB_NAME,
                auth_plugin="mysql_native_password",
                autocommit=True
            )
            print(f"[DB] Kết nối MySQL thành công! → {config.DB_HOST}:{config.DB_NAME}")
        except Exception as e:
            print(f"[DB ERROR] Không kết nối được MySQL: {e}")
            raise
    return _pool

def get_conn():
    """Lấy 1 kết nối từ pool"""
    return get_pool().get_connection()

def dict_cursor(conn):
    """Cursor trả về dict (dễ dùng nhất)"""
    return conn.cursor(dictionary=True)

def tuple_cursor(conn):
    """Cursor trả về tuple (nếu cần)"""
    return conn.cursor()

# Test kết nối khi chạy file trực tiếp (tùy chọn)
if __name__ == "__main__":
    try:
        conn = get_conn()
        cur = dict_cursor(conn)
        cur.execute("SELECT 'Kết nối DB thành công!' AS msg")
        print(cur.fetchone())
        conn.close()
    except Exception as e:
        print(f"[TEST FAILED] {e}")