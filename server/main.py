import threading
from . import config
from .tcp_server import run_tcp
from .ftp_server import run_ftp

if __name__ == "__main__":
    t1 = threading.Thread(target=run_tcp, args=(config.TCP_HOST, config.TCP_PORT), daemon=True)
    t2 = threading.Thread(target=run_ftp, args=(config.FTP_HOST, config.FTP_PORT), daemon=True)
    t1.start()
    t2.start()

    print("Server started (TCP + FTP). Ctrl+C to stop.")
    t1.join()
    t2.join()
