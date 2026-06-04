import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, Canvas, Scrollbar
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import datetime
from decimal import Decimal
import base64
import zlib
import traceback

# Giả lập modules nếu thiếu (để test local)
try:
    from shared import protocol
    from shared.protocol import ACTIONS
except ImportError:
    print("Warning: shared.protocol not found - using fake")
    class FakeProtocol:
        ACTIONS = {
            "login": "login",
            "register": "register",
            "balance": "balance",
            "list_files": "list_files",
            "preview": "preview",
            "purchase_request": "purchase_request",
            "purchase_confirm": "purchase_confirm",
            "create_upload_record": "create_upload_record",
            "history_purchases": "history_purchases"
        }
    protocol = FakeProtocol()

try:
    from .net_tcp import send
except ImportError:
    print("Warning: net_tcp not found - using fake send")
    def send(data):
        print("[FAKE SEND]", data)
        action = data.get("action")
        if action == protocol.ACTIONS["login"]:
            return {"ok": True, "data": {"user_id": 1, "balance": 10000, "token": "fake_token"}}
        elif action == protocol.ACTIONS["register"]:
            return {"ok": True}
        elif action == protocol.ACTIONS["list_files"]:
            return {"ok": True, "data": {"files": [{"id": 1, "filename": "test.pdf", "is_free": True, "price": 0}]}}
        elif action == protocol.ACTIONS["preview"]:
            return {"ok": True, "data": [{"data": base64.b64encode(b'fake_image_data')}]}
        elif action == protocol.ACTIONS["purchase_request"]:
            return {"ok": True}
        elif action == protocol.ACTIONS["purchase_confirm"]:
            return {"ok": True}
        elif action == protocol.ACTIONS["create_upload_record"]:
            return {"ok": True}
        elif action == "topup":
            return {"ok": True, "data": {"new_balance": 20000}}
        elif action == protocol.ACTIONS["balance"]:
            return {"ok": True, "data": {"balance": 10000}}
        elif action == "history_transactions" or action == protocol.ACTIONS["history_purchases"]:
            return {"ok": True, "data": {"items": [{"id": 1, "created_at": datetime.datetime.now(), "amount": -10.00, "filename": "test.pdf"}]}}
        return {"ok": False, "error": "Fake error"}

try:
    from .net_ftp import upload, download
except ImportError:
    print("Warning: net_ftp not found - using fake")
    def upload(local, remote):
        print(f"[FAKE UPLOAD] {local} to {remote}")
        return True
    def download(remote, local):
        print(f"[FAKE DOWNLOAD] {remote} to {local}")
        with open(local, 'w') as f:
            f.write("Fake file content")
        return True

try:
    from .config import set_ftp_credentials
except ImportError:
    def set_ftp_credentials(u, p):
        print(f"[FAKE] Set FTP creds: {u}")

# ============================= BOOTSTRAP-INSPIRED THEME =============================
COLORS = {
    "bg": "#f8f9fa",
    "white": "#ffffff",
    "cream": "#f8f9fa",
    "green": "#198754",
    "green_hover": "#157347",
    "green_light": "#d1e7dd",
    "red": "#dc3545",
    "red_hover": "#bb2d3b",
    "border": "#dee2e6",
    "text": "#212529",
    "text_gray": "#6c757d",
    "text_muted": "#adb5bd",
    "card_hover": "#f8f9fa",
    "card_bg": "#ffffff",
    "income": "#28a745",
    "expense": "#dc3545",
    "blue": "#0d6efd",
}
FONT_FAMILY = "Times New Roman"

class SoftButton(tk.Canvas):
    def __init__(self, parent, text, command, bg_color=None, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.bg_color = bg_color or COLORS["green"]
        self.hover_color = COLORS["green_hover"] if bg_color == COLORS["green"] else COLORS["red_hover"]
        self.is_hover = False
        
        
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.draw()
    
    def draw(self):
        self.delete("all")
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        if w <= 1: w = 150
        if h <= 1: h = 40
        color = self.hover_color if self.is_hover else self.bg_color
        self.create_rounded_rect(2, 2, w, h, 20, fill="#d0d0d0", outline="")
        self.create_rounded_rect(0, 0, w-2, h-2, 20, fill=color, outline="")
        self.create_text((w-2)//2, (h-2)//2, text=self.text, fill="white", font=("Segoe UI", 10, "bold"))
    
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, 
                 x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2,
                 x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2,
                 x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, e):
        self.is_hover = True
        self.draw()
        self.configure(cursor="hand2")
    
    def on_leave(self, e):
        self.is_hover = False
        self.draw()
        self.configure(cursor="")

class FileCardCompact(tk.Frame):
    def __init__(self, parent, file_info, on_preview, on_buy):
        super().__init__(parent, bg="white", relief="flat", bd=1,
                        highlightbackground="#dee2e6", highlightthickness=1)
        
        self.file_info = file_info
        
        # Dùng grid để căn đẹp
        self.grid_columnconfigure(0, weight=1)
        
        main = tk.Frame(self, bg="white")
        main.grid(row=0, column=0, sticky="ew", padx=15, pady=12)
        main.grid_columnconfigure(0, weight=1)

        # Tên file + icon
        left = tk.Frame(main, bg="white")
        left.grid(row=0, column=0, sticky="w")
        tk.Label(left, text="FILE", font=("Segoe UI", 16), bg="white", fg="#6c757d").pack(side="left")
        name = file_info['filename']
        if len(name) > 60: name = name[:57] + "..."
        tk.Label(left, text=name, font=("Segoe UI", 11, "bold"), bg="white", fg="#212529", anchor="w")\
            .pack(side="left", padx=(10,0), fill="x", expand=True)

        # Giá + nút
        right = tk.Frame(main, bg="white")
        right.grid(row=0, column=1, sticky="e")

        if file_info.get("is_free"):
            tk.Label(right, text="MIỄN PHÍ", font=("Segoe UI", 10, "bold"),
                    bg="#d4edda", fg="#28a745", padx=12, pady=4).pack(side="left", padx=(0,10))
        else:
            p = file_info.get("price", 0)
            tk.Label(right, text=f"{p:,}đ".replace(",","."), font=("Segoe UI", 10, "bold"),
                    bg="#f8d7da", fg="#dc3545", padx=12, pady=4).pack(side="left", padx=(0,10))

        tk.Button(right, text="Xem trước", font=("Segoe UI", 9), bg="white", fg="#198754",
                  relief="solid", bd=1, command=lambda: on_preview(file_info["id"]), width=12).pack(side="left", padx=3)
        
        btn_text = "Tải ngay" if file_info.get("is_free") else "Mua ngay"
        tk.Button(right, text=btn_text, font=("Segoe UI", 9, "bold"), bg="#198754", fg="white",
                  command=lambda: on_buy(file_info["id"]), width=12).pack(side="left")

        # Hover đẹp
        self.bind("<Enter>", lambda e: self.config(bg="#f8f9fa"))
        self.bind("<Leave>", lambda e: self.config(bg="white"))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FileSharing")
        self.geometry("1100x650")
        self.configure(bg=COLORS["bg"])
        
        self.session = {"user_id": None, "role": "user", "balance": 0.0, "email": None, "username": "Guest"}
        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, MainFrame):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.place(x=0, y=0, relwidth=1, relheight=1)

        self.show("LoginFrame")

    def show(self, name: str):
        self.frames[name].tkraise()

    def set_session(self, data: dict):
        self.session.update(data)

class LoginFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["cream"])
        self.app = app
        
        shadow = tk.Frame(self, bg="#e0e0e0")
        shadow.place(relx=0.5, rely=0.5, anchor="center", width=504, height=504)
        
        container = tk.Frame(self, bg=COLORS["white"])
        container.place(relx=0.5, rely=0.5, anchor="center", width=500, height=500)
        
        self.lbl_title = tk.Label(container, text="ĐĂNG NHẬP", font=("Segoe UI", 18, "bold"),
                                 bg=COLORS["white"], fg=COLORS["text"])
        self.lbl_title.pack(pady=(40, 10))
        
        tk.Label(container, text="Chào mừng đến với FileSharing!", font=("Segoe UI", 11),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(pady=(0, 40))
        
        form = tk.Frame(container, bg=COLORS["white"])
        form.pack(padx=50, fill="x")
        
        tk.Label(form, text="Tên đăng nhập", font=("Segoe UI", 10),
                bg=COLORS["white"], fg=COLORS["text"]).pack(anchor="w", pady=(10, 5))
        
        user_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1, 
                             highlightbackground=COLORS["border"], highlightthickness=1)
        user_frame.pack(fill="x", pady=(0, 20))
        
        self.e_login_user = tk.Entry(user_frame, font=("Segoe UI", 11), relief="flat", 
                                     bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_login_user.pack(fill="x", padx=12, pady=10)
        
        tk.Label(form, text="Mật khẩu", font=("Segoe UI", 10),
                bg=COLORS["white"], fg=COLORS["text"]).pack(anchor="w", pady=(5, 5))
        
        pass_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1,
                             highlightbackground=COLORS["border"], highlightthickness=1)
        pass_frame.pack(fill="x", pady=(0, 35))
        
        self.e_login_pass = tk.Entry(pass_frame, font=("Segoe UI", 11), show="●", 
                                     relief="flat", bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_login_pass.pack(fill="x", padx=12, pady=10)
        self.e_login_pass.bind("<Return>", lambda e: self.login())
        
        btn_login = SoftButton(form, "ĐĂNG NHẬP", self.login, width=400, height=45)
        btn_login.pack()
        
        link_frame = tk.Frame(form, bg=COLORS["white"])
        link_frame.pack(pady=20)
        
        tk.Label(link_frame, text="Bạn chưa có tài khoản? ", font=("Segoe UI", 9),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(side="left")
        
        lbl_signup = tk.Label(link_frame, text="Đăng ký ngay!", font=("Segoe UI", 9, "bold"),
                             bg=COLORS["white"], fg=COLORS["red"], cursor="hand2")
        lbl_signup.pack(side="left")
        lbl_signup.bind("<Button-1>", lambda e: self.show_signup())
        
        self.signup_shadow = tk.Frame(self, bg="#e0e0e0")
        self.signup_container = tk.Frame(self, bg=COLORS["white"])
        self.build_signup_form()

    def build_signup_form(self):
        tk.Label(self.signup_container, text="ĐĂNG KÝ", font=("Segoe UI", 18, "bold"),
                bg=COLORS["white"], fg=COLORS["text"]).pack(pady=(40, 10))
        
        tk.Label(self.signup_container, text="Chào mừng đến với FileSharing!", font=("Segoe UI", 11),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(pady=(0, 35))
        
        form = tk.Frame(self.signup_container, bg=COLORS["white"])
        form.pack(padx=50, fill="x")
        
        tk.Label(form, text="Tên đăng nhập", font=("Segoe UI", 10),
                bg=COLORS["white"], fg=COLORS["text"]).pack(anchor="w", pady=(5, 5))
        
        user_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        user_frame.pack(fill="x", pady=(0, 18))
        
        self.e_reg_user = tk.Entry(user_frame, font=("Segoe UI", 11), relief="flat", 
                                   bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_reg_user.pack(fill="x", padx=12, pady=10)
        
        tk.Label(form, text="Mật khẩu", font=("Segoe UI", 10),
                bg=COLORS["white"], fg=COLORS["text"]).pack(anchor="w", pady=(5, 5))
        
        pass_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        pass_frame.pack(fill="x", pady=(0, 18))
        
        self.e_reg_pass = tk.Entry(pass_frame, font=("Segoe UI", 11), show="●", 
                                   relief="flat", bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_reg_pass.pack(fill="x", padx=12, pady=10)
        
        tk.Label(form, text="Email", font=("Segoe UI", 10),
                bg=COLORS["white"], fg=COLORS["text"]).pack(anchor="w", pady=(5, 5))
        
        mail_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        mail_frame.pack(fill="x", pady=(0, 35))
        
        self.e_reg_mail = tk.Entry(mail_frame, font=("Segoe UI", 11), relief="flat", 
                                   bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_reg_mail.pack(fill="x", padx=12, pady=10)
        
        btn_signup = SoftButton(form, "ĐĂNG KÝ", self.register, width=400, height=45)
        btn_signup.pack()
        
        link_frame = tk.Frame(form, bg=COLORS["white"])
        link_frame.pack(pady=20)
        
        tk.Label(link_frame, text="Bạn đã có tài khoản? ", font=("Segoe UI", 9),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(side="left")
        
        lbl_login = tk.Label(link_frame, text="Đăng nhập ngay!", font=("Segoe UI", 9, "bold"),
                            bg=COLORS["white"], fg=COLORS["red"], cursor="hand2")
        lbl_login.pack(side="left")
        lbl_login.bind("<Button-1>", lambda e: self.show_login())

    def show_signup(self):
        self.lbl_title.master.place_forget()
        self.signup_shadow.place(relx=0.5, rely=0.5, anchor="center", width=504, height=564)
        self.signup_container.place(relx=0.5, rely=0.5, anchor="center", width=500, height=560)

    def show_login(self):
        self.signup_shadow.place_forget()
        self.signup_container.place_forget()
        self.lbl_title.master.place(relx=0.5, rely=0.5, anchor="center", width=500, height=500)

    def register(self):
        username = self.e_reg_user.get().strip()
        pw = self.e_reg_pass.get().strip()
        mail = self.e_reg_mail.get().strip()
        if not username or not pw:
            messagebox.showerror("Lỗi", "Nhập tên đăng nhập và mật khẩu!")
            return
        try:
            res = send({"action": protocol.ACTIONS["register"], "data": {"username": username, "password": pw, "email": mail or None}})
            if res.get("ok"):
                messagebox.showinfo("Thành công", "Đăng ký thành công!")
                self.show_login()
            else:
                messagebox.showerror("Lỗi", res.get("error", "Đăng ký thất bại"))
        except Exception as e:
            messagebox.showerror("Lỗi mạng", str(e))

    def login(self):
        username = self.e_login_user.get().strip()
        pw = self.e_login_pass.get().strip()
        if not username or not pw:
            messagebox.showwarning("Thiếu thông tin", "Điền đầy đủ thông tin!")
            return
        try:
            res = send({"action": protocol.ACTIONS["login"], "data": {"username": username, "password": pw}})
            if res.get("ok"):
                set_ftp_credentials(username, pw)
                res["data"]["username"] = username
                self.app.set_session(res["data"])
                self.app.session["token"] = res["data"].get("token")
                self.app.show("MainFrame")
                self.app.frames["MainFrame"].refresh_all()
            else:
                messagebox.showerror("Lỗi", res.get("error", "Thông tin không hợp lệ"))
        except Exception as e:
            messagebox.showerror("Lỗi kết nối", str(e))


class MainFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["cream"])
        self.app = app
        self.files_map = {}
        self.preview_images = []
        self.selected_local_file = None
        self.current_tab = "file"
        self.all_files = []
        self.history_built = False

        # Header
        header = tk.Canvas(self, height=75, bg=COLORS["green"], highlightthickness=0)
        header.pack(fill="x", side="top")
        
        for i in range(75):
            ratio = i / 75
            r1, g1, b1 = 0x19, 0x87, 0x54
            r2, g2, b2 = 0x14, 0x6c, 0x43
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f'#{r:02x}{g:02x}{b:02x}'
            header.create_line(0, i, 1100, i, fill=color, width=1)
        
        header.create_text(25, 37, text="📁 FileSharing", font=("Segoe UI", 16, "bold"), fill="white", anchor="w")
        
        
        
        self.user_info_frame = tk.Frame(header, bg=COLORS["green"])
        header.create_window(1070, 37, window=self.user_info_frame, anchor="e")
        
        self.lbl_username = tk.Label(self.user_info_frame, text="Guest", font=("Segoe UI", 11, "bold"),
                                     bg=COLORS["green"], fg="white")
        self.lbl_username.pack(side="left", padx=(0, 15))
        
        self.lbl_balance = tk.Label(self.user_info_frame, text="💰 đ", font=("Segoe UI", 10, "bold"),
                                    bg=COLORS["green_hover"], fg="white", padx=12, pady=6)
        self.lbl_balance.pack(side="left")
        
        # Nav
        nav_bg = tk.Frame(self, bg=COLORS["white"], height=50)
        nav_bg.pack(fill="x", side="top")
        nav_bg.pack_propagate(False)
        
        nav_frame = tk.Frame(nav_bg, bg=COLORS["white"])
        nav_frame.pack(side="left", padx=25)
        
        self.nav_buttons = {}
        self.nav_icons = {}  # Giữ reference tránh bị garbage collect

        
        icons = {
            "file": "file.png",
            "history": "history.png", 
            "upload": "upload.png",
            "topup": "topup.png",
            "logout": "logout.png"
        }

        nav_items = [
            ("File", "file"),
            ("Lịch sử", "history"),
            ("Upload", "upload"),
            ("Nạp tiền", "topup"),
            ("Đăng xuất", "logout")
        ]

        for text, tab in nav_items:
            btn_frame = tk.Frame(nav_frame, bg=COLORS["white"])
            btn_frame.pack(side="left", padx=6)

            # Thử load icon
            icon_path = icons.get(tab)
            if icon_path and os.path.exists(icon_path):
                try:
                    img = Image.open(icon_path).resize((28, 28), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.nav_icons[tab] = photo  # QUAN TRỌNG: giữ reference
                    
                    tk.Label(btn_frame, image=photo, bg=COLORS["white"]).pack(side="left", padx=(15, 5))
                except:
                    pass  # Nếu lỗi → bỏ qua icon

            btn = tk.Label(btn_frame, text=text, font=("Segoe UI", 10),
                          bg=COLORS["white"], fg=COLORS["text_gray"], cursor="hand2")
            btn.pack(side="left", padx=(0, 15), pady=15)

            if tab == "logout":
                btn.bind("<Button-1>", lambda e: self.logout())
            else:
                btn.bind("<Button-1>", lambda e, t=tab: self.switch_tab(t))

            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=COLORS["green"], font=("Segoe UI", 10, "bold")))
            btn.bind("<Leave>", lambda e, b=btn, t=tab: b.config(
                fg=COLORS["green"] if self.current_tab == t else COLORS["text_gray"],
                font=("Segoe UI", 10, "bold") if self.current_tab == t else ("Segoe UI", 10)))

            self.nav_buttons[tab] = btn

        self.content = tk.Frame(self, bg=COLORS["cream"])
        self.content.pack(fill="both", expand=True, padx=25, pady=25)
        
        self.tab_file = tk.Frame(self.content, bg=COLORS["cream"])
        self.tab_history = tk.Frame(self.content, bg=COLORS["cream"])
        self.tab_upload = tk.Frame(self.content, bg=COLORS["cream"])
        self.tab_topup = tk.Frame(self.content, bg=COLORS["cream"])

        self.build_file_tab()
        self.build_upload_tab()
        self.build_topup_tab()
        
        self.after(200, lambda: self.switch_tab("file"))

    def logout(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn đăng xuất?"):
            self.app.session = {"user_id": None, "role": "user", "balance": 0.0, "email": None, "username": "Guest"}
            self.app.show("LoginFrame")

    def update_user_info(self):
        username = self.app.session.get("username", "Guest")
        balance = self.app.session.get("balance", 0)
        self.lbl_username.config(text=f"👤 {username}")
        self.lbl_balance.config(text=f"💰 {balance:,.0f}đ")

    def switch_tab(self, tab_name):
        for key, btn in self.nav_buttons.items():
            btn.config(fg=COLORS["text_gray"], font=(FONT_FAMILY, 10))
        
        if tab_name in self.nav_buttons:
            self.nav_buttons[tab_name].config(fg=COLORS["green"], font=(FONT_FAMILY, 10, "bold"))
        
        for tab in [self.tab_file, self.tab_history, self.tab_upload, self.tab_topup]:
            tab.pack_forget()
        
        self.current_tab = tab_name
        
        if tab_name == "file":
            self.tab_file.pack(fill="both", expand=True)
            self.load_files()
        elif tab_name == "history":
            self.tab_history.pack(fill="both", expand=True)
            self.build_history_tab()
            self.load_history()
        elif tab_name == "upload":
            self.tab_upload.pack(fill="both", expand=True)
        elif tab_name == "topup":
            self.tab_topup.pack(fill="both", expand=True)

    def build_file_tab(self):
        self.file_title = tk.Label(self.tab_file, text="CHÀO MỪNG, GUEST!", 
                font=("Segoe UI", 22, "bold"), bg=COLORS["cream"], fg=COLORS["text"])
        self.file_title.pack(anchor="w", pady=(5, 20))
        
        split = tk.Frame(self.tab_file, bg=COLORS["cream"])
        split.pack(fill="both", expand=True)
        
        left_container = tk.Frame(split, bg=COLORS["cream"])
        left_container.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        left = tk.Frame(left_container, bg=COLORS["white"], relief="solid", bd=1,
                       highlightbackground=COLORS["border"], highlightthickness=1)
        left.pack(fill="both", expand=True)
        
        search_header = tk.Frame(left, bg=COLORS["white"], height=55)
        search_header.pack(fill="x")
        search_header.pack_propagate(False)
        
        search_inner = tk.Frame(search_header, bg=COLORS["white"])
        search_inner.pack(fill="x", padx=15, pady=12)
        
        tk.Label(search_inner, text="🔍", font=("Segoe UI", 14),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(side="left", padx=(0, 8))
        
        self.search_var = tk.StringVar()
        
        
        search_frame = tk.Frame(search_inner, bg=COLORS["white"], relief="solid", bd=1,
                               highlightbackground=COLORS["border"], highlightthickness=1)
        search_frame.pack(side="left", fill="x", expand=True)
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               font=("Segoe UI", 10), relief="flat", bg=COLORS["white"], fg=COLORS["text"], bd=0)
        search_entry.pack(fill="x", padx=10, pady=8)
        search_entry.insert(0, "Tìm kiếm file...")
        search_entry.config(fg=COLORS["text_muted"])
        self.search_var.trace('w', lambda *args: self.filter_files())
        
        def on_focus_in(e):
            if search_entry.get() == "Tìm kiếm file...":
                search_entry.delete(0, tk.END)
                search_entry.config(fg=COLORS["text"])
        
        def on_focus_out(e):
            if not search_entry.get():
                search_entry.insert(0, "Tìm kiếm file...")
                search_entry.config(fg=COLORS["text_muted"])
        
        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)
        
        tk.Frame(left, bg=COLORS["border"], height=1).pack(fill="x")
        
        header_frame = tk.Frame(left, bg="#f8f9fa", height=45)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="FILE", font=("Segoe UI", 10, "bold"),
                bg="#f8f9fa", fg=COLORS["text"], anchor="w", width=40).pack(side="left", padx=(20, 0), pady=12)
        
        tk.Label(header_frame, text="GIÁ", font=("Segoe UI", 10, "bold"),
                bg="#f8f9fa", fg=COLORS["text"], anchor="center", width=10).pack(side="left", padx=10, pady=12)
        
        tk.Label(header_frame, text="THAO TÁC", font=("Segoe UI", 10, "bold"),
                bg="#f8f9fa", fg=COLORS["text"], anchor="center", width=25).pack(side="left", padx=10, pady=12)
        
        tk.Frame(left, bg=COLORS["border"], height=1).pack(fill="x")
        
        cards_outer = tk.Frame(left, bg=COLORS["white"])
        cards_outer.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(cards_outer, bg=COLORS["white"], highlightthickness=0)
        scrollbar = tk.Scrollbar(cards_outer, command=canvas.yview, width=12)
        
        self.cards_container = tk.Frame(canvas, bg=COLORS["white"])
        canvas.create_window((0,0), window=self.cards_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.cards_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        right_container = tk.Frame(split, bg=COLORS["cream"], width=420)
        right_container.pack(side="right", fill="both")
        right_container.pack_propagate(False)
        
        right = tk.Frame(right_container, bg=COLORS["white"], relief="solid", bd=1,
                        highlightbackground=COLORS["border"], highlightthickness=1)
        right.pack(fill="both", expand=True)
        
        preview_header = tk.Frame(right, bg=COLORS["white"], height=55)
        preview_header.pack(fill="x")
        preview_header.pack_propagate(False)
        
        tk.Label(preview_header, text=" Xem trước", font=("Segoe UI", 12, "bold"),
                bg=COLORS["white"], fg=COLORS["text"]).pack(side="left", padx=15, pady=15)
        
        tk.Frame(right, bg=COLORS["border"], height=1).pack(fill="x")
        
        preview_container = tk.Frame(right, bg=COLORS["white"])
        preview_container.pack(fill="both", expand=True)
        
        canvas_preview = tk.Canvas(preview_container, bg=COLORS["white"], highlightthickness=0)
        scrollbar_preview = tk.Scrollbar(preview_container, command=canvas_preview.yview, width=12)
        
        self.preview_panel = tk.Frame(canvas_preview, bg=COLORS["white"])
        canvas_preview.create_window((0,0), window=self.preview_panel, anchor="nw")
        canvas_preview.configure(yscrollcommand=scrollbar_preview.set)
        
        canvas_preview.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        scrollbar_preview.pack(side="right", fill="y")
        
        self.preview_panel.bind("<Configure>", lambda e: canvas_preview.configure(scrollregion=canvas_preview.bbox("all")))
        
        self.preview_default = tk.Label(self.preview_panel, text="Chọn file để xem trước",
                                       font=("Segoe UI", 11), fg=COLORS["text_muted"], bg=COLORS["white"])
        self.preview_default.pack(pady=100)
        self.search_var.trace_add("write", lambda *args: self.filter_files())
        
        if self.app.session["user_id"]:
            self.after(300, self.load_files)

    def build_history_tab(self):
        if self.history_built:
            return
        self.history_built = True

        self.history_title = tk.Label(self.tab_history, text="CHÀO MỪNG, GUEST!",
            font=("Segoe UI", 22, "bold"), bg=COLORS["cream"], fg=COLORS["text"])
        self.history_title.pack(anchor="w", pady=(5, 20))

        container = tk.Frame(self.tab_history, bg="white", relief="solid", bd=1,
                             highlightbackground=COLORS["border"], highlightthickness=1)
        container.pack(fill="both", expand=True, padx=20, pady=(0,20))

        header = tk.Frame(container, bg="#e9ecef", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="THỜI GIAN",      font=("Segoe UI", 10, "bold"), bg="#e9ecef", width=22).pack(side="left", padx=20, pady=12)
        tk.Label(header, text="LOẠI GIAO DỊCH", font=("Segoe UI", 10, "bold"), bg="#e9ecef", width=18).pack(side="left", padx=10)
        tk.Label(header, text="SỐ TIỀN",       font=("Segoe UI", 10, "bold"), bg="#e9ecef", width=18).pack(side="left", padx=10)
        tk.Label(header, text="CHI TIẾT",       font=("Segoe UI", 10, "bold"), bg="#e9ecef").pack(side="left", fill="x", expand=True, padx=20)

        tk.Frame(container, height=1, bg="#dee2e6").pack(fill="x")

        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview, width=14)
        canvas.configure(yscrollcommand=scrollbar.set)

        self.history_container = tk.Frame(canvas, bg="white")
        canvas.create_window((0,0), window=self.history_container, anchor="nw")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.history_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas.find_withtag("all")[0], width=e.width) if canvas.find_withtag("all") else None)

    def load_history(self):
        for widget in self.history_container.winfo_children():
            widget.destroy()

        try:
            # Ưu tiên action mới: history_transactions (có + và - tiền)
            res = send({"action": "history_transactions", "data": {"token": self.app.session.get("token")}})

            # Fallback nếu server chưa có action mới
            if not res.get("ok"):
                res = send({"action": protocol.ACTIONS["history_purchases"], "data": {"token": self.app.session.get("token")}})

            if not res.get("ok"):
                raise Exception(res.get("error", "Lỗi server"))

            # Lấy danh sách từ action mới
            items = res.get("data", {}).get("transactions") or res.get("data", {}).get("items", [])

            if not items:
                tk.Label(self.history_container, text="Chưa có giao dịch nào",
                        fg=COLORS["text_muted"], font=("Segoe UI", 11), bg="white").pack(pady=120)
                return

            for idx, item in enumerate(items):
                row_bg = "white" if idx % 2 == 0 else "#f8f9fa"
                row = tk.Frame(self.history_container, bg=row_bg, height=60)
                row.pack(fill="x", padx=8, pady=2)
                row.pack_propagate(False)

                # Thời gian
                time_raw = item.get("created_at") or item.get("time") or "N/A"
                if isinstance(time_raw, datetime.datetime):
                    time_str = time_raw.strftime("%d/%m/%Y %H:%M")
                else:
                    time_str = str(time_raw)[:19].replace("T", " ")

                amount = float(item.get("amount", 0))

                # Xác định loại giao dịch và màu
                trans_type = item.get("type", "").lower()
                if trans_type in ["topup", "earning"] or amount > 0:
                    type_text = "Nạp tiền" if trans_type == "topup" else "Thu nhập"
                    amount_text = f"+{abs(amount):,.0f}đ"
                    color = "#28a745"  # xanh
                else:
                    type_text = "Mua file"
                    amount_text = f"-{abs(amount):,.0f}đ"
                    color = "#dc3545"  # đỏ

                # Chi tiết
                details = item.get("details") or item.get("filename") or "Giao dịch"

                tk.Label(row, text=time_str, font=("Segoe UI", 9), bg=row_bg, fg="#212529", anchor="w", width=22)\
                    .pack(side="left", padx=20)
                tk.Label(row, text=type_text, font=("Segoe UI", 9, "bold"), bg=row_bg, fg=color, width=18)\
                    .pack(side="left", padx=10)
                tk.Label(row, text=amount_text, font=("Segoe UI", 10, "bold"), bg=row_bg, fg=color, width=18)\
                    .pack(side="left", padx=10)
                tk.Label(row, text=details, font=("Segoe UI", 9), bg=row_bg, fg="#6c757d", anchor="w")\
                    .pack(side="left", fill="x", expand=True, padx=20)

                if idx < len(items)-1:
                    tk.Frame(self.history_container, height=1, bg="#dee2e6").pack(fill="x", pady=2)

        except Exception as e:
            print("Lỗi load_history:", e)
            tk.Label(self.history_container, text=f"Không tải được lịch sử\n{e}",
                    fg="red", font=("Segoe UI", 11), bg="white").pack(pady=100)

    def build_upload_tab(self):
        self.upload_title = tk.Label(self.tab_upload, text="CHÀO MỪNG, GUEST!", 
                font=("Segoe UI", 22, "bold"), bg=COLORS["cream"], fg=COLORS["text"])
        self.upload_title.pack(anchor="w", pady=(5, 20))
        
        container = tk.Frame(self.tab_upload, bg=COLORS["white"], relief="solid", bd=1,
                           highlightbackground=COLORS["border"], highlightthickness=1)
        container.pack(fill="both", expand=True)
        
        header = tk.Frame(container, bg=COLORS["green"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="⬆️  CHỌN FILE BẠN MUỐN UPLOAD", font=("Segoe UI", 12, "bold"),
                bg=COLORS["green"], fg="white").pack(pady=15)
        
        form = tk.Frame(container, bg=COLORS["white"])
        form.pack(fill="both", expand=True, padx=60, pady=25)  # Giảm pady từ 35 xuống 25
        
        tk.Label(form, text="File", font=("Segoe UI", 11, "bold"),
                bg=COLORS["white"], fg=COLORS["text"], anchor="w").pack(fill="x", pady=(10, 8))
        
        file_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        file_frame.pack(fill="x", pady=(0, 15))
        
        file_inner = tk.Frame(file_frame, bg=COLORS["white"])
        file_inner.pack(fill="x", padx=5, pady=5)
        
        self.lbl_selected_file = tk.Label(file_inner, text="Chưa chọn file", font=("Segoe UI", 10),
                                         bg=COLORS["white"], fg=COLORS["text_muted"], anchor="w")
        self.lbl_selected_file.pack(side="left", fill="x", expand=True, padx=7, pady=7)
        
        btn_choose = tk.Button(file_inner, text="Chọn file", font=("Segoe UI", 9, "bold"),
                              bg=COLORS["green"], fg="white", relief="flat", cursor="hand2", bd=0,
                              activebackground=COLORS["green_hover"], 
                              command=self.pick_file_for_upload, height=1)
        btn_choose.pack(side="right", padx=5, pady=5)
        
        tk.Label(form, text="Loại file", font=("Segoe UI", 11, "bold"),
                bg=COLORS["white"], fg=COLORS["text"], anchor="w").pack(fill="x", pady=(10, 8))
        
        self.var_type = tk.StringVar(value="free")
        
        type_frame = tk.Frame(form, bg=COLORS["white"])
        type_frame.pack(fill="x", pady=(0, 15))
        
        tk.Radiobutton(type_frame, text="Có phí", variable=self.var_type, value="paid",
                      font=("Segoe UI", 11), bg=COLORS["white"], fg=COLORS["text"],
                      selectcolor=COLORS["white"], activebackground=COLORS["white"]).pack(side="left", padx=(0, 35))
        tk.Radiobutton(type_frame, text="Miễn phí", variable=self.var_type, value="free",
                      font=("Segoe UI", 11), bg=COLORS["white"], fg=COLORS["text"],
                      selectcolor=COLORS["white"], activebackground=COLORS["white"]).pack(side="left")
        
        tk.Label(form, text="Giá (nếu có phí)", font=("Segoe UI", 11, "bold"),
                bg=COLORS["white"], fg=COLORS["text"], anchor="w").pack(fill="x", pady=(10, 8))
        
        price_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        price_frame.pack(fill="x", pady=(0, 20))
        
        self.e_price = tk.Entry(price_frame, font=("Segoe UI", 11), relief="flat",
                               bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_price.pack(fill="x", padx=12, pady=10)
        self.e_price.insert(0, "10")
        
        # Thêm khoảng trống trước nút upload
        tk.Frame(form, bg=COLORS["white"], height=20).pack(fill="x")
        
        # Frame chứa nút upload căn giữa
        btn_frame = tk.Frame(form, bg=COLORS["white"])
        btn_frame.pack(fill="x", pady=(10, 0))
        
        btn_upload = SoftButton(btn_frame, "UPLOAD", self.do_upload,
                               bg_color=COLORS["green"], width=300, height=48)
        btn_upload.pack(anchor="center")

    def build_topup_tab(self):
        self.topup_title = tk.Label(self.tab_topup, text="CHÀO MỪNG, GUEST!", 
                font=("Segoe UI", 22, "bold"), bg=COLORS["cream"], fg=COLORS["text"])
        self.topup_title.pack(anchor="w", pady=(5, 20))
        
        container = tk.Frame(self.tab_topup, bg=COLORS["white"], relief="solid", bd=1,
                           highlightbackground=COLORS["border"], highlightthickness=1)
        container.pack(fill="both", expand=True)
        
        header = tk.Frame(container, bg=COLORS["green"], height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="💳  NẠP TIỀN", font=("Segoe UI", 12, "bold"),
                bg=COLORS["green"], fg="white").pack(pady=15)
        
        form = tk.Frame(container, bg=COLORS["white"])
        form.pack(fill="both", expand=True, padx=60, pady=35)
        
        tk.Label(form, text="Chọn mệnh giá:", font=("Segoe UI", 11),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(anchor="w", pady=(10, 15))
        
        amounts_frame = tk.Frame(form, bg=COLORS["white"])
        amounts_frame.pack(fill="x", pady=(0, 25))
        
        amounts = [("10K", 10000), ("20K", 20000), ("50K", 50000), ("100K", 100000)]
        for i, (text, amount) in enumerate(amounts):
            btn = tk.Button(amounts_frame, text=text, font=("Segoe UI", 11, "bold"),
                          bg=COLORS["white"], fg=COLORS["text"], relief="solid", bd=1, cursor="hand2",
                          width=10, height=2, command=lambda amt=amount: (self.e_topup.delete(0, tk.END), self.e_topup.insert(0, str(amt))))
            btn.grid(row=0, column=i, padx=8, pady=0)
            
            def on_enter(e, b=btn):
                b.config(bg=COLORS["green_light"])
            def on_leave(e, b=btn):
                b.config(bg=COLORS["white"])
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        tk.Label(form, text="Hoặc nhập số tiền:", font=("Segoe UI", 11),
                bg=COLORS["white"], fg=COLORS["text_gray"]).pack(anchor="w", pady=(15, 10))
        
        amount_frame = tk.Frame(form, bg=COLORS["white"], relief="solid", bd=1)
        amount_frame.pack(fill="x", pady=(0, 35))
        
        self.e_topup = tk.Entry(amount_frame, font=("Segoe UI", 13), relief="flat",
                               bg=COLORS["white"], fg=COLORS["text"], bd=0)
        self.e_topup.pack(fill="x", padx=15, pady=15)
        self.e_topup.insert(0, "10000")
        
        # Frame chứa nút xác nhận căn giữa
        btn_frame = tk.Frame(form, bg=COLORS["white"])
        btn_frame.pack(fill="x", pady=(10, 0))
        
        btn_confirm = SoftButton(btn_frame, "XÁC NHẬN NẠP TIỀN", 
                                lambda: self.topup_amount(self.parse_amount(self.e_topup.get())),
                                bg_color=COLORS["green"], width=300, height=48)
        btn_confirm.pack(anchor="center")

    def parse_amount(self, text):
        text = text.strip().upper().replace("K", "000").replace(",", "")
        try:
            return int(text)
        except:
            return 0

    def topup_amount(self, amount):
        if amount <= 0:
            messagebox.showwarning("Lỗi", "Nhập số tiền hợp lệ!")
            return

        try:
            res = send({
                "action": "topup",
                "data": {
                    "amount": amount,
                    "token": self.app.session.get("token")  # BẮT BUỘC PHẢI CÓ TOKEN
                }
            })

            if res.get("ok"):
                new_balance = res["data"]["new_balance"]
                self.app.session["balance"] = new_balance
                self.update_user_info()
                messagebox.showinfo("Thành công", f"Nạp {amount:,}đ thành công!\nSố dư mới: {new_balance:,.0f}đ")
                self.refresh_all()
            else:
                messagebox.showerror("Lỗi", res.get("error", "Nạp thất bại"))
        except Exception as e:
            messagebox.showerror("Lỗi mạng", str(e))

    def refresh_top(self):
        uid = self.app.session.get("user_id")
        if not uid: return
        try:
            res = send({"action": protocol.ACTIONS["balance"], "data": {"user_id": uid}})
            if res.get("ok"): 
                self.app.session["balance"] = res["data"]["balance"]
        except: 
            pass

    def refresh_all(self):
        self.refresh_top()
        self.update_user_info()
        self.update_welcome_messages()
        if self.current_tab == "file":
            self.load_files()
        if self.current_tab == "history":
            self.load_history()
    
    def update_welcome_messages(self):
        username = self.app.session.get("username", "GUEST").upper()
        welcome_text = f"CHÀO MỪNG, {username}!"
        self.file_title.config(text=welcome_text)
        if hasattr(self, 'history_title'):
            self.history_title.config(text=welcome_text)
        self.upload_title.config(text=welcome_text)
        self.topup_title.config(text=welcome_text)

    def filter_files(self):
        search_text = self.search_var.get().lower().strip()
        if search_text == "tìm kiếm file...":
            search_text = ""
        
        for widget in self.cards_container.winfo_children():
            widget.destroy()
        
        filtered_files = [f for f in self.all_files if search_text in f['filename'].lower() or not search_text]
        
        if filtered_files:
            for f in filtered_files:
                card = FileCardCompact(self.cards_container, f,
                       on_preview=self.preview_file,
                       on_buy=self.buy_file)
                card.pack(fill="both", expand=True, pady=2, padx=0)
        else:
            empty_frame = tk.Frame(self.cards_container, bg=COLORS["white"])
            empty_frame.pack(fill="both", expand=True)
            tk.Label(empty_frame, text="Không tìm thấy file nào",
                    font=("Segoe UI", 11), fg=COLORS["text_muted"], bg=COLORS["white"]).pack(pady=80)
    
    def preview_file(self, file_id):
            if not file_id: 
                return
            info = self.files_map.get(file_id)
            if not info: 
                return

            try:
                res = send({
                    "action": protocol.ACTIONS["preview"], 
                    "data": {"filename": info["filename"], "file_id": file_id}
                })

                if not res.get("ok"):
                    messagebox.showerror("Lỗi", res.get("error", "Không thể xem trước"))
                    return

                # Xóa preview cũ
                for widget in self.preview_panel.winfo_children():
                    widget.destroy()
                self.preview_images.clear()

                # LẤY DỮ LIỆU PREVIEW CHUẨN
                preview_data = []
                if "preview" in res:
                    preview_data = res["preview"]
                elif "data" in res:
                    if isinstance(res["data"], list):
                        preview_data = res["data"]
                    elif "preview" in res["data"]:
                        preview_data = res["data"]["preview"]

                if not preview_data:
                    tk.Label(self.preview_panel, text="Không có trang xem trước",
                            font=("Segoe UI", 11), fg=COLORS["text_muted"], bg="white").pack(pady=100)
                    return

                # Header tên file
                header_frame = tk.Frame(self.preview_panel, bg=COLORS["green_light"])
                header_frame.pack(fill="x", padx=15, pady=10)
                tk.Label(header_frame, text=f"{info['filename']}", 
                        font=("Segoe UI", 12, "bold"), bg=COLORS["green_light"], fg="#155724").pack(anchor="w", padx=10)

                # Hiển thị từng trang
                for i, b64_str in enumerate(preview_data, 1):
                    try:
                        # SỬA CHỖ NÀY – QUAN TRỌNG NHẤT!
                        if isinstance(b64_str, str):
                            # Loại bỏ tiền tố data:image/png;base64, nếu có
                            if "data:" in b64_str:
                                b64_str = b64_str.split(",", 1)[1]
                            # Fix padding
                            b64_str += '=' * ((4 - len(b64_str) % 4) % 4)
                            img_bytes = base64.b64decode(b64_str)
                        else:
                            img_bytes = b64_str

                        img = Image.open(io.BytesIO(img_bytes))
                        img = img.resize((380, int(380 * img.height / img.width)), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)

                        frame = tk.Frame(self.preview_panel, bg="white", relief="solid", bd=1)
                        frame.pack(pady=8, padx=15, fill="x")

                        tk.Label(frame, text=f"Trang {i}", font=("Segoe UI", 9, "bold"), 
                                bg="white", fg=COLORS["text_gray"]).pack(anchor="w", padx=10, pady=(5,2))

                        lbl = tk.Label(frame, image=photo, bg="white")
                        lbl.image = photo  # Giữ reference
                        lbl.pack(padx=10, pady=5)
                        self.preview_images.append(photo)

                    except Exception as e:
                        print(f"[PREVIEW PAGE {i} ERROR]", e)
                        tk.Label(self.preview_panel, text=f"Không hiển thị được trang {i}", 
                                fg="red", bg="white").pack(pady=5)

                # Thông báo thành công
                tk.Label(self.preview_panel, text=f"Đã tải {len(self.preview_images)} trang xem trước", 
                        fg=COLORS["green"], font=("Segoe UI", 10, "bold"), bg="white").pack(pady=10)

            except Exception as e:
                print("[PREVIEW TOTAL ERROR]", traceback.format_exc())
                tk.Label(self.preview_panel, text=f"Lỗi kết nối hoặc file không hỗ trợ xem trước", 
                        fg="red", bg="white").pack(pady=50)

    def buy_file(self, file_id):
        self.buy_selected_by_id(file_id)

    def load_files(self):
        try:
            res = send({"action": protocol.ACTIONS["list_files"], "data": {}})
            if not res.get("ok"):
                raise Exception(res.get("error", "Lỗi server"))

            self.all_files = res["data"]["files"]
            self.files_map = {f["id"]: f for f in self.all_files}
            self.filter_files()
        except Exception as e:
            for widget in self.cards_container.winfo_children():
                widget.destroy()
            tk.Label(self.cards_container,
                     text=f"Không tải được danh sách file\n{e}",
                     fg="red",
                     bg="white",
                     font=("Segoe UI", 11)).pack(pady=100)

    def filter_files(self):
        search = (self.search_var.get() or "").lower().strip()
        if search == "tìm kiếm file...":
            search = ""

        for widget in self.cards_container.winfo_children():
            widget.destroy()

        count = 0
        for f in self.all_files:
            if search in f["filename"].lower():
                card = FileCardCompact(
                    self.cards_container,
                    file_info=f,
                    on_preview=self.preview_file,
                    on_buy=self.buy_file
                )
                card.pack(fill="both", expand=True, pady=2, padx=0)
                count += 1

        if count == 0:
            tk.Label(self.cards_container,
                     text="Không tìm thấy file nào",
                     fg=COLORS["text_muted"],
                     bg="white",
                     font=("Segoe UI", 11)).pack(pady=100)

    def pick_file_for_upload(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.selected_local_file = path
            name = os.path.basename(path)
            size = os.path.getsize(path) / (1024*1024)
            self.lbl_selected_file.config(text=f"✓  {name} ({size:.2f} MB)", fg=COLORS["green"])

    def do_upload(self):
        if not self.selected_local_file:
            messagebox.showwarning("Lỗi", "Chọn file trước!")
            return

        filename = os.path.basename(self.selected_local_file)
        is_free = self.var_type.get() == "free"
        price = 0.0 if is_free else float(self.e_price.get() or 0)

        remote_path = f"pending/{filename}"
        
        if not upload(self.selected_local_file, remote_path):
            messagebox.showerror("Lỗi", "Tải lên FTP thất bại!")
            return

        try:
            request_data = {
                "uploader_id": self.app.session["user_id"],
                "filename": filename,
                "stored_path": f"shared/pending/{filename}",
                "is_free": is_free,
                "price": price,
                "size_bytes": os.path.getsize(self.selected_local_file),
                "token": self.app.session.get("token")
            }

            res = send({
                "action": protocol.ACTIONS["create_upload_record"],
                "data": request_data
            })

            if res.get("ok"):
                messagebox.showinfo("Thành công", "Tải lên thành công! Chờ duyệt")
                self.selected_local_file = None
                self.lbl_selected_file.config(text="Chưa chọn file", fg=COLORS["text_muted"])
            else:
                messagebox.showerror("Lỗi", res.get("error", "Lỗi không xác định từ server"))
        except Exception as e:
            messagebox.showerror("Lỗi DB", str(e))

    def buy_selected_by_id(self, fid):
        if not fid: return
        info = self.files_map.get(fid)
        if not info: return
        uid = self.app.session["user_id"]

        if info.get("is_free"):
            save_path = filedialog.asksaveasfilename(initialfile=info['filename'], defaultextension=".pdf")
            if not save_path: return
            
            stored = info.get('stored_path', '')
            paths_to_try = [stored, f"pending/{info['filename']}", f"approved/{info['filename']}", 
                           f"downloads/{info['filename']}", info['filename']]
            paths_to_try = list(set(p for p in paths_to_try if p))
            
            success = False
            for p in paths_to_try:
                try:
                    if download(p, save_path):
                        messagebox.showinfo("Thành công", f"Đã tải file miễn phí!\nLưu tại: {save_path}")
                        success = True
                        break
                except: pass
                    
            if not success:
                messagebox.showerror("Lỗi tải xuống", "Không thể tải file miễn phí")
            return

        try:
            res = send({
                "action": protocol.ACTIONS["purchase_request"],
                "data": {
                    "user_id": uid,
                    "file_id": fid,
                    "token": self.app.session.get("token")
                }
            })
            if not res.get("ok"):
                messagebox.showerror("Lỗi", res.get("error"))
                return

            messagebox.showinfo("OTP", "Mã OTP đã được gửi đến email!")

            win = tk.Toplevel(self)
            win.title("Xác nhận mua hàng")
            win.geometry("480x380")
            win.configure(bg=COLORS["cream"])
            win.resizable(False, False)
            win.grab_set()

            shadow = tk.Frame(win, bg="#e0e0e0")
            shadow.place(relx=0.5, rely=0.5, anchor="center", width=444, height=344)
            
            card = tk.Frame(win, bg=COLORS["white"])
            card.place(relx=0.5, rely=0.5, anchor="center", width=440, height=340)

            header = tk.Frame(card, bg=COLORS["green"], height=55)
            header.pack(fill="x")
            header.pack_propagate(False)
            
            tk.Label(header, text="🔐  Nhập mã OTP", font=("Segoe UI", 13, "bold"),
                    bg=COLORS["green"], fg="white").pack(pady=15)

            content = tk.Frame(card, bg=COLORS["white"])
            content.pack(fill="both", expand=True, padx=40, pady=30)

            tk.Label(content, text="NHẬP MÃ OTP 6 CHỮ SỐ", font=("Segoe UI", 12, "bold"),
                    bg=COLORS["white"], fg=COLORS["text"]).pack(pady=(15, 5))
            
            tk.Label(content, text="ĐỂ MUA FILE", font=("Segoe UI", 12, "bold"),
                    bg=COLORS["white"], fg=COLORS["text"]).pack(pady=(0, 30))

            otp_outer = tk.Frame(content, bg="#9370db", relief="flat", bd=2)
            otp_outer.pack(pady=(0, 30))
            
            e_otp = tk.Entry(otp_outer, font=("Segoe UI", 15), justify="center", width=22, relief="flat",
                           bg=COLORS["white"], fg=COLORS["text"], bd=0)
            e_otp.pack(padx=3, pady=3, ipady=10)
            e_otp.focus()

            def confirm():
                otp = e_otp.get().strip()
                if not otp:
                    messagebox.showwarning("Lỗi", "Nhập mã OTP!", parent=win)
                    return
                try:
                    res2 = send({
                        "action": protocol.ACTIONS["purchase_confirm"], 
                        "data": {
                            "user_id": uid,
                            "file_id": fid,
                            "otp": otp,
                            "token": self.app.session.get("token")
                        }
                    })
                    if res2.get("ok"):
                        win.destroy()
                        messagebox.showinfo("THÀNH CÔNG", f"Mua hàng thành công!\n{info['filename']}")
                        
                        self.refresh_all()
                        
                        save = filedialog.asksaveasfilename(initialfile=info['filename'], defaultextension=".pdf")
                        if save:
                            stored = info.get('stored_path', '')
                            download_paths = [stored, f"pending/{info['filename']}", f"approved/{info['filename']}", 
                                           f"downloads/{info['filename']}", info['filename']]
                            download_paths = list(set(p for p in download_paths if p))
                            
                            downloaded = False
                            for dpath in download_paths:
                                try:
                                    if download(dpath, save):
                                        messagebox.showinfo("OK", f"Đã lưu tại:\n{save}")
                                        downloaded = True
                                        break
                                except: pass
                                    
                            if not downloaded:
                                messagebox.showerror("Lỗi tải xuống", "Không thể tải sau khi mua")
                        self.refresh_all()
                    else:
                        messagebox.showerror("Sai OTP", res2.get("error"), parent=win)
                except Exception as e:
                    messagebox.showerror("Lỗi", str(e))

            btn_confirm = SoftButton(content, "Xác nhận", confirm, bg_color=COLORS["green"], width=360, height=45)
            btn_confirm.pack()
            
            e_otp.bind("<Return>", lambda e: confirm())

        except Exception as e:
            messagebox.showerror("Lỗi mạng", str(e))


if __name__ == "__main__":
    App().mainloop()