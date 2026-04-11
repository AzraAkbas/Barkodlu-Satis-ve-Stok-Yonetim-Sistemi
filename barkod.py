import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import sqlite3
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from reportlab.graphics.shapes import Drawing
from reportlab.lib.enums import TA_CENTER
import customtkinter as ctk
from reportlab.graphics.barcode import createBarcodeDrawing
import tempfile
import webbrowser
import os
import time
import random
import reportlab.pdfbase.pdfdoc
import hashlib
import reportlab.pdfbase.pdfdoc

# Yeni Kütüphane Eklendi
import pandas as pd

# ReportLab MD5 hatası için yama
try:
    # Python 3.9+ için usedforsecurity parametresi desteklenir
    # Python 3.8 ve altı için bu parametreyi kaldırmamız gerekiyor
    if hasattr(hashlib, 'md5'):
        original_md5 = hashlib.md5


        def patched_md5(*args, **kwargs):
            if 'usedforsecurity' in kwargs:
                kwargs.pop('usedforsecurity')
            return original_md5(*args, **kwargs)


        hashlib.md5 = patched_md5

        # ReportLab'in iç kullanımı için de yamalıyoruz
        reportlab.pdfbase.pdfdoc.md5 = patched_md5
except Exception:
    pass
# ReportLab için font kayıtları
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Fontları bir kez kaydetmek için global değişkenler
DEFAULT_PDF_FONT_NAME = 'TurkishFont'
BOLD_PDF_FONT_NAME = 'TurkishFont-Bold'
PDF_FONT_REGISTERED = False
PDF_BOLD_FONT_REGISTERED = False


def register_pdf_fonts():
    global PDF_FONT_REGISTERED, PDF_BOLD_FONT_REGISTERED

    if PDF_FONT_REGISTERED:
        return

    try:
        pdfmetrics.registerFont(TTFont(DEFAULT_PDF_FONT_NAME, 'DejaVuSans.ttf'))
        PDF_FONT_REGISTERED = True
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont(DEFAULT_PDF_FONT_NAME, 'C:\\Windows\\Fonts\\arial.ttf'))
            PDF_FONT_REGISTERED = True
        except Exception as font_e:
            pass


class BarcodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Barkod Uygulaması - BALIKESİR ENGİN İNŞ. SAN. VE TİC. LTD.ŞTİ.")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        self.root.geometry(f"{screen_width}x{screen_height - 70}+0+0")

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.conn = sqlite3.connect('products.db')
        self.cursor = self.conn.cursor()
        self.create_table()

        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15, fg_color="#ff8c00")
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=5)

        self.main_frame.columnconfigure(0, weight=7)
        self.main_frame.columnconfigure(1, weight=3)
        self.main_frame.rowconfigure(0, weight=1)

        self.left_panel_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, border_width=1, border_color="#e5e7eb")
        self.left_panel_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=20)
        self.left_panel_frame.grid_propagate(False)
        self.left_panel_frame.configure(width=530)

        self.right_panel_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, border_width=1, border_color="#e5e7eb")
        self.right_panel_frame.grid(row=0, column=1, sticky="ns", padx=10, pady=5)
        self.right_panel_frame.grid_propagate(False)
        self.right_panel_frame.configure(width=900)

        self.create_product_input_section(self.left_panel_frame)
        self.create_cart_section(self.right_panel_frame)

        self.cart_items = []
        self.calculate_total()

        self.in_place_edit_entry = None
        self.editing_item_barkod = None
        self.editing_column = None
        self.cart_entry_widgets = {}

        self.hide_results_after_focus_out_job = None

        self.product_list_window_instance = None
        self.product_list_search_entry = None
        self.products_tree = None
        self.edit_entry = None

        register_pdf_fonts()
        self.barkod_entry.focus_set()

    def create_table(self):
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS products
                            (
                                barkod
                                TEXT
                                PRIMARY
                                KEY,
                                urun_adi
                                TEXT
                                UNIQUE,
                                fiyat
                                REAL,
                                adet
                                INTEGER
                            )
                            ''')
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS sales
                            (
                                sale_id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                sale_date
                                TEXT,
                                total_amount
                                REAL
                            )
                            ''')
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS sale_items
                            (
                                item_id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                sale_id
                                INTEGER,
                                barkod
                                TEXT,
                                urun_adi
                                TEXT,
                                fiyat
                                REAL,
                                adet
                                INTEGER,
                                FOREIGN
                                KEY
                            (
                                sale_id
                            ) REFERENCES sales
                            (
                                sale_id
                            )
                                )
                            ''')
        self.conn.commit()

    def set_entry_text(self, entry_widget, text):
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, text)

    def create_product_input_section(self, parent_frame):
        ctk.CTkLabel(parent_frame, text="💳 Barkod:", font=("Segoe UI", 18)).grid(row=0, column=0, padx=15, pady=10,
                                                                                 sticky="w")
        self.barkod_entry = ctk.CTkEntry(parent_frame, placeholder_text="Barkod Girin", font=("Segoe UI", 20),
                                         height=40)
        self.barkod_entry.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        self.barkod_entry.bind("<Return>", self.search_and_add_product)

        ctk.CTkLabel(parent_frame, text="🍬 Ürün Adı:", font=("Segoe UI", 18)).grid(row=1, column=0, padx=15, pady=10,
                                                                                   sticky="w")
        self.urun_adi_entry = ctk.CTkEntry(parent_frame, placeholder_text="Ürün Adı", font=("Segoe UI", 20), height=40)
        self.urun_adi_entry.grid(row=1, column=1, padx=15, pady=10, sticky="ew")
        self.urun_adi_entry.bind("<KeyRelease>", self.on_urun_adi_key_release)
        self.urun_adi_entry.bind("<FocusOut>", self.on_urun_adi_focus_out)
        self.urun_adi_entry.bind("<FocusIn>", self.on_urun_adi_focus_in)
        self.urun_adi_entry.bind("<Return>", self.add_selected_product_from_dropdown_to_cart)
        self.urun_adi_entry.bind("<Down>", self.focus_search_results_listbox)

        self.search_results_listbox = tk.Listbox(parent_frame, height=7, selectmode="browse", exportselection=False,
                                                 bg="white", font=("Segoe UI", 18))
        self.search_results_listbox.bind("<Double-1>", self.add_selected_product_from_dropdown_to_cart)
        self.search_results_listbox.bind("<Return>", self.add_selected_product_from_dropdown_to_cart)
        self.search_results_listbox.bind("<FocusOut>", self.on_search_listbox_focus_out)
        self.search_results_listbox.bind("<Up>", self.focus_urun_adi_entry)

        ctk.CTkLabel(parent_frame, text="💵 Fiyat:", font=("Segoe UI", 18)).grid(row=3, column=0, padx=15, pady=10,
                                                                                sticky="w")
        self.fiyat_entry = ctk.CTkEntry(parent_frame, placeholder_text="Fiyat", font=("Segoe UI", 20), height=40)
        self.fiyat_entry.grid(row=3, column=1, padx=15, pady=10, sticky="ew")
        self.fiyat_entry.configure(state="readonly")

        ctk.CTkLabel(parent_frame, text="🚚 Stok Adet:", font=("Segoe UI", 18)).grid(row=4, column=0, padx=15, pady=10,
                                                                                    sticky="w")
        self.bulunan_adet_entry = ctk.CTkEntry(parent_frame, placeholder_text="Stok Adedi", font=("Segoe UI", 20),
                                               height=40)
        self.bulunan_adet_entry.grid(row=4, column=1, padx=15, pady=10, sticky="ew")
        self.bulunan_adet_entry.configure(state="readonly")

        self.barcode_print_button = ctk.CTkButton(parent_frame, text="📄 Barkod Üret",
                                                  command=self.generate_barcodes_and_open_pdf, fg_color="#483d8b",
                                                  hover_color="#6a5acd", font=("Segoe UI", 22), height=45)
        self.barcode_print_button.grid(row=5, column=0, columnspan=2, padx=15, pady=15, sticky="ew")


        self.list_all_products_button = ctk.CTkButton(parent_frame, text="📊 Tüm Ürünleri Listele",
                                                      command=self.show_all_products_window,fg_color="#9370db",hover_color="#8a2be2", font=("Segoe UI", 22),
                                                      height=45)
        self.list_all_products_button.grid(row=6, column=0, columnspan=2, padx=15, pady=15, sticky="ew")

        # <<< YENİ EXCEL BUTONU BAŞLANGIÇ >>>
        self.export_excel_button = ctk.CTkButton(parent_frame, text="💾 Tüm Ürünleri Excel'e Kaydet",
                                                 command=self.save_all_products_to_excel, fg_color="#3cb371",
                                                 hover_color="#059669", font=("Segoe UI", 22), height=45)
        self.export_excel_button.grid(row=12, column=0, columnspan=2, padx=15, pady=40, sticky="ew")
        # <<< YENİ EXCEL BUTONU SONU >>>


        parent_frame.grid_columnconfigure(1, weight=1)
        parent_frame.grid_rowconfigure(9, weight=1)

        self.search_results_listbox.item_data = {}

    def create_cart_section(self, parent_frame):
        # KRİTİK DEĞİŞİKLİK: parent_frame'e bir sütun daha ekleniyor (Kaydırma çubuğu için)
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(1, weight=0)  # Scrollbar için ayrılmış sütun

        # Yeni satır düzenlemesi (indexler değişti)
        parent_frame.grid_rowconfigure(0, weight=0)  # Başlık (Satış Sepeti)
        parent_frame.grid_rowconfigure(1, weight=0)  # Başlıklar için çerçeve (Header Frame)
        parent_frame.grid_rowconfigure(2, weight=8)  # Kanvas için
        parent_frame.grid_rowconfigure(3, weight=0)  # H Scrollbar
        parent_frame.grid_rowconfigure(4, weight=0)  # Toplam
        parent_frame.grid_rowconfigure(5, weight=0)  # Buton 1
        parent_frame.grid_rowconfigure(6, weight=0)  # Buton 2
        parent_frame.grid_rowconfigure(7, weight=0)  # Copyright

        ctk.CTkLabel(parent_frame, text="🛒 Satış Sepeti", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, pady=5,
                                                                                              columnspan=2)

        # Başlıkları kaydırma alanının dışına sabitlemek için yeni çerçeve
        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 0), columnspan=2)

        headers = ["Ürün Adı", "Fiyat", "Adet", "Tutar", "İşlemler"]

        # 🚨 KRİTİK DÜZELTME: Sütun genişlikleri pixel olarak sabitleniyor.
        column_weights = [0, 0, 0, 0, 0]
        # Sabit genişlikler (px cinsinden) - Toplam genişlik 880px
        self.cart_column_widths = [490, 150, 150, 150, 150]

        for i, header_text in enumerate(headers):
            header_label = ctk.CTkLabel(header_frame, text=header_text, font=("Segoe UI", 16, "bold"),
                                        fg_color="#e0e0e0", corner_radius=5)
            header_label.grid(row=0, column=i, sticky="nsew", padx=1, pady=1, ipady=5)

            # BAŞLIK ÇERÇEVESİNE SABİT GENİŞLİK AYARLANIYOR
            header_frame.grid_columnconfigure(i, weight=0, minsize=self.cart_column_widths[i])

        # Sepet canvas'ını (row=2'de)
        self.cart_canvas = ctk.CTkCanvas(parent_frame, borderwidth=0, highlightthickness=0, bg="#f9fafb", height=400)
        self.cart_vscrollbar = ctk.CTkScrollbar(parent_frame, orientation="vertical", command=self.cart_canvas.yview)
        self.cart_hscrollbar = ctk.CTkScrollbar(parent_frame, orientation="horizontal", command=self.cart_canvas.xview)
        self.cart_canvas.configure(yscrollcommand=self.cart_vscrollbar.set, xscrollcommand=self.cart_hscrollbar.set)

        self.cart_canvas.grid(row=2, column=0, sticky="nsew", padx=15, pady=5, columnspan=2)

        # Horizontal Scrollbar konumu
        self.cart_hscrollbar.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 5), columnspan=2)

        self.cart_inner_frame = ctk.CTkFrame(self.cart_canvas, fg_color="#f9fafb")

        # Kanvas içinde pencereyi oluştur. Bu pencerenin kimliğini (ID) saklıyoruz.
        self.canvas_window = self.cart_canvas.create_window((0, 0), window=self.cart_inner_frame, anchor="nw")

        # Inner Frame'in de ağırlıklarını 0 yap.
        for i, weight in enumerate(column_weights):
            self.cart_inner_frame.grid_columnconfigure(i, weight=0)

        # Kanvas her yeniden boyutlandırıldığında, iç çerçeveyi (cart_inner_frame) de genişlet.
        # Genişlik, check_cart_scrollbar içinde hesaplanacaktır.
        self.cart_canvas.bind('<Configure>',
                              lambda e: (
                                  self.cart_canvas.configure(scrollregion=self.cart_canvas.bbox("all")),
                                  self.check_cart_scrollbar()
                              )
                              )

        self.cart_canvas.bind_all("<MouseWheel>", self._on_cart_mouse_wheel)

        # Alt kısımlar
        bottom_cart_frame = ctk.CTkFrame(parent_frame)
        bottom_cart_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=5, columnspan=2)

        bottom_cart_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bottom_cart_frame, text="Toplam Tutar:", font=("Segoe UI", 32, "bold")).grid(row=0, column=0,
                                                                                                  padx=10, sticky="w")
        self.total_amount_var = ctk.StringVar(value="0.00")
        self.total_amount_entry = ctk.CTkEntry(bottom_cart_frame, textvariable=self.total_amount_var, state="readonly",
                                               font=("Segoe UI", 32, "bold"))
        self.total_amount_entry.grid(row=0, column=1, padx=10, sticky="ew")

        ctk.CTkButton(parent_frame, text="✅ Satışı Tamamla", command=self.complete_sale, fg_color="#6495ed",
                      hover_color="#4169e1", font=("Segoe UI", 26, "bold"), height=40).grid(row=5, column=0,
                                                                                            sticky="ew",
                                                                                            padx=30, pady=5,
                                                                                            columnspan=2)
        ctk.CTkButton(parent_frame, text="📄 Satış Özeti PDF", command=self.save_cart_as_pdf, fg_color="#ff6347",
                      hover_color="#ff0000",
                      font=("Segoe UI", 22, "bold"),
                      height=40).grid(row=6, column=0, sticky="ew", padx=30, pady=5, columnspan=2)

        self.company_name_label = ctk.CTkLabel(parent_frame,
                                               text="COPYRIGHT © 2025 - Azra AKBAŞ, Tüm Hakları Saklıdır.",
                                               font=("Segoe UI", 14, "italic"), text_color="#6b7280")
        self.company_name_label.grid(row=7, column=0, sticky="se", padx=15, pady=0, columnspan=2)
    def _on_cart_mouse_wheel(self, event):
        self.cart_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def is_valid_barcode(self, barcode):
        # Tüm barkodları kabul et (harf, rakam, özel karakter içerebilir)
        # Sadece boş olmamasını kontrol et
        return bool(barcode and barcode.strip())

    def search_and_add_product(self, event=None):
        barkod = self.barkod_entry.get().strip()
        self.barkod_entry.delete(0, tk.END)

        if not barkod:
            messagebox.showwarning("Uyarı", "Lütfen bir barkod girin veya okutun.")
            return

        if not self.is_valid_barcode(barkod):
            messagebox.showerror("Hata", "Geçersiz barkod formatı. Barkod boş olamaz.")
            self.barkod_entry.focus_set()
            return

        self.cursor.execute("SELECT * FROM products WHERE barkod=?", (barkod,))
        product = self.cursor.fetchone()

        if product:
            self.set_entry_text(self.urun_adi_entry, product[1])

            self.fiyat_entry.configure(state="normal")
            self.set_entry_text(self.fiyat_entry, f"{product[2]:.2f}")
            self.fiyat_entry.configure(state="readonly")

            self.bulunan_adet_entry.configure(state="normal")
            self.set_entry_text(self.bulunan_adet_entry, str(product[3]))
            self.bulunan_adet_entry.configure(state="readonly")

            self.add_product_to_cart_from_input(product[0], product[1], product[2], 1)
            # Burada clear_left_panel zaten çağrılacak
        else:
            self.open_new_product_window(barkod)

        self.hide_search_results()
    def on_urun_adi_key_release(self, event=None):
        search_term = self.urun_adi_entry.get().strip()

        if self.hide_results_after_focus_out_job:
            self.root.after_cancel(self.hide_results_after_focus_out_job)
            self.hide_results_after_focus_out_job = None

        if search_term and event and event.keysym not in ("Up", "Down", "Return", "Escape", "Tab"):
            self.search_products_by_name(search_term)
        elif not search_term:
            self.hide_search_results()

    def on_urun_adi_focus_in(self, event=None):
        if self.hide_results_after_focus_out_job:
            self.root.after_cancel(self.hide_results_after_focus_out_job)
            self.hide_results_after_focus_out_job = None

        search_term = self.urun_adi_entry.get().strip()
        if search_term:
            self.search_products_by_name(search_term)
        else:
            self.hide_search_results()

    def search_products_by_name(self, search_term):
        self.search_results_listbox.delete(0, tk.END)
        self.search_results_listbox.item_data = {}

        if not search_term:
            self.hide_search_results()
            return

        self.cursor.execute("SELECT barkod, urun_adi, fiyat, adet FROM products WHERE urun_adi LIKE ? COLLATE NOCASE",
                            ('%' + search_term + '%',))
        results = self.cursor.fetchall()

        for product in results:
            urun_adi_display = product[1]
            self.search_results_listbox.insert(tk.END, urun_adi_display)
            self.search_results_listbox.item_data[urun_adi_display] = {
                "barkod": product[0],
                "urun_adi": product[1],
                "fiyat": product[2],
                "adet": product[3]
            }

        if results:
            self.show_search_results()
        else:
            self.hide_search_results()

    def show_search_results(self):
        if not self.search_results_listbox.grid_info():
            self.search_results_listbox.grid(row=2, column=0, columnspan=2, padx=15, pady=0, sticky="ew")
            self.root.update_idletasks()

    def hide_search_results(self):
        if self.search_results_listbox.grid_info():
            self.search_results_listbox.grid_forget()
            self.root.update_idletasks()

    def on_urun_adi_focus_out(self, event=None):
        if self.root.focus_get() == self.search_results_listbox:
            return
        self.hide_results_after_focus_out_job = self.root.after(200, self.hide_search_results)

    def on_search_listbox_focus_out(self, event=None):
        if self.root.focus_get() != self.urun_adi_entry:
            self.hide_search_results()

    def focus_search_results_listbox(self, event=None):
        if self.search_results_listbox.size() > 0 and self.search_results_listbox.grid_info():
            self.search_results_listbox.focus_set()
            self.search_results_listbox.selection_set(0)

    def focus_urun_adi_entry(self, event=None):
        self.urun_adi_entry.focus_set()

    def add_selected_product_from_dropdown_to_cart(self, event=None):
        selected_index = None
        if event and event.keysym == "Return":
            selected_indices = self.search_results_listbox.curselection()
            if selected_indices:
                selected_index = selected_indices[0]
        elif event and event.type == tk.EventType.ButtonPress:
            selected_index = self.search_results_listbox.nearest(event.y)

        if selected_index is None:
            messagebox.showinfo("Bilgi", "Seçili ürün yok. Lütfen listeden bir ürün seçin veya yeni ürün ekleyin.")
            return

        selected_urun_adi_display = self.search_results_listbox.get(selected_index)
        product_data = self.search_results_listbox.item_data.get(selected_urun_adi_display)

        if product_data:
            barkod = product_data["barkod"]
            urun_adi = product_data["urun_adi"]
            fiyat = product_data["fiyat"]
            adet = product_data["adet"]

            self.barkod_entry.delete(0, tk.END)
            self.set_entry_text(self.urun_adi_entry, urun_adi)

            self.fiyat_entry.configure(state="normal")
            self.set_entry_text(self.fiyat_entry, f"{fiyat:.2f}")
            self.fiyat_entry.configure(state="readonly")

            self.bulunan_adet_entry.configure(state="normal")
            self.set_entry_text(self.bulunan_adet_entry, str(adet))
            self.bulunan_adet_entry.configure(state="readonly")

            self.add_product_to_cart_from_input(barkod, urun_adi, fiyat, 1)
            # Burada clear_left_panel zaten çağrılacak
        self.hide_search_results()
    def add_product_to_cart_from_input(self, barkod, urun_adi, fiyat, quantity):
        if not barkod or not urun_adi or not fiyat or not quantity:
            messagebox.showerror("Hata", "Ürün bilgileri eksik. Sepete eklenemedi.")
            return

        self.cursor.execute("SELECT adet FROM products WHERE barkod=?", (barkod,))
        available_stock = self.cursor.fetchone()

        if available_stock:
            current_in_cart_qty = 0
            for item in self.cart_items:
                if item["barkod"] == barkod:
                    current_in_cart_qty = item["adet"]
                    break

            if available_stock[0] < (quantity + current_in_cart_qty):
                messagebox.showerror("Stok Yetersiz",
                                     f"Stokta sadece {available_stock[0]} adet mevcut. Sepetinizde bu üründen {current_in_cart_qty} adet var. Eklemek istediğiniz {quantity} adet ile toplam {quantity + current_in_cart_qty} adet olur ki bu stoktan fazladır.")
                return
        else:
            messagebox.showerror("Hata",
                                 "Ürün veritabanında bulunamadı. Lütfen önce 'Yeni Ürün Ekle' butonu ile ürünü ekleyiniz.")
            return

        self.add_to_cart_logic(barkod, urun_adi, fiyat, quantity)

        # SOL TARAFI BOŞALT
        self.clear_left_panel()

    def clear_left_panel(self):
        """Sol paneldeki tüm alanları temizle"""
        self.barkod_entry.delete(0, tk.END)
        self.urun_adi_entry.delete(0, tk.END)

        self.fiyat_entry.configure(state="normal")
        self.fiyat_entry.delete(0, tk.END)
        self.fiyat_entry.configure(state="readonly")

        self.bulunan_adet_entry.configure(state="normal")
        self.bulunan_adet_entry.delete(0, tk.END)
        self.bulunan_adet_entry.configure(state="readonly")

        # Arama sonuçlarını da gizle
        self.hide_search_results()

        # Barkod alanına focus et
        self.barkod_entry.focus_set()
    def add_to_cart_logic(self, barkod, urun_adi, fiyat, adet):
        found = False
        for item in self.cart_items:
            if item["barkod"] == barkod:
                item["adet"] += adet
                found = True
                break
        if not found:
            self.cart_items.append({"barkod": barkod, "urun_adi": urun_adi, "fiyat": fiyat, "adet": adet})

        self.update_cart_display()
        self.calculate_total()

    def update_cart_display(self):
        # Önceki ürün widget'larını temizle
        for widget in self.cart_inner_frame.winfo_children():
            widget.destroy()

        self.cart_entry_widgets = {}

        # Sabit genişlikler (px cinsinden) - Toplam genişlik 880px
        column_widths = [390, 120, 120, 130, 90]

        row_num = 0
        for item in self.cart_items:
            barkod = item["barkod"]
            urun_adi = item["urun_adi"]
            fiyat = item["fiyat"]
            adet = item["adet"]
            total_price_for_item = fiyat * adet

            # Sütun 0: Ürün Adı - Sabit genişlik
            # Uzun ürün adlarını kısaltmak için
            if len(urun_adi) > 35:  # Yaklaşık 35 karakterden uzunsa
                display_urun_adi = urun_adi[:32] + "..."  # İlk 32 karakter + "..."
            else:
                display_urun_adi = urun_adi

            urun_adi_label = ctk.CTkLabel(self.cart_inner_frame, text=display_urun_adi, font=("Segoe UI", 22),
                                          fg_color="white",
                                          corner_radius=0, anchor="w", width=column_widths[0])
            urun_adi_label.grid(row=row_num, column=0, sticky="nsew", padx=1, pady=1, ipady=2)

            # Tooltip (isteğe bağlı) - fare üzerine gelince tam adı göster
            def create_tooltip(widget, text):
                def show_tooltip(event):
                    tooltip = tk.Toplevel()
                    tooltip.wm_overrideredirect(True)
                    tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
                    label = tk.Label(tooltip, text=text, background="yellow", relief='solid', borderwidth=1)
                    label.pack()
                    widget.tooltip = tooltip

                def hide_tooltip(event):
                    if hasattr(widget, 'tooltip') and widget.tooltip:
                        widget.tooltip.destroy()
                        widget.tooltip = None

                widget.bind("<Enter>", show_tooltip)
                widget.bind("<Leave>", hide_tooltip)

            # Eğer ürün adı kısaltıldıysa tooltip ekle
            if len(urun_adi) > 35:
                create_tooltip(urun_adi_label, urun_adi)

            # Sütun 1: Fiyat - Sabit genişlik
            fiyat_entry = ctk.CTkEntry(self.cart_inner_frame, font=("Segoe UI", 26), fg_color="white", corner_radius=0,
                                       border_width=0, justify='center', width=column_widths[1])
            fiyat_entry.insert(0, f"{fiyat:.2f}")
            fiyat_entry.grid(row=row_num, column=1, sticky="nsew", padx=1, pady=1, ipady=2)
            fiyat_entry.bind("<ButtonRelease-1>",
                             lambda e, b=barkod, col="fiyat", entry=fiyat_entry: self.on_cart_cell_click(e, b, col,
                                                                                                         entry))
            fiyat_entry.bind("<Return>",
                             lambda e, b=barkod, col="fiyat", entry=fiyat_entry: self.save_inline_cart_edit(e, b, col,
                                                                                                            entry))
            fiyat_entry.bind("<FocusOut>",
                             lambda e, b=barkod, col="fiyat", entry=fiyat_entry: self.save_inline_cart_edit(e, b, col,
                                                                                                            entry))

            # Sütun 2: Adet - Sabit genişlik
            adet_entry = ctk.CTkEntry(self.cart_inner_frame, font=("Segoe UI", 26), fg_color="white", corner_radius=0,
                                      border_width=0, justify='center', width=column_widths[2])
            adet_entry.insert(0, str(adet))
            adet_entry.grid(row=row_num, column=2, sticky="nsew", padx=1, pady=1, ipady=2)
            adet_entry.bind("<ButtonRelease-1>",
                            lambda e, b=barkod, col="adet", entry=adet_entry: self.on_cart_cell_click(e, b, col, entry))
            adet_entry.bind("<Return>",
                            lambda e, b=barkod, col="adet", entry=adet_entry: self.save_inline_cart_edit(e, b, col,
                                                                                                         entry))
            adet_entry.bind("<FocusOut>",
                            lambda e, b=barkod, col="adet", entry=adet_entry: self.save_inline_cart_edit(e, b, col,
                                                                                                         entry))

            # Sütun 3: Tutar - Sabit genişlik
            tutar_label = ctk.CTkLabel(self.cart_inner_frame, text=f"{total_price_for_item:.2f} TL",
                                       font=("Segoe UI", 26), fg_color="white", corner_radius=0, justify='center',
                                       width=column_widths[3])
            tutar_label.grid(row=row_num, column=3, sticky="nsew", padx=1, pady=1, ipady=2)

            # Sütun 4: İşlemler (Sil Butonu) - Sabit genişlik
            delete_button = ctk.CTkButton(self.cart_inner_frame, text="Sil",
                                          command=lambda b=barkod: self.remove_item_from_cart(b), font=("Segoe UI", 22),
                                          height=30, fg_color="#ef4444", hover_color="#b91c1c",
                                          width=column_widths[4])
            delete_button.grid(row=row_num, column=4, sticky="nsew", padx=5, pady=1)

            self.cart_entry_widgets[barkod] = {
                "fiyat_entry": fiyat_entry,
                "adet_entry": adet_entry,
                "tutar_label": tutar_label
            }
            row_num += 1

        # İç çerçevenin sütun ağırlıklarını sıfırla ve sabit genişlik ayarla
        for i, width in enumerate(column_widths):
            self.cart_inner_frame.grid_columnconfigure(i, weight=0, minsize=width)

        # Gerekli güncellemeleri yap
        self.cart_inner_frame.update_idletasks()
        self.cart_canvas.configure(scrollregion=self.cart_canvas.bbox("all"))

        # Kaydırma çubuğunun görünürlüğünü ve iç çerçeve genişliğini kontrol et
        self.check_cart_scrollbar()
    def check_cart_scrollbar(self):
        """Sepet içeriği kanvas alanını aşıyorsa dikey kaydırma çubuğunu gösterir ve görünümü ayarlar."""

        # UI güncellemelerinin tamamlanmasını sağla
        self.cart_inner_frame.update_idletasks()
        self.cart_canvas.update_idletasks()

        # İç çerçeve yüksekliği
        inner_height = self.cart_inner_frame.winfo_reqheight()
        # Kanvas görünür yüksekliği
        canvas_height = self.cart_canvas.winfo_height()

        # Kaydırma çubuğunun genişliği (0 veya mevcut genişlik)
        scrollbar_width = self.cart_vscrollbar.winfo_width() if self.cart_vscrollbar.winfo_ismapped() else 0

        # Eğer içerik yüksekliği, kanvas yüksekliğinden büyükse (Taşma var)
        if inner_height > canvas_height:
            if not self.cart_vscrollbar.winfo_ismapped():
                # Kaydırma çubuğunu göster
                # Scrollbar'ı ana çerçevede (parent_frame) 1. sütunda gridliyoruz
                self.cart_vscrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 15), pady=5)

            self.root.update_idletasks()
            scrollbar_width = self.cart_vscrollbar.winfo_width()

            # Kaydırma aralığını ayarla
            self.cart_canvas.configure(scrollregion=self.cart_canvas.bbox("all"))
            # İç çerçeve genişliği = Kanvas Genişliği - Scrollbar Genişliği
            self.cart_canvas.itemconfigure(self.canvas_window, width=self.cart_canvas.winfo_width() - scrollbar_width)

        # Eğer içerik yüksekliği, kanvas yüksekliğinden küçük veya eşitse (Taşma yok)
        else:
            if self.cart_vscrollbar.winfo_ismapped():
                # Kaydırma çubuğunu gizle
                self.cart_vscrollbar.grid_forget()

            # Kanvası en üste sıfırla
            self.cart_canvas.yview_moveto(0)

            # İç çerçeve genişliğini kaydırma çubuğu olmadan ayarla
            # Bu, iç çerçeveyi kanvasın tam genişliğine ayarlar.
            self.cart_canvas.itemconfigure(self.canvas_window, width=self.cart_canvas.winfo_width())

            # Kaydırma aralığını içeriğin yüksekliği kadar ayarla
            scrollregion_bbox = self.cart_canvas.bbox("all")
            if scrollregion_bbox:
                new_scrollregion = (scrollregion_bbox[0], scrollregion_bbox[1],
                                    scrollregion_bbox[2], max(canvas_height, inner_height))
                self.cart_canvas.configure(scrollregion=new_scrollregion)

        self.root.update_idletasks()
    def calculate_total(self):
        total = sum(item["fiyat"] * item["adet"] for item in self.cart_items)
        self.total_amount_var.set(f"{total:.2f}")

    def generate_barcodes_and_open_pdf(self):
        num_barcodes_str = simpledialog.askstring("Barkod PDF", "Kaç adet barkod oluşturmak istersiniz?",
                                                  parent=self.root)
        if not num_barcodes_str:
            return

        try:
            num_barcodes = int(num_barcodes_str)
            if num_barcodes <= 0 or num_barcodes > 100:
                messagebox.showwarning("Geçersiz Sayı", "Lütfen 1 ile 100 arasında bir sayı girin.")
                return
        except ValueError:
            messagebox.showwarning("Hatalı Giriş", "Sayısal bir değer girin.")
            return

        # Benzersiz bir başlangıç noktası oluştur
        # Zaman damgası ve rastgele sayı kullanarak
        base_seed = int(time.time() * 1000) % 1000000
        random.seed(base_seed)
        start_point = random.randint(0, 999999999 - num_barcodes)

        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Barkod Etiketleri", styles['h1']))
        elements.append(Paragraph(f"Üretim Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))

        barcodes_per_row = 3
        barcode_bar_height = 0.5 * inch
        cell_width = 2.8 * inch

        table_data = []
        row = []

        for i in range(num_barcodes):
            # Her seferinde farklı bir seri numarası
            serial = str(start_point + i).zfill(9)
            barcode_number = "868" + serial

            if not barcode_number.isdigit() or len(barcode_number) != 12:
                continue

            barcode_drawing = createBarcodeDrawing('EAN13', value=barcode_number, barHeight=barcode_bar_height,
                                                   humanReadable=True)
            drawing = Drawing(cell_width, barcode_bar_height + 0.3 * inch)
            drawing.add(barcode_drawing)

            text = barcode_number
            style = styles['Normal']
            style.alignment = TA_CENTER
            para = Paragraph(text, style)

            block = [drawing, para, Spacer(1, 0.1 * inch)]
            row.append(block)

            if len(row) == barcodes_per_row:
                table_data.append(row)
                row = []

        if row:
            while len(row) < barcodes_per_row:
                row.append("")
            table_data.append(row)

        col_widths = [cell_width] * barcodes_per_row
        barcode_table = Table(table_data, colWidths=col_widths)
        barcode_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        elements.append(barcode_table)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            doc = SimpleDocTemplate(tmp_file.name, pagesize=landscape(A4))
            doc.build(elements)

        try:
            if os.name == 'nt':
                os.startfile(tmp_file.name)
            elif os.name == 'posix':
                webbrowser.open(f"file://{tmp_file.name}")
        except Exception as e:
            messagebox.showerror("Açma Hatası", f"PDF açılırken hata oluştu:\n{e}")

    # <<< YENİ METOT BAŞLANGIÇ >>>
    def save_all_products_to_excel(self):
        """Tüm ürünleri veritabanından çeker ve Excel dosyasına kaydeder."""
        try:
            # Tüm ürünleri çek
            self.cursor.execute("SELECT barkod, urun_adi, fiyat, adet FROM products ORDER BY urun_adi ASC")
            all_products = self.cursor.fetchall()

            if not all_products:
                messagebox.showwarning("Uyarı", "Veritabanında kaydedilecek ürün bulunmamaktadır.")
                return

            # Pandas DataFrame oluştur
            df = pd.DataFrame(all_products, columns=['Barkod', 'Ürün Adı', 'Fiyat (TL)', 'Stok Adedi'])

            # Kayıt yolu seçimi için dosya iletişim kutusunu aç
            # Varsayılan dosya adı ve uzantısı belirtiliyor
            default_filename = f"Urun_Listesi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile=default_filename,
                filetypes=[("Excel dosyaları", "*.xlsx")],
                title="Tüm Ürünleri Kaydet"
            )

            if not file_path:
                messagebox.showinfo("İptal Edildi", "Excel'e kaydetme işlemi iptal edildi.")
                return

            # Excel dosyasına kaydet
            df.to_excel(file_path, index=False)

            messagebox.showinfo("Başarılı",
                                f"Tüm ürünler başarıyla Excel dosyasına kaydedildi:\n{file_path}",
                                parent=self.root)

        except ImportError:
            messagebox.showerror("Hata",
                                 "Bu özellik için 'pandas' ve 'openpyxl' kütüphaneleri gereklidir. Lütfen terminalde 'pip install pandas openpyxl' komutunu çalıştırın.",
                                 parent=self.root)
        except Exception as e:
            messagebox.showerror("Hata", f"Excel dosyasına kaydederken bir hata oluştu: {e}", parent=self.root)
    # <<< YENİ METOT SONU >>>

    def get_product_stock(self, barkod):
        self.cursor.execute("SELECT adet FROM products WHERE barkod=?", (barkod,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def on_cart_cell_click(self, event, barkod, col_name, entry_widget):
        if self.in_place_edit_entry and self.in_place_edit_entry.winfo_exists():
            self.save_inline_cart_edit(None, self.editing_item_barkod, self.editing_column, self.in_place_edit_entry)

        self.in_place_edit_entry = entry_widget
        self.editing_item_barkod = barkod
        self.editing_column = col_name
        entry_widget.focus_set()
        entry_widget.select_range(0, tk.END)

    def save_inline_cart_edit(self, event, barkod, column, entry_widget):
        if event and event.type == tk.EventType.FocusOut and self.root.focus_get() == entry_widget:
            return

        if event and event.keysym == "Escape":
            self.cancel_inline_cart_edit()
            return

        new_value_str = entry_widget.get().strip()

        try:
            if column == "adet":
                new_value = int(new_value_str)
                if new_value < 0:
                    messagebox.showerror("Hata", "Adet negatif olamaz.")
                    entry_widget.focus_set()
                    return
            elif column == "fiyat":
                new_value = float(new_value_str.replace(',', '.'))
                if new_value < 0:
                    messagebox.showerror("Hata", "Fiyat negatif olamaz.")
                    entry_widget.focus_set()
                    return
            else:
                return

            for item in self.cart_items:
                if item["barkod"] == barkod:
                    if column == "adet":
                        self.cursor.execute("SELECT adet FROM products WHERE barkod=?", (barkod,))
                        available_stock = self.cursor.fetchone()

                        if available_stock and new_value > available_stock[0]:
                            messagebox.showerror("Stok Yetersiz",
                                                 f"Stokta sadece {available_stock[0]} adet mevcut. Girdiğiniz miktar ({new_value}) stoktan fazla.")
                            entry_widget.focus_set()
                            return

                    item[column] = new_value
                    break

            if column == "adet" and new_value == 0:
                self.remove_item_from_cart(barkod)
                messagebox.showinfo("Bilgi", f"Ürün sepetten kaldırıldı: {barkod}")
            else:
                self.update_cart_display()
                self.calculate_total()

        except ValueError:
            messagebox.showerror("Hata", "Geçersiz değer. Lütfen sayısal bir değer girin.")
            entry_widget.focus_set()
            return
        except Exception as e:
            messagebox.showerror("Hata", f"Değer güncellenirken bir hata oluştu: {e}")
            entry_widget.focus_set()
            return
        finally:
            self.in_place_edit_entry = None
            self.editing_item_barkod = None
            self.editing_column = None

    def cancel_inline_cart_edit(self):
        if self.in_place_edit_entry and self.in_place_edit_entry.winfo_exists():
            self.in_place_edit_entry.destroy()
        self.in_place_edit_entry = None
        self.editing_item_barkod = None
        self.editing_column = None
        self.root.focus_set()

    def remove_item_from_cart(self, barkod):
        item_to_remove = None
        for item in self.cart_items:
            if item["barkod"] == barkod:
                item_to_remove = item
                break

        if item_to_remove:
            confirm = messagebox.askyesno("Onay",
                                          f"'{item_to_remove['urun_adi']}' ürününü sepetten tamamen kaldırmak istediğinizden emin misiniz? ",
                                          parent=self.product_list_window_instance)
            if confirm:
                self.cart_items = [item for item in self.cart_items if item["barkod"] != barkod]
                self.update_cart_display()
                self.calculate_total()
        else:
            messagebox.showerror("Hata", "Kaldırılacak ürün sepette bulunamadı.")

    def complete_sale(self):
        if not self.cart_items:
            messagebox.showwarning("Boş Sepet", "Sepetinizde ürün bulunmamaktadır. Satış yapılamaz.")
            return

        confirm = messagebox.askyesno("Satış Onayı", "Satışı tamamlamak istediğinizden emin misiniz?")
        if confirm:
            try:
                sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                total_amount = sum(item["fiyat"] * item["adet"] for item in self.cart_items)
                self.cursor.execute("INSERT INTO sales (sale_date, total_amount) VALUES (?, ?)",
                                    (sale_date, total_amount))
                sale_id = self.cursor.lastrowid

                for item in self.cart_items:
                    barkod = item["barkod"]
                    urun_adi = item["urun_adi"]
                    fiyat = item["fiyat"]
                    adet_to_deduct = item["adet"]

                    self.cursor.execute(
                        "INSERT INTO sale_items (sale_id, barkod, urun_adi, fiyat, adet) VALUES (?, ?, ?, ?, ?)",
                        (sale_id, barkod, urun_adi, fiyat, adet_to_deduct))
                    self.update_stock(barkod, -adet_to_deduct)

                self.conn.commit()

                self.cart_items = []
                self.update_cart_display()
                self.calculate_total()

                self.barkod_entry.delete(0, tk.END)
                self.urun_adi_entry.delete(0, tk.END)
                self.fiyat_entry.configure(state="normal")
                self.fiyat_entry.delete(0, tk.END)
                self.fiyat_entry.configure(state="readonly")
                self.bulunan_adet_entry.configure(state="normal")
                self.bulunan_adet_entry.delete(0, tk.END)
                self.bulunan_adet_entry.configure(state="readonly")

                messagebox.showinfo("Satış Tamamlandı", "Satış başarıyla tamamlandı.")
                self.barkod_entry.focus_set()

            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Satış Hatası", f"Satış sırasında bir hata oluştu: {e}. İşlemler geri alındı.")
        else:
            messagebox.showinfo("Satış İptal Edildi", "Satış işlemi iptal edildi.")

    def save_cart_as_pdf(self, clear_after_save=False):
        if not self.cart_items:
            messagebox.showwarning("Boş Sepet", "PDF olarak kaydedilecek ürün bulunmamaktadır.")
            return

        elements = []
        try:
            if not PDF_FONT_REGISTERED:
                register_pdf_fonts()
            if not PDF_FONT_REGISTERED:
                return

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='NormalTurkish', parent=styles['Normal'], fontName=DEFAULT_PDF_FONT_NAME,
                                      fontSize=12, leading=14))
            styles.add(
                ParagraphStyle(name='H1Turkish', parent=styles['h1'], fontName=DEFAULT_PDF_FONT_NAME, fontSize=20,
                               leading=28))

            if PDF_BOLD_FONT_REGISTERED:
                styles.add(
                    ParagraphStyle(name='BoldTurkishParagraph', parent=styles['Normal'], fontName=BOLD_PDF_FONT_NAME,
                                   fontSize=12, leading=18, spaceAfter=8, spaceBefore=8))
            else:
                styles.add(
                    ParagraphStyle(name='BoldTurkishParagraph', parent=styles['Normal'], fontName=DEFAULT_PDF_FONT_NAME,
                                   fontSize=12, leading=18, spaceAfter=8, spaceBefore=8))

            company_name_full = self.root.title().split(" - ")[
                1] if " - " in self.root.title() else "BALIKESİR ENGİN İNŞ. SAN. VE TİC. LTD.ŞTİ."
            elements.append(Paragraph(company_name_full, styles['H1Turkish']))
            elements.append(Paragraph("Satış Özeti", styles['H1Turkish']))
            elements.append(
                Paragraph(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", styles['NormalTurkish']))
            elements.append(Spacer(1, 0.2 * inch))

            data = [['Ürün Adı', 'Fiyat', 'Adet', 'Tutar']]
            for item in self.cart_items:
                total_price_for_item = item["fiyat"] * item["adet"]
                data.append([
                    Paragraph(item["urun_adi"], styles['NormalTurkish']),
                    Paragraph(f"{item['fiyat']:.2f} TL", styles['NormalTurkish']),
                    Paragraph(str(item["adet"]), styles['NormalTurkish']),
                    Paragraph(f"{total_price_for_item:.2f} TL", styles['NormalTurkish'])
                ])

            total_amount = sum(item["fiyat"] * item["adet"] for item in self.cart_items)
            data.append([Paragraph("GENEL TOPLAM:", styles['BoldTurkishParagraph']), '', '',
                         Paragraph(f"{total_amount:.2f} TL", styles['BoldTurkishParagraph'])])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0),
                 BOLD_PDF_FONT_NAME if PDF_BOLD_FONT_REGISTERED else DEFAULT_PDF_FONT_NAME),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 1), (-1, -1), DEFAULT_PDF_FONT_NAME),
                ('FONTNAME', (2, -1), (3, -1),
                 BOLD_PDF_FONT_NAME if PDF_BOLD_FONT_REGISTERED else DEFAULT_PDF_FONT_NAME),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                doc = SimpleDocTemplate(tmp_file.name, pagesize=A4)
                doc.build(elements)

            try:
                if os.name == 'nt':
                    os.startfile(tmp_file.name)
                elif os.name == 'posix':
                    webbrowser.open(f"file://{tmp_file.name}")
            except Exception as e:
                messagebox.showerror("Açma Hatası", f"PDF açılırken hata oluştu:\n{e}")

            messagebox.showinfo("PDF Oluşturuldu", "Satış özeti başarıyla oluşturuldu ve açıldı.")
            if clear_after_save:
                self.cart_items = []
                self.update_cart_display()
                self.calculate_total()
                self.barkod_entry.focus_set()

        except Exception as e:
            messagebox.showerror("PDF Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")

    def open_new_product_window(self, barkod_value):
        new_product_window = ctk.CTkToplevel(self.root)
        new_product_window.title("Yeni Ürün Ekle/Düzenle")
        new_product_window.transient(self.root)
        new_product_window.grab_set()
        new_product_window.geometry("500x350")

        ctk.CTkLabel(new_product_window, text="Barkod:", font=("Segoe UI", 16)).grid(row=0, column=0, padx=10, pady=8,
                                                                                     sticky="w")
        barkod_entry = ctk.CTkEntry(new_product_window, placeholder_text="Barkod", font=("Segoe UI", 14), height=30)
        barkod_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        barkod_entry.insert(0, barkod_value)
        barkod_entry.configure(state="readonly")

        ctk.CTkLabel(new_product_window, text="Ürün Adı:", font=("Segoe UI", 16)).grid(row=1, column=0, padx=10, pady=8,
                                                                                       sticky="w")
        urun_adi_entry = ctk.CTkEntry(new_product_window, placeholder_text="Ürün Adını Girin", font=("Segoe UI", 14),
                                      height=30)
        urun_adi_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        urun_adi_entry.focus_set()

        ctk.CTkLabel(new_product_window, text="Fiyat:", font=("Segoe UI", 16)).grid(row=2, column=0, padx=10, pady=8,
                                                                                    sticky="w")
        fiyat_entry = ctk.CTkEntry(new_product_window, placeholder_text="Fiyat", font=("Segoe UI", 14), height=30)
        fiyat_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(new_product_window, text="Stok Adet:", font=("Segoe UI", 16)).grid(row=3, column=0, padx=10,
                                                                                        pady=8, sticky="w")
        adet_entry = ctk.CTkEntry(new_product_window, placeholder_text="Stok Adedi", font=("Segoe UI", 14), height=30)
        adet_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")

        save_button = ctk.CTkButton(new_product_window, text="Kaydet/Güncelle",
                                    command=lambda: self.save_product(new_product_window, barkod_entry.get(),
                                                                      urun_adi_entry.get(), fiyat_entry.get(),
                                                                      adet_entry.get()), font=("Segoe UI", 16),
                                    height=40)
        save_button.grid(row=4, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

        new_product_window.grid_columnconfigure(1, weight=1)

    def save_product(self, window, barkod, urun_adi, fiyat_str, adet_str):
        if not barkod or not urun_adi or not fiyat_str or not adet_str:
            messagebox.showerror("Hata", "Tüm alanlar dolu olmalıdır!", parent=window)
            return

        urun_adi_cleaned = urun_adi.strip()
        if not urun_adi_cleaned:
            messagebox.showerror("Hata", "Ürün adı boş olamaz!", parent=window)
            return

        self.cursor.execute("SELECT barkod FROM products WHERE urun_adi = ? AND barkod != ?",
                            (urun_adi_cleaned, barkod))
        duplicate_name_product = self.cursor.fetchone()
        if duplicate_name_product:
            messagebox.showerror("Hata",
                                 f"Bu ürün adı zaten mevcut. Lütfen benzersiz bir ürün adı girin.\nÇakışan Barkod: '{duplicate_name_product[0]}'",
                                 parent=window)
            return

        try:
            fiyat = float(fiyat_str.replace(',', '.'))
            adet = int(adet_str)
            if adet < 0:
                messagebox.showerror("Hata", "Adet negatif olamaz.", parent=window)
                return
        except ValueError:
            messagebox.showerror("Hata", "Fiyat ve stok adedi sayısal değer olmalıdır.", parent=window)
            return

        try:
            self.cursor.execute("SELECT * FROM products WHERE barkod = ?", (barkod,))
            existing_product = self.cursor.fetchone()

            if existing_product:
                self.cursor.execute("UPDATE products SET urun_adi=?, fiyat=?, adet=? WHERE barkod=?",
                                    (urun_adi_cleaned, fiyat, adet, barkod))
                messagebox.showinfo("Başarılı", f"'{urun_adi_cleaned}' ürünü başarıyla güncellendi!", parent=window)

                for item in self.cart_items:
                    if item["barkod"] == barkod:
                        item["urun_adi"] = urun_adi_cleaned
                        item["fiyat"] = fiyat
                        break
                self.update_cart_display()
                self.calculate_total()
            else:
                self.cursor.execute("INSERT INTO products (barkod, urun_adi, fiyat, adet) VALUES (?, ?, ?, ?)",
                                    (barkod, urun_adi_cleaned, fiyat, adet))
                messagebox.showinfo("Başarılı", f"'{urun_adi_cleaned}' ürünü başarıyla kaydedildi!", parent=window)

            self.conn.commit()

            self.barkod_entry.delete(0, tk.END)
            self.urun_adi_entry.delete(0, tk.END)
            self.fiyat_entry.configure(state="normal")
            self.fiyat_entry.delete(0, tk.END)
            self.fiyat_entry.configure(state="readonly")
            self.bulunan_adet_entry.configure(state="normal")
            self.bulunan_adet_entry.delete(0, tk.END)
            self.bulunan_adet_entry.configure(state="readonly")
            window.destroy()
            self.barkod_entry.focus_set()

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: products.urun_adi" in str(e):
                messagebox.showerror("Hata", "Bu ürün adı zaten mevcut. Lütfen benzersiz bir ürün adı girin.",
                                     parent=window)
            else:
                messagebox.showerror("Hata", f"Ürün kaydedilirken bir veritabanı hatası oluştu: {e}", parent=window)
        except Exception as e:
            messagebox.showerror("Hata", f"Ürün kaydedilirken beklenmedik bir hata oluştu: {e}", parent=window)

    def update_stock(self, barkod, quantity_change):
        self.cursor.execute("UPDATE products SET adet = adet + ? WHERE barkod = ?", (quantity_change, barkod))
        self.conn.commit()

    def show_all_products_window(self):
        print("DEBUG: show_all_products_window çağrıldı")
        if self.product_list_window_instance and self.product_list_window_instance.winfo_exists():
            print("DEBUG: Pencere zaten açık, lift ediliyor")
            self.product_list_window_instance.lift()
            return

        print("DEBUG: Yeni pencere oluşturuluyor")
        product_list_window = ctk.CTkToplevel(self.root)
        product_list_window.title("Tüm Ürünleri Listele (Enter ile Kaydet, ESC ile İptal)")
        product_list_window.transient(self.root)
        product_list_window.geometry("800x600")

        # Pencere protokolünü ayarla - sadece bir kez
        product_list_window.protocol("WM_DELETE_WINDOW",
                                     lambda: self.on_product_list_close(product_list_window))

        self.product_list_window_instance = product_list_window

        search_frame = ctk.CTkFrame(product_list_window, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=10)

        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(search_frame, text="Barkod/Ürün Ara:", font=("Segoe UI", 16)).grid(row=0, column=0, padx=5, pady=5,
                                                                                        sticky="w")
        self.product_list_search_entry = ctk.CTkEntry(search_frame, placeholder_text="Barkod veya Ürün Adına Göre Ara",
                                                      font=("Segoe UI", 14))
        self.product_list_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.product_list_search_entry.bind("<KeyRelease>", self.search_products_in_list_window)

        delete_button = ctk.CTkButton(search_frame, text="🗑️ Seçiliyi Sil", command=self.delete_product_from_list_grid,
                                      font=("Segoe UI", 14, "bold"), height=30, fg_color="#ef4444",
                                      hover_color="#b91c1c", width=120)
        delete_button.grid(row=0, column=2, padx=5, pady=5)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", font=("Segoe UI", 14), rowheight=35, fieldbackground="white", background="white",
                        foreground="black", bordercolor="#e5e7eb", borderwidth=1)
        style.map('Treeview', background=[('selected', '#3b82f6')])
        style.configure("Treeview.Heading", font=("Segoe UI", 16, "bold"), background="#e0e0e0", foreground="black")

        columns = ("urun_adi", "fiyat", "adet")
        self.products_tree = ttk.Treeview(product_list_window, columns=columns, show="headings tree")

        self.products_tree.heading("#0", text="Barkod", anchor=tk.W)
        self.products_tree.heading("urun_adi", text="Ürün Adı", anchor=tk.W)
        self.products_tree.heading("fiyat", text="Fiyat", anchor=tk.E)
        self.products_tree.heading("adet", text="Stok Adet", anchor=tk.E)

        self.products_tree.column("#0", width=150, minwidth=150, anchor=tk.W)
        self.products_tree.column("urun_adi", width=300, minwidth=200, anchor=tk.W)
        self.products_tree.column("fiyat", width=120, minwidth=100, anchor=tk.E)
        self.products_tree.column("adet", width=120, minwidth=100, anchor=tk.E)

        vscrollbar = ctk.CTkScrollbar(product_list_window, orientation="vertical", command=self.products_tree.yview)
        hscrollbar = ctk.CTkScrollbar(product_list_window, orientation="horizontal", command=self.products_tree.xview)
        self.products_tree.configure(yscrollcommand=vscrollbar.set, xscrollcommand=hscrollbar.set)

        vscrollbar.pack(side="right", fill="y", padx=(0, 5), pady=(0, 5))
        hscrollbar.pack(side="bottom", fill="x", padx=5, pady=(0, 5))
        self.products_tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.products_tree.bind('<Double-1>', self.on_treeview_double_click)
        self.products_tree.bind('<<TreeviewSelect>>', self.on_treeview_select)

        # Destroy event'ini kaldır, sadece WM_DELETE_WINDOW kullan
        # product_list_window.bind("<Destroy>", lambda e: self.on_product_list_close(product_list_window))

        self.edit_entry = None
        self.populate_product_list_grid()

        print("DEBUG: Pencere oluşturma tamamlandı")

    def debug_focus_out(self, event):
        print(f"DEBUG: FocusOut - event: {event}, focus: {self.root.focus_get()}")

    def debug_destroy(self, event):
        print(f"DEBUG: Destroy - event: {event}")

    def on_treeview_select(self, event):
        print("DEBUG: Treeview select")
        if self.edit_entry and self.edit_entry.winfo_exists():
            print("DEBUG: Edit entry var, kaydetmeye çalışıyor")
            self.save_inline_edit(event=None)

    def populate_product_list_grid(self, search_term=""):
        print(f"DEBUG: populate_product_list_grid - search_term: '{search_term}'")
        if self.products_tree:
            self.products_tree.delete(*self.products_tree.get_children())

        if search_term:
            self.cursor.execute(
                "SELECT * FROM products WHERE urun_adi LIKE ? COLLATE NOCASE OR barkod LIKE ? ORDER BY urun_adi ASC",
                ('%' + search_term + '%', '%' + search_term + '%'))
        else:
            self.cursor.execute("SELECT * FROM products ORDER BY urun_adi ASC")

        all_products = self.cursor.fetchall()

        for product in all_products:
            barkod = product[0]
            urun_adi = product[1]
            fiyat = product[2]
            adet = product[3]

            self.products_tree.insert("", tk.END, iid=barkod, text=barkod, values=(urun_adi, f"{fiyat:.2f}", adet))

    def on_treeview_double_click(self, event):
        print("DEBUG: Treeview double click")
        if self.edit_entry and self.edit_entry.winfo_exists():
            print("DEBUG: Önceki edit entry var, kaydediliyor")
            self.save_inline_edit(event=None)

        region = self.products_tree.identify('region', event.x, event.y)
        print(f"DEBUG: Region: {region}")
        if region != 'cell':
            return

        selected_item = self.products_tree.identify_row(event.y)
        print(f"DEBUG: Selected item: {selected_item}")
        if not selected_item:
            return

        column = self.products_tree.identify_column(event.x)
        column_map = {'#0': 'barkod', '#1': 'urun_adi', '#2': 'fiyat', '#3': 'adet'}
        col_name = column_map.get(column)
        print(f"DEBUG: Column: {column}, col_name: {col_name}")

        if col_name not in ['urun_adi', 'fiyat', 'adet']:
            print("DEBUG: Düzenlenemez sütun")
            return

        bbox = self.products_tree.bbox(selected_item, column)
        print(f"DEBUG: Bbox: {bbox}")
        if not bbox:
            return

        x, y, width, height = bbox

        print("DEBUG: Edit entry oluşturuluyor")
        self.edit_entry = tk.Entry(self.products_tree, font=("Segoe UI", 14), bd=0, highlightthickness=1,
                                   highlightbackground="#3b82f6")

        if column == '#0':
            current_value = self.products_tree.item(selected_item, 'text')
        else:
            current_value = self.products_tree.item(selected_item, 'values')[int(column.replace('#', '')) - 1]

        self.edit_entry.insert(0, current_value)
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.place(x=x, y=y, width=width, height=height)

        self.edit_entry.barkod = selected_item
        self.edit_entry.col_name = col_name
        self.edit_entry.tree_column = column

        # DEBUG: Tüm olayları izle
        self.edit_entry.bind("<FocusIn>", self.debug_edit_focus_in)
        self.edit_entry.bind("<FocusOut>", self.on_edit_focus_out)  # Değişti
        self.edit_entry.bind("<Key>", self.debug_edit_key)

        self.edit_entry.bind("<Return>", self.save_inline_edit)
        self.edit_entry.bind("<Escape>", self.cancel_inline_edit)

        self.edit_entry.focus_set()
        print("DEBUG: Edit entry oluşturuldu ve focus edildi")

    def debug_edit_focus_in(self, event):
        print(f"DEBUG: Edit FocusIn - event: {event}")

    def on_edit_focus_out(self, event):
        print(f"DEBUG: Edit FocusOut - event: {event}, focus: {self.root.focus_get()}")

        # Eğer edit entry artık yoksa, işlem yapma
        if not self.edit_entry or not self.edit_entry.winfo_exists():
            print("DEBUG: Edit entry yok, işlem yapılmıyor")
            return

        # Eğer focus hala aynı penceredeyse veya treeview'daysa, kaydetme
        current_focus = self.root.focus_get()
        if (current_focus == self.edit_entry or
                current_focus == self.products_tree or
                (self.product_list_window_instance and
                 self.product_list_window_instance.winfo_exists() and
                 self.is_widget_in_window(current_focus, self.product_list_window_instance))):
            print("DEBUG: Focus hala aynı pencere içinde, kaydetmiyor")
            return

        # Eğer focus başka bir pencereye geçtiyse kaydet
        print("DEBUG: Focus başka pencereye geçti, kaydediliyor")
        self.save_inline_edit(event)

    def is_widget_in_window(self, widget, window):
        """Widget'ın belirtilen pencere içinde olup olmadığını kontrol et"""
        try:
            current = widget
            while current:
                if current == window:
                    return True
                current = current.master
            return False
        except:
            return False
    def debug_edit_key(self, event):
        print(f"DEBUG: Edit Key - keysym: {event.keysym}, char: {event.char}")

    def cancel_inline_edit(self, event=None):
        print("DEBUG: cancel_inline_edit çağrıldı")
        if self.edit_entry and self.edit_entry.winfo_exists():
            print("DEBUG: Edit entry yok ediliyor")
            self.edit_entry.destroy()
        self.edit_entry = None
        print("DEBUG: Edit entry None yapıldı")

    def save_inline_edit(self, event=None):
        print(f"DEBUG: save_inline_edit çağrıldı - event: {event}")
        if not self.edit_entry or not self.edit_entry.winfo_exists():
            print("DEBUG: Edit entry yok veya mevcut değil")
            return

        if event and event.keysym == "Escape":
            print("DEBUG: Escape tuşu, iptal ediliyor")
            self.cancel_inline_edit()
            return

        # Eğer event FocusOut ise ve focus hala aynı penceredeyse, kaydetme
        if (event and hasattr(event, 'type') and event.type == tk.EventType.FocusOut and
                self.product_list_window_instance and self.product_list_window_instance.winfo_exists()):
            current_focus = self.root.focus_get()
            if current_focus in [self.products_tree, self.product_list_search_entry, self.product_list_window_instance]:
                print("DEBUG: FocusOut ama hala aynı pencerede, kaydetmiyor")
                return

        print("DEBUG: Değer kaydediliyor")
        new_value_str = self.edit_entry.get().strip()
        barkod = self.edit_entry.barkod
        col_name = self.edit_entry.col_name

        print(f"DEBUG: new_value_str: '{new_value_str}', barkod: {barkod}, col_name: {col_name}")

        current_values_text = self.products_tree.item(barkod, 'text')
        current_values_tuple = self.products_tree.item(barkod, 'values')

        new_urun_adi = current_values_tuple[0] if len(current_values_tuple) > 0 else ""
        new_fiyat = float(current_values_tuple[1].replace(',', '.')) if len(current_values_tuple) > 1 and \
                                                                        current_values_tuple[1] else 0.0
        new_adet = int(current_values_tuple[2]) if len(current_values_tuple) > 2 and current_values_tuple[2] else 0

        try:
            if col_name == "urun_adi":
                new_value = new_value_str
                if not new_value:
                    raise ValueError("Ürün adı boş olamaz.")
                new_urun_adi = new_value
            elif col_name == "fiyat":
                new_value = float(new_value_str.replace(',', '.'))
                if new_value < 0:
                    raise ValueError("Fiyat negatif olamaz.")
                new_fiyat = new_value
            elif col_name == "adet":
                new_value = int(new_value_str)
                if new_value < 0:
                    raise ValueError("Stok adedi negatif olamaz.")
                new_adet = new_value
            else:
                self.cancel_inline_edit()
                return
        except ValueError as e:
            messagebox.showerror("Hata", f"Geçersiz değer: {e}", parent=self.product_list_window_instance)
            self.edit_entry.focus_set()
            return

        success, error_message = self._update_product_in_db_logic(barkod, new_urun_adi, new_fiyat, new_adet)

        if not success:
            messagebox.showerror("Kaydetme Hatası", error_message, parent=self.product_list_window_instance)
            self.edit_entry.focus_set()
            return
        else:
            self.products_tree.item(barkod, values=(new_urun_adi, f"{new_fiyat:.2f}", new_adet))

            if self.barkod_entry.get() == barkod:
                self.set_entry_text(self.urun_adi_entry, new_urun_adi)
                self.fiyat_entry.configure(state="normal")
                self.set_entry_text(self.fiyat_entry, f"{new_fiyat:.2f}")
                self.fiyat_entry.configure(state="readonly")
                self.bulunan_adet_entry.configure(state="normal")
                self.set_entry_text(self.bulunan_adet_entry, str(new_adet))
                self.bulunan_adet_entry.configure(state="readonly")

            for item in self.cart_items:
                if item["barkod"] == barkod:
                    item["urun_adi"] = new_urun_adi
                    item["fiyat"] = new_fiyat
                    break
            self.update_cart_display()
            self.calculate_total()

        self.cancel_inline_edit()
        print("DEBUG: Kayıt tamamlandı")

    def search_products_in_list_window(self, event=None):
        if hasattr(self, "_search_after_id"):
            self.root.after_cancel(self._search_after_id)

        self._search_after_id = self.root.after(500, self._perform_search_in_list_window)

    def _perform_search_in_list_window(self):
        search_term = self.product_list_search_entry.get().strip()
        self.populate_product_list_grid(search_term)

    def _update_product_in_db_logic(self, barkod, new_urun_adi, new_fiyat, new_adet):
        try:
            self.cursor.execute("SELECT barkod FROM products WHERE urun_adi = ? AND barkod != ?",
                                (new_urun_adi, barkod))
            duplicate_name_product = self.cursor.fetchone()
            if duplicate_name_product:
                return False, f"'{new_urun_adi}' ürün adı zaten mevcut. Lütfen benzersiz bir ürün adı girin.\nÇakışan Barkod: '{duplicate_name_product[0]}'"

            self.cursor.execute("UPDATE products SET urun_adi=?, fiyat=?, adet=? WHERE barkod=?",
                                (new_urun_adi, new_fiyat, new_adet, barkod))
            self.conn.commit()
            return True, None
        except Exception as e:
            self.conn.rollback()
            return False, f"Veritabanı hatası: {e}"

    def save_all_products_from_grid(self):
        messagebox.showinfo("Bilgi",
                            "Değişiklikler artık hücreye çift tıklayıp Enter'a basıldığında veya odak kaybedildiğinde anında kaydedilmektedir.")
        return

    def delete_product_from_list_grid(self, barkod=None):
        if barkod is None:
            selected_items = self.products_tree.selection()
            if not selected_items:
                messagebox.showwarning("Uyarı", "Lütfen listeden silmek istediğiniz bir ürün seçin.",
                                       parent=self.product_list_window_instance)
                return
            barkod = selected_items[0]

        self.cursor.execute("SELECT urun_adi FROM products WHERE barkod = ?", (barkod,))
        product_name_result = self.cursor.fetchone()

        if not product_name_result:
            messagebox.showerror("Hata", "Silmek istediğiniz ürün veritabanında bulunamadı.")
            if self.products_tree and barkod in self.products_tree.get_children():
                self.products_tree.delete(barkod)
            return

        urun_adi = product_name_result[0]

        confirm = messagebox.askyesno("Silme Onayı",
                                      f"'{urun_adi}' adlı ürünü veritabanından kalıcı olarak silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.",
                                      parent=self.product_list_window_instance)

        if confirm:
            try:
                self.cursor.execute("DELETE FROM products WHERE barkod=?", (barkod,))
                self.conn.commit()
                messagebox.showinfo("Başarılı", f"'{urun_adi}' adlı ürün başarıyla silindi.",
                                    parent=self.product_list_window_instance)

                if self.products_tree and barkod in self.products_tree.get_children():
                    self.products_tree.delete(barkod)

                if self.barkod_entry.get() == barkod:
                    self.barkod_entry.delete(0, tk.END)
                    self.urun_adi_entry.delete(0, tk.END)
                    self.fiyat_entry.configure(state="normal")
                    self.fiyat_entry.delete(0, tk.END)
                    self.fiyat_entry.configure(state="readonly")
                    self.bulunan_adet_entry.configure(state="normal")
                    self.bulunan_adet_entry.delete(0, tk.END)
                    self.bulunan_adet_entry.configure(state="readonly")

                self.cart_items = [item for item in self.cart_items if item["barkod"] != barkod]
                self.update_cart_display()
                self.calculate_total()

            except Exception as e:
                messagebox.showerror("Hata", f"Ürün silinirken bir hata oluştu: {e}",
                                     parent=self.product_list_window_instance)
                self.conn.rollback()

    def on_numpad_close(self):
        pass

    def on_product_list_close(self, window):
        print("DEBUG: on_product_list_close çağrıldı")
        if self.edit_entry and self.edit_entry.winfo_exists():
            print("DEBUG: Edit entry var, iptal ediliyor")
            self.cancel_inline_edit()

        try:
            window.destroy()
        except tk.TclError:
            pass
        finally:
            self.product_list_window_instance = None
            self.products_tree = None
            self.root.focus_set()

    def on_closing(self):
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = ctk.CTk()
    app = BarcodeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()