# client/pdf_preview.py – BẢN HOÀN HẢO, KHÔNG BỊ TRẮNG, ĐẸP MƯỢT
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import tkinter as tk
import os
def render_first_pages(pdf_path: str, pages: int = 3, zoom: float = 2.0) -> list:
    """
    Render 3 trang đầu của PDF → trả về list[PhotoImage]
    zoom = 2.0 → đẹp, rõ nét trên màn hình Full HD
    """
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"[PDF] Không tìm thấy file: {pdf_path}")
        return []

    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            doc.close()
            return []

        images = []
        render_pages = min(pages, doc.page_count)

        for page_num in range(render_pages):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(zoom, zoom)  # Zoom cao → đẹp
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Chuyển sang PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize nếu quá to (tránh lag + lỗi canvas)
            max_width = 800
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Chuyển thành PhotoImage và giữ reference trong list
            photo = ImageTk.PhotoImage(img)
            images.append(photo)
        
        doc.close()
        print(f"[PDF] Render thành công {len(images)} trang từ {pdf_path}")
        return images

    except Exception as e:
        print(f"[PDF] Lỗi render PDF {pdf_path}: {e}")
        import traceback
        traceback.print_exc()
        return []