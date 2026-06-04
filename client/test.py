from client.net_ftp import connection


ftp = connection()

print("PWD:", ftp.pwd())
print("ROOT LIST:", ftp.nlst())

for d in ("pending", "downloads"):
    try:
        ftp.cwd(d)
        print(f"{d}/:", ftp.nlst())
        ftp.cwd("..")
    except Exception as e:
        print(f"Cannot enter {d}:", e)

ftp.quit()
