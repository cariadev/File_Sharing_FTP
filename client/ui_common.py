import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel, Canvas, Scrollbar
from PIL import Image, ImageTk

# ============================= LIGHT MODERN THEME =============================
PALETTE = {
    "bg": "#f8f9fd",              # Nền chính - xanh nhạt tinh tế
    "panel": "#ffffff",            # Panel trắng tinh
    "card": "#ebf0ff",             # Card màu xanh nhạt
    "text": "#1a2332",             # Text đậm dễ đọc
    "muted": "#64748b",            # Text phụ
    "accent": "#6366f1",           # Indigo hiện đại
    "accent_hover": "#4f46e5",     # Hover đậm hơn
    "good": "#10b981",             # Xanh lá tươi
    "good_hover": "#059669",       
    "bad": "#ef4444",              # Đỏ cảnh báo
    "border": "#e2e8f0",           # Viền nhẹ
    "shadow": "#cbd5e1",           # Bóng mờ
}
