import tkinter as tk
from tkinter import ttk, messagebox
from admin.ui_common import style_root
from admin.net_tcp import send
from shared import protocol


class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FileShare Admin")
        self.geometry("1040x640")
        style_root(self)

        # session: luôn có user_id; token có thể None (nếu server chưa trả token)
        self.session = {"user_id": None, "token": None}

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        self.frames = {}
        for F in (LoginFrame, Dashboard):
            f = F(self.container, self)
            self.frames[F.__name__] = f
            f.grid(row=0, column=0, sticky="nsew")

        self.show("LoginFrame")

    def show(self, name: str):
        self.frames[name].tkraise()
        # Khi vừa chuyển sang Dashboard (sau login) thì mới refresh dữ liệu
        if name == "Dashboard":
            self.frames["Dashboard"].refresh_all()


class LoginFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="ADMIN LOGIN", font=("Segoe UI", 14, "bold")).pack(pady=10)

        frm = ttk.Frame(self)
        frm.pack(pady=10)

        ttk.Label(frm, text="Username").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        self.u = ttk.Entry(frm, width=26)
        self.u.grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(frm, text="Password").grid(row=1, column=0, padx=6, pady=4, sticky="w")
        self.p = ttk.Entry(frm, show="*", width=26)
        self.p.grid(row=1, column=1, padx=6, pady=4)

        ttk.Button(self, text="Đăng nhập", command=self.login).pack(pady=8)

    def login(self):
        res = send({
            "action": protocol.ACTIONS["login"],
            "data": {"username": self.u.get(), "password": self.p.get()}
        })

        # Tránh crash nếu server trả về format khác
        if not res.get("ok"):
            messagebox.showerror("Lỗi", res.get("error", "Đăng nhập thất bại"))
            return

        data = res.get("data", {}) or {}
        role = data.get("role")
        user_id = data.get("user_id")

        if role != "admin" or not user_id:
            messagebox.showerror("Lỗi", "Tài khoản này không phải admin.")
            return

        # Ghi session: token có thể không có (server cũ), nhưng vẫn chạy được
        self.app.session["user_id"] = user_id
        self.app.session["token"] = data.get("token")  # có thì dùng, không có thì None

        self.app.show("Dashboard")


class Dashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, pady=6)

        self.users = ttk.Frame(nb); nb.add(self.users, text="Users")
        self.pending = ttk.Frame(nb); nb.add(self.pending, text="Pending files")
        self.activity = ttk.Frame(nb); nb.add(self.activity, text="User activity")

        self.build_users()
        self.build_pending()
        self.build_activity()

    # Helper: build payload cho mọi request admin (token trước, nếu không có thì dùng admin_id)
    def _admin_payload(self, extra=None):
        extra = extra or {}
        token = self.app.session.get("token")
        if token:
            base = {"token": token}
        else:
            base = {"admin_id": self.app.session.get("user_id")}
        base.update(extra)
        return base

    def build_users(self):
        ttk.Label(self.users, text="Danh sách user", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=6)
        self.lst_users = tk.Listbox(self.users, width=90, height=22)
        self.lst_users.pack(padx=8, pady=6)

    def build_pending(self):
        ttk.Label(self.pending, text="Files chờ duyệt", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=6)
        self.lst_pending = tk.Listbox(self.pending, width=90, height=22)
        self.lst_pending.pack(padx=8, pady=6)

        btns = ttk.Frame(self.pending); btns.pack(pady=6)
        ttk.Button(btns, text="Approve", command=self.approve).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Reject", command=self.reject).grid(row=0, column=1, padx=6)

    def build_activity(self):
        ttk.Label(self.activity, text="Hoạt động theo user", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=6)
        frm = ttk.Frame(self.activity); frm.pack(pady=6)

        ttk.Label(frm, text="User ID:").grid(row=0, column=0, padx=6, pady=4)
        self.e_uid = ttk.Entry(frm, width=12); self.e_uid.grid(row=0, column=1, padx=6, pady=4)
        ttk.Button(frm, text="Load", command=self.load_activity).grid(row=0, column=2, padx=6)

        self.lst_act = tk.Listbox(self.activity, width=90, height=20)
        self.lst_act.pack(padx=8, pady=6)

    def refresh_all(self):
        # Chỉ refresh khi đã có user_id (đã login)
        if not self.app.session.get("user_id"):
            return
        self.refresh_users()
        self.refresh_pending()

    def refresh_users(self):
        res = send({
            "action": protocol.ACTIONS["admin_list_users"],
            "data": self._admin_payload()
        })
        self.lst_users.delete(0, "end")
        if not res.get("ok"):
            return
        for u in res["data"].get("users", []):
            self.lst_users.insert("end", f"#{u['id']} | {u['username']} | {u['role']} | bal={u['balance']}")

    def refresh_pending(self):
        res = send({
            "action": protocol.ACTIONS["admin_list_pending_files"],
            "data": self._admin_payload()
        })
        self.lst_pending.delete(0, "end")
        if not res.get("ok"):
            return
        for f in res["data"].get("files", []):
            price = "FREE" if f["is_free"] else f"{f['price']}$"
            line = f"#{f['id']} | {f['filename']} | {price} | by {f['uploader']}"
            self.lst_pending.insert("end", line)

    def _selected_file_id(self):
        idx = self.lst_pending.curselection()
        if not idx:
            messagebox.showwarning("Chưa chọn", "Chọn 1 file trong danh sách.")
            return None
        line = self.lst_pending.get(idx[0])
        return int(line.split("|")[0].strip().lstrip("#"))

    def approve(self):
        fid = self._selected_file_id()
        if not fid:
            return
        res = send({
            "action": protocol.ACTIONS["admin_approve_file"],
            "data": self._admin_payload({"file_id": fid})
        })
        messagebox.showinfo("Kết quả", res.get("message") or res.get("error"))
        self.refresh_pending()

    def reject(self):
        fid = self._selected_file_id()
        if not fid:
            return
        res = send({
            "action": protocol.ACTIONS["admin_reject_file"],
            "data": self._admin_payload({"file_id": fid})
        })
        messagebox.showinfo("Kết quả", res.get("message") or res.get("error"))
        self.refresh_pending()

    def load_activity(self):
        try:
            uid = int(self.e_uid.get().strip())
        except ValueError:
            messagebox.showerror("Sai", "User ID phải là số.")
            return

        res = send({
            "action": protocol.ACTIONS["admin_user_activity"],
            "data": self._admin_payload({"user_id": uid})
        })
        self.lst_act.delete(0, "end")
        if not res.get("ok"):
            return
        for it in res["data"].get("items", []):
            self.lst_act.insert("end", f"{it['at']} | {it['kind']} | {it['filename']} | {it['status']}")


if __name__ == "__main__":
    AdminApp().mainloop()
