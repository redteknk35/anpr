import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image, ImageTk, ImageOps, ImageDraw
import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import sqlite3

class HikvisionANPRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Red Güvenlik iDS-2CD7A46G0 Plaka Yönetici Yavuz KULAS")
        self.root.geometry("880x860")
        self.root.minsize(800, 800)

        # --- SQLITE VERİTABANI BAŞLANGICI ---
        self.init_db()

        # Tema Durumu (True: Koyu Tema, False: Açık Tema)
        self.is_dark_theme = True
        self.init_themes()

        # Kök Pencere Arka Planı
        self.root.configure(bg=self.bg_color)
        
        # Tema ve Stil Ayarları
        self.setup_styles()

        # İkon Yükleme
        self.set_app_icon()

        # Aktif başarılı kamera IP'lerini ve ortak değişkenleri önceden tanımla
        self.active_cameras = []
        self.use_date_var = tk.BooleanVar(value=False)
        self.test_mode_active = False

        # --- ÜST MENÜ BUTONLARI (Sekmeler) ---
        frame_top_menu = ttk.Frame(root, padding=5)
        frame_top_menu.pack(fill="x", padx=10, pady=(5, 5))

        self.menu_buttons = {}
        menus = [
            ("Kamera Yönetimi", self.show_camera_management),
            ("Plaka Listesi", self.show_plate_list),
            ("VCA", self.show_vca_test),
            ("Ayarlar", self.show_settings),
            ("Hakkında", self.show_about)
        ]

        for text, cmd in menus:
            btn = ttk.Button(frame_top_menu, text=text, command=cmd)
            btn.pack(side="left", expand=True, fill="x", padx=2)
            self.menu_buttons[text] = btn

        # --- İÇERİK ALANI (Sayfaların yükleneceği ana frame) ---
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True, padx=10, pady=5)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Sayfaları oluştur
        self.frames = {}
        for F in (CameraManagementFrame, PlateListFrame, VCAFrame, SettingsFrame, AboutFrame):
            frame_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Durum Çubuğu
        self.lbl_status = ttk.Label(root, text="Hazır | F11 / F12: Tam Ekran | ESC: Normal Ekran", relief="flat", anchor="w", padding=5)
        self.lbl_status.pack(side="bottom", fill="x")

        # Tam Ekran Kısayol Dinleyicileri
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<F12>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)
        self.is_fullscreen = False

        # Başlangıçta Kamera Yönetimi ekranını aç
        self.show_camera_management()

    def init_db(self):
        """Uygulama klasöründe cameras.db veritabanını ve tablosunu oluşturur."""
        try:
            self.conn = sqlite3.connect("cameras.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port TEXT,
                    user TEXT,
                    password TEXT
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"[VERİTABANI HATA] {e}")

    def show_frame(self, frame_name):
        frame = self.frames[frame_name]
        frame.tkraise()

    def show_camera_management(self):
        self.show_frame("CameraManagementFrame")

    def show_plate_list(self):
        self.show_frame("PlateListFrame")

    def show_vca_test(self):
        self.show_frame("VCAFrame")

    def show_settings(self):
        self.show_frame("SettingsFrame")

    def show_about(self):
        self.show_frame("AboutFrame")

    def init_themes(self):
        if self.is_dark_theme:
            self.bg_color = "#1e1e1e"
            self.fg_color = "#ffffff"
            self.card_bg = "#2d2d30"
            self.input_bg = "#333333"
            self.img_bg_color = "#121212"
            self.img_fg_color = "#888888"
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#000000"
            self.card_bg = "#ffffff"
            self.input_bg = "#ffffff"
            self.img_bg_color = "#e1e1e1"
            self.img_fg_color = "#555555"

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.bg_color, foreground=self.fg_color, fieldbackground=self.input_bg)
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color, bordercolor="#888888")
        style.configure("TLabelframe.Label", background=self.bg_color, foreground="#00adb5" if self.is_dark_theme else "#005f73", font=("Arial", 9, "bold"))
        
        btn_bg = "#3c3c3c" if self.is_dark_theme else "#e0e0e0"
        btn_active = "#505050" if self.is_dark_theme else "#d0d0d0"
        style.configure("TButton", background=btn_bg, foreground=self.fg_color, borderwidth=1, focusthickness=3, focuscolor="none")
        style.map("TButton", background=[('active', btn_active), ('pressed', '#252526' if self.is_dark_theme else '#c0c0c0')])
        
        style.configure("TCheckbutton", background=self.bg_color, foreground=self.fg_color)
        style.map("TCheckbutton", background=[('active', self.bg_color)])

        style.configure("TEntry", fieldbackground=self.input_bg, foreground=self.fg_color, insertcolor=self.fg_color)
        style.configure("TCombobox", fieldbackground=self.input_bg, foreground=self.fg_color)

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.init_themes()
        
        self.root.configure(bg=self.bg_color)
        self.setup_styles()
        
        for frame in self.frames.values():
            if hasattr(frame, "apply_theme"):
                frame.apply_theme()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.root.attributes("-fullscreen", False)

    def set_app_icon(self):
        for filename in ["logo.ico", "logo.png"]:
            if os.path.exists(filename):
                try:
                    img = Image.open(filename)
                    self.app_icon = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, self.app_icon)
                    return
                except Exception:
                    pass

        try:
            img = Image.new('RGBA', (32, 32), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([2, 6, 29, 25], fill="#1F2937", outline="#DC2626", width=2)
            draw.rectangle([6, 11, 25, 20], fill="#DC2626")
            draw.ellipse([12, 12, 19, 19], fill="#FFFFFF")
            
            self.app_icon = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            pass

    def clean_plate(self, plate_str):
        tr_map = str.maketrans("çğışöüÇĞIŞÖÜ", "cgisouCGISOU")
        cleaned = plate_str.translate(tr_map)
        return "".join(c for c in cleaned if c.isalnum()).upper()

# --- 1. KAMERA YÖNETİMİ EKRANI ---
class CameraManagementFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Sol Panel (Kamera Ekleme ve Liste Yönetimi)
        frame_left = ttk.LabelFrame(self, text="Kamera Listesi ve Ekleme", padding=10)
        frame_left.pack(side="left", fill="both", expand=False, padx=(0, 5), pady=5)

        # Girdi Alanları
        frame_form = ttk.Frame(frame_left)
        frame_form.pack(fill="x", pady=(0, 10))

        ttk.Label(frame_form, text="IP Adresi:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_ip = ttk.Entry(frame_form, width=18)
        self.entry_ip.insert(0, "192.168.1.64")
        self.entry_ip.grid(row=0, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(frame_form, text="Port:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_port = ttk.Entry(frame_form, width=18)
        self.entry_port.insert(0, "80")
        self.entry_port.grid(row=1, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(frame_form, text="Kullanıcı Adı:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_user = ttk.Entry(frame_form, width=18)
        self.entry_user.insert(0, "admin")
        self.entry_user.grid(row=2, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(frame_form, text="Şifre:").grid(row=3, column=0, sticky="w", pady=2)
        self.entry_pass = ttk.Entry(frame_form, show="*", width=18)
        self.entry_pass.grid(row=3, column=1, sticky="w", pady=2, padx=5)

        # Ekle / Güncelle Butonları
        frame_form_btns = ttk.Frame(frame_form)
        frame_form_btns.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        self.btn_add_cam = ttk.Button(frame_form_btns, text="➕ Kamera Ekle", command=self.add_or_update_camera)
        self.btn_add_cam.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_cancel_edit = ttk.Button(frame_form_btns, text="İptal", command=self.clear_form, state="disabled")
        self.btn_cancel_edit.pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Kamera Listesi Tablosu (Treeview)
        columns = ("no", "ip", "port", "user", "pass")
        self.tree_cams = ttk.Treeview(frame_left, columns=columns, show="headings", height=8, selectmode="extended")
        self.tree_cams.heading("no", text="No")
        self.tree_cams.heading("ip", text="IP Adresi")
        self.tree_cams.heading("port", text="Port")
        self.tree_cams.heading("user", text="Kullanıcı")
        self.tree_cams.heading("pass", text="Şifre")

        self.tree_cams.column("no", width=45, anchor="center")
        self.tree_cams.column("ip", width=105, anchor="w")
        self.tree_cams.column("port", width=45, anchor="center")
        self.tree_cams.column("user", width=75, anchor="w")
        self.tree_cams.column("pass", width=0, stretch=False)

        # Durum renk tag tanımlamaları
        self.tree_cams.tag_configure("red_led", foreground="#ff4d4d", font=("Arial", 10, "bold"))
        self.tree_cams.tag_configure("green_led", foreground="#2ecc71", font=("Arial", 10, "bold"))

        self.tree_cams.pack(fill="both", expand=True, pady=5)
        self.tree_cams.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Tablo Yönetim Butonları
        frame_table_btns = ttk.Frame(frame_left)
        frame_table_btns.pack(fill="x", pady=(2, 5))

        self.btn_edit_cam = ttk.Button(frame_table_btns, text="✏️ Düzenle", command=self.edit_selected_camera, state="disabled")
        self.btn_edit_cam.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.btn_del_cam = ttk.Button(frame_table_btns, text="🗑️ Sil", command=self.delete_selected_cameras, state="disabled")
        self.btn_del_cam.pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Bağlan / Bağlantıyı Kes Butonları
        self.btn_test = ttk.Button(frame_left, text="Bağlan & Test Et (Seçilenler)", command=self.start_connection_thread)
        self.btn_test.pack(fill="x", pady=(5, 2))

        self.btn_disconnect = ttk.Button(frame_left, text="Bağlantıyı Kes (Seçilenler)", command=self.disconnect_cameras, state="disabled")
        self.btn_disconnect.pack(fill="x", pady=(2, 5))

        self.lbl_conn_status = tk.Label(frame_left, text="● Henüz Bağlanılmadı", bg=controller.card_bg, fg="gray", font=("Arial", 9, "bold"))
        self.lbl_conn_status.pack(pady=5)

        # --- SQLite Veritabanından Kayıtları Yükle ---
        self.load_cameras_from_db()

        # Sağ / Alt Alan: Canlı Önizleme
        self.frame_preview = ttk.LabelFrame(self, text="Canlı Kamera Önizleme", padding=10)
        self.frame_preview.pack(side="right", fill="both", expand=True, pady=5)

        frame_cam_select = ttk.Frame(self.frame_preview)
        frame_cam_select.pack(fill="x", pady=(0, 5))

        ttk.Label(frame_cam_select, text="Önizleme Kamerası:").pack(side="left", padx=(0, 5))
        self.selected_camera_var = tk.StringVar()
        self.combo_cameras = ttk.Combobox(frame_cam_select, textvariable=self.selected_camera_var, state="readonly", width=22)
        self.combo_cameras.pack(side="left", fill="x", expand=True)
        self.combo_cameras.bind("<<ComboboxSelected>>", self.on_camera_selected)

        self.lbl_image = tk.Label(self.frame_preview, text="Görüntü Yok\n(Önce Bağlantı Kurun)", bg=controller.img_bg_color, fg=controller.img_fg_color)
        self.lbl_image.pack(fill="both", expand=True)

        self.editing_item = None

    def apply_theme(self):
        self.lbl_image.config(bg=self.controller.img_bg_color, fg=self.controller.img_fg_color)
        self.lbl_conn_status.config(bg=self.controller.card_bg)

    def load_cameras_from_db(self):
        """Veritabanındaki kameraları okur ve arayüze yükler. Boşsa varsayılan ekler."""
        try:
            self.controller.cursor.execute("SELECT ip, port, user, password FROM cameras")
            rows = self.controller.cursor.fetchall()
            
            if rows:
                for row in rows:
                    ip, port, user, pwd = row
                    new_no = str(len(self.tree_cams.get_children()) + 1)
                    self.tree_cams.insert("", "end", values=(new_no, ip, port, user, pwd), tags=("red_led",))
            else:
                self.tree_cams.insert("", "end", values=("1", "192.168.1.64", "80", "admin", ""), tags=("red_led",))
                self.save_all_cameras_to_db()
                
            self.refresh_camera_numbers()
        except Exception as e:
            print(f"[DB YÜKLEME HATA] {e}")

    def save_all_cameras_to_db(self):
        """Arayüzdeki tüm kameraları veritabanına baştan kaydeder."""
        try:
            self.controller.cursor.execute("DELETE FROM cameras")
            for item in self.tree_cams.get_children():
                vals = self.tree_cams.item(item, "values")
                ip, port, user, pwd = vals[1], vals[2], vals[3], vals[4]
                self.controller.cursor.execute(
                    "INSERT INTO cameras (ip, port, user, password) VALUES (?, ?, ?, ?)",
                    (ip, port, user, pwd)
                )
            self.controller.conn.commit()
        except Exception as e:
            print(f"[DB KAYDETME HATA] {e}")

    def refresh_camera_numbers(self):
        for index, item in enumerate(self.tree_cams.get_children(), start=1):
            vals = self.tree_cams.item(item, "values")
            self.tree_cams.item(item, values=(str(index), vals[1], vals[2], vals[3], vals[4]))

    def clear_form(self):
        self.entry_ip.delete(0, tk.END)
        self.entry_port.delete(0, tk.END)
        self.entry_port.insert(0, "80")
        self.entry_user.delete(0, tk.END)
        self.entry_user.insert(0, "admin")
        self.entry_pass.delete(0, tk.END)
        self.btn_add_cam.config(text="➕ Kamera Ekle")
        self.btn_cancel_edit.config(state="disabled")
        self.editing_item = None

    def add_or_update_camera(self):
        ip = self.entry_ip.get().strip()
        port = self.entry_port.get().strip() or "80"
        user = self.entry_user.get().strip() or "admin"
        pwd = self.entry_pass.get().strip()

        if not ip:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir IP adresi girin.")
            return

        if self.editing_item:
            current_tags = self.tree_cams.item(self.editing_item, "tags")
            current_no = self.tree_cams.item(self.editing_item, "values")[0]
            self.tree_cams.item(self.editing_item, values=(current_no, ip, port, user, pwd), tags=current_tags)
            messagebox.showinfo("Başarılı", "Kamera bilgileri güncellendi.")
            self.clear_form()
        else:
            for item in self.tree_cams.get_children():
                if self.tree_cams.item(item, "values")[1] == ip:
                    messagebox.showwarning("Uyarı", f"{ip} adresi zaten listede mevcut.")
                    return
            new_no = str(len(self.tree_cams.get_children()) + 1)
            self.tree_cams.insert("", "end", values=(new_no, ip, port, user, pwd), tags=("red_led",))
            self.clear_form()
            self.refresh_camera_numbers()

        # Değişiklikleri veritabanına kaydet
        self.save_all_cameras_to_db()

    def on_tree_select(self, event=None):
        selected = self.tree_cams.selection()
        if selected:
            self.btn_edit_cam.config(state="normal")
            self.btn_del_cam.config(state="normal")
            self.btn_disconnect.config(state="normal")
        else:
            self.btn_edit_cam.config(state="disabled")
            self.btn_del_cam.config(state="disabled")
            if not self.controller.active_cameras:
                self.btn_disconnect.config(state="disabled")

    def edit_selected_camera(self):
        selected = self.tree_cams.selection()
        if not selected:
            return
        item = selected[0]
        vals = self.tree_cams.item(item, "values")
        
        self.entry_ip.delete(0, tk.END)
        self.entry_ip.insert(0, vals[1])
        self.entry_port.delete(0, tk.END)
        self.entry_port.insert(0, vals[2])
        self.entry_user.delete(0, tk.END)
        self.entry_user.insert(0, vals[3])
        self.entry_pass.delete(0, tk.END)
        self.entry_pass.insert(0, vals[4])

        self.editing_item = item
        self.btn_add_cam.config(text="💾 Güncelle")
        self.btn_cancel_edit.config(state="normal")

    def delete_selected_cameras(self):
        selected = self.tree_cams.selection()
        if not selected:
            return
        if messagebox.askyesno("Onay", "Seçilen kamera(lar) listeden silinsin mi?"):
            for item in selected:
                self.tree_cams.delete(item)
            self.clear_form()
            self.refresh_camera_numbers()
            self.on_tree_select()
            
            # Değişiklikleri veritabanına kaydet
            self.save_all_cameras_to_db()

    def get_selected_camera_list(self):
        selected = self.tree_cams.selection()
        items = selected if selected else self.tree_cams.get_children()
        
        cameras = []
        for item in items:
            vals = self.tree_cams.item(item, "values")
            cameras.append({
                "item_id": item,
                "ip": vals[1],
                "port": vals[2],
                "user": vals[3],
                "pass": vals[4]
            })
        return cameras

    def start_connection_thread(self):
        cams = self.get_selected_camera_list()
        if not cams:
            messagebox.showwarning("Eksik Bilgi", "Listede işlem yapılacak kamera bulunamadı.")
            return

        self.btn_test.config(state="disabled")
        self.controller.lbl_status.config(text=f"{len(cams)} kameraya bağlanılıyor...")
        threading.Thread(target=self.test_all_connections, args=(cams,), daemon=True).start()

    def disconnect_cameras(self):
        selected_items = self.tree_cams.selection()
        items_to_disconnect = selected_items if selected_items else self.tree_cams.get_children()
        
        disconnected_ips = []
        for item in items_to_disconnect:
            vals = self.tree_cams.item(item, "values")
            ip = vals[1]
            disconnected_ips.append(ip)
            self.tree_cams.item(item, values=(vals[0], vals[1], vals[2], vals[3], vals[4]), tags=("red_led",))

        self.controller.active_cameras = [ip for ip in self.controller.active_cameras if ip not in disconnected_ips]

        self.combo_cameras['values'] = self.controller.active_cameras
        current_preview = self.combo_cameras.get()

        if current_preview in disconnected_ips:
            self.combo_cameras.set('')
            self.lbl_image.config(image='', text="Görüntü Yok\n(Bağlantı Kesildi)")

        if not self.controller.active_cameras:
            self.btn_disconnect.config(state="disabled")
            self.lbl_conn_status.config(text="● Bağlantı Kesildi", fg="gray")
        else:
            if not self.combo_cameras.get():
                self.combo_cameras.set(self.controller.active_cameras[0])
                self.on_camera_selected()
            self.lbl_conn_status.config(text=f"● {len(self.controller.active_cameras)} Aktif", fg="#2ecc71")

        self.controller.lbl_status.config(text=f"Seçilen kameraların bağlantısı kesildi: {', '.join(disconnected_ips)}")

    def test_single_camera(self, cam):
        ip, port, user, pwd = cam["ip"], cam["port"], cam["user"], cam["pass"]
        base_url = f"http://{ip}:{port}" if port else f"http://{ip}"
        
        urls = [
            f"{base_url}/ISAPI/System/deviceInfo",
            f"{base_url}/ISAPI/Security/securityCapabilities"
        ]
        
        for url in urls:
            try:
                res = requests.get(url, auth=HTTPDigestAuth(user, pwd), timeout=4)
                if res.status_code == 200:
                    model_str = "iDS-2CD7A46G0"
                    try:
                        root = ET.fromstring(res.content)
                        model_node = root.find('{http://www.isapi.org/ver20/XMLSchema}model')
                        if model_node is None:
                            model_node = root.find('model')
                        if model_node is not None and model_node.text:
                            model_str = model_node.text.strip()
                    except Exception:
                        pass
                    return True, cam, model_str
                elif res.status_code == 401:
                    return False, cam, "Erişim Engellendi / Hatalı Şifre (401)"
            except Exception:
                continue
        return False, cam, "Erişilemedi (Bağlantı Zaman Aşımı)"

    def test_all_connections(self, cams):
        success_info = []
        failed_cams = []

        with ThreadPoolExecutor(max_workers=len(cams)) as executor:
            futures = [executor.submit(self.test_single_camera, cam) for cam in cams]
            for future in as_completed(futures):
                success, cam, info_or_msg = future.result()
                if success:
                    success_info.append((cam, info_or_msg))
                else:
                    failed_cams.append(f"{cam['ip']}: {info_or_msg}")

        self.after(0, lambda: self.finish_connection_test(success_info, failed_cams, cams))

    def finish_connection_test(self, success_info, failed_cams, cams):
        self.btn_test.config(state="normal")
        success_ips = {cam["ip"] for cam, _ in success_info}
        
        for ip in success_ips:
            if ip not in self.controller.active_cameras:
                self.controller.active_cameras.append(ip)

        for cam in cams:
            item_id = cam["item_id"]
            ip = cam["ip"]
            no, port, user, pwd = self.tree_cams.item(item_id, "values")[0], cam["port"], cam["user"], cam["pass"]
            
            if ip in success_ips:
                self.tree_cams.item(item_id, values=(no, ip, port, user, pwd), tags=("green_led",))

        if self.controller.active_cameras:
            self.combo_cameras['values'] = self.controller.active_cameras
            self.btn_disconnect.config(state="normal")
            
            if not self.combo_cameras.get() and self.controller.active_cameras:
                self.combo_cameras.set(self.controller.active_cameras[0])
                self.on_camera_selected()

            self.lbl_conn_status.config(text=f"● {len(self.controller.active_cameras)} Aktif", fg="#2ecc71")

        if success_info:
            result_msg = "Bağlantı Başarılı (iDS-2CD7A46G0):\n" + "\n".join([f"• {cam['ip']} ({model})" for cam, model in success_info])
            if failed_cams:
                result_msg += "\n\nBaşarısız Kameralar:\n" + "\n".join(failed_cams)
            
            self.controller.lbl_status.config(text=f"Bağlantı Tamamlandı. ({len(success_info)}/{len(cams)} kamera aktif)")
            messagebox.showinfo("Bağlantı Sonucu", result_msg)
        else:
            if not self.controller.active_cameras:
                self.combo_cameras['values'] = []
                self.combo_cameras.set('')
                self.btn_disconnect.config(state="disabled")
                self.lbl_image.config(image='', text="Görüntü Yok\n(Bağlantı Başarısız)")
                self.lbl_conn_status.config(text="● Bağlantı Başarısız", fg="#ff4d4d")
            
            self.controller.lbl_status.config(text="Bağlantı Hatası: Kameralara erişilemedi.")
            messagebox.showerror("Hata", "Seçilen kameralara erişilemedi:\n" + "\n".join(failed_cams))

    def get_camera_credentials(self, ip):
        for item in self.tree_cams.get_children():
            vals = self.tree_cams.item(item, "values")
            if vals[1] == ip:
                return vals[2], vals[3], vals[4]
        return "80", "admin", ""

    def on_camera_selected(self, event=None):
        selected_ip = self.combo_cameras.get()
        if not selected_ip:
            return
        port, user, pwd = self.get_camera_credentials(selected_ip)
        threading.Thread(target=self.load_snapshot_thread, args=(selected_ip, port, user, pwd), daemon=True).start()

    def load_snapshot_thread(self, ip, port, user, pwd):
        base_url = f"http://{ip}:{port}" if port else f"http://{ip}"
        snapshot_url = f"{base_url}/ISAPI/Streaming/channels/101/picture"
        try:
            res = requests.get(snapshot_url, auth=HTTPDigestAuth(user, pwd), timeout=3)
            if res.status_code == 200:
                img_data = io.BytesIO(res.content)
                img = Image.open(img_data)
                target_w, target_h = self.lbl_image.winfo_width(), self.lbl_image.winfo_height()
                if target_w <= 1 or target_h <= 1:
                    target_w, target_h = 320, 200
                img_fitted = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img_fitted)
                self.after(0, lambda: self.update_camera_preview(tk_img, ip))
                return
        except Exception:
            pass
        self.after(0, lambda: self.update_camera_preview(None, ip))

    def update_camera_preview(self, tk_img, ip):
        if tk_img:
            self.lbl_image.config(image=tk_img, text="")
            self.lbl_image.image = tk_img
        else:
            self.lbl_image.config(image="", text=f"Görüntü Alınamadı\n({ip})")


# --- 2. PLAKA LİSTESİ YÖNETİMİ EKRANI ---
class PlateListFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        frame_date = ttk.LabelFrame(self, text="Plaka Geçerlilik Süresi", padding=10)
        frame_date.pack(fill="x", pady=5)

        chk_date = ttk.Checkbutton(frame_date, text="Geçerlilik Tarihi Tanımla", variable=controller.use_date_var, command=self.toggle_date_inputs)
        chk_date.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(frame_date, text="Başlangıç (YYYY-AA-GG):").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_start = ttk.Entry(frame_date, width=15)
        self.entry_start.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.entry_start.grid(row=1, column=1, sticky="w", pady=2, padx=5)

        ttk.Label(frame_date, text="Bitiş (YYYY-AA-GG):").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_end = ttk.Entry(frame_date, width=15)
        self.entry_end.insert(0, "2030-12-31")
        self.entry_end.grid(row=2, column=1, sticky="w", pady=2, padx=5)

        self.toggle_date_inputs()

        frame_plates = ttk.LabelFrame(self, text="İzin Verilen Plakalar (Beyaz Liste - Her satıra 1 plaka)", padding=10)
        frame_plates.pack(fill="both", expand=True, pady=5)

        self.txt_plates = tk.Text(frame_plates, height=10, width=70, bg=controller.input_bg, fg=controller.fg_color, insertbackground=controller.fg_color, relief="flat", font=("Consolas", 10))
        self.txt_plates.pack(fill="both", expand=True)

        frame_file_ops = ttk.Frame(frame_plates)
        frame_file_ops.pack(fill="x", pady=5)

        self.btn_fetch = ttk.Button(frame_file_ops, text="📥 Kameralardaki Mevcut Plakaları Çek", command=self.start_fetch_plates_thread)
        self.btn_fetch.pack(side="left")

        btn_file = ttk.Button(frame_file_ops, text="📂 TXT / CSV Dosyasından Yükle", command=self.load_from_file)
        btn_file.pack(side="right")

        frame_actions = ttk.Frame(self)
        frame_actions.pack(fill="x", pady=5)

        self.btn_upload = ttk.Button(frame_actions, text="Plakaları Kameralara Gönder", command=self.start_upload_plates_thread)
        self.btn_upload.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_clear = ttk.Button(frame_actions, text="⚠️ Kameralardaki Tüm Plakaları Sil", command=self.start_clear_plates_thread)
        self.btn_clear.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def apply_theme(self):
        self.txt_plates.config(bg=self.controller.input_bg, fg=self.controller.fg_color, insertbackground=self.controller.fg_color)

    def toggle_date_inputs(self):
        state = "normal" if self.controller.use_date_var.get() else "disabled"
        self.entry_start.config(state=state)
        self.entry_end.config(state=state)

    def load_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.txt_plates.delete("1.0", tk.END)
                    self.txt_plates.insert(tk.END, f.read())
                self.controller.lbl_status.config(text="Plaka listesi yüklendi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya okunamadı: {str(e)}")

    def start_fetch_plates_thread(self):
        cam_frame = self.controller.frames["CameraManagementFrame"]
        cams = cam_frame.get_selected_camera_list()

        if not cams:
            messagebox.showwarning("Eksik Bilgi", "Lütfen önce Kamera Yönetimi ekranından kamera seçin veya ekleyin.")
            return

        self.btn_fetch.config(state="disabled")
        self.controller.lbl_status.config(text=f"{len(cams)} kameradan plaka verileri çekiliyor...")
        threading.Thread(target=self.fetch_all_camera_plates, args=(cams,), daemon=True).start()

    def fetch_single_camera_plates(self, cam):
        base_url = f"http://{cam['ip']}:{cam['port']}" if cam['port'] else f"http://{cam['ip']}"
        fetched_plates = []
        
        # Filtrelenecek başlık ve gereksiz ifadeler listesi
        ignore_keywords = [
            "effectiveenddate", "effectivestartdate", "group0blocklist", 
            "plateno", "id", "licenseplate", "format"
        ]
        
        url = f"{base_url}/ISAPI/Traffic/channels/1/licensePlateAuditData?fileType=csv"

        try:
            res = requests.get(url, auth=HTTPDigestAuth(cam['user'], cam['pass']), timeout=5)
            if res.status_code == 200:
                csv_content = res.content.decode('utf-8', errors='ignore')
                
                for line in csv_content.splitlines():
                    # Satırı küçük harfe çevirip işle
                    clean_line = line.strip().lower()
                    
                    # Başlık satırlarını ve tamamen gereksiz olanları atla
                    if not line.strip() or any(key in clean_line for key in ignore_keywords):
                        continue
                        
                    # CSV virgül veya noktalı virgül ile ayrılmış olabilir
                    parts = [p.strip().strip('"') for p in line.replace(';', ',').split(',')]
                    
                    for part in parts:
                        clean = self.controller.clean_plate(part)
                        
                        # Temel filtreleme:
                        # 1. En az 5 karakter olsun
                        # 2. Sadece sayılardan oluşmasın (çünkü ID'ler genellikle rakamdır)
                        # 3. Yasaklı kelimeleri içermesin
                        if clean and len(clean) >= 5 and not clean.isdigit():
                            if clean not in fetched_plates:
                                fetched_plates.append(clean)
                                
                if fetched_plates:
                    return True, cam['ip'], fetched_plates
                    
        except Exception as e:
            print(f"[FETCH CSV HATA] IP: {cam['ip']} | Detay: {e}")

        return False, cam['ip'], []

    def fetch_all_camera_plates(self, cams):
        all_plates = set()
        failed_ips = []

        with ThreadPoolExecutor(max_workers=len(cams)) as executor:
            futures = [executor.submit(self.fetch_single_camera_plates, cam) for cam in cams]
            for future in as_completed(futures):
                success, ip, plates = future.result()
                if success:
                    all_plates.update(plates)
                else:
                    failed_ips.append(ip)

        self.after(0, lambda: self.finish_fetch_plates(all_plates, failed_ips))

    def finish_fetch_plates(self, all_plates, failed_ips):
        self.btn_fetch.config(state="normal")
        if all_plates:
            sorted_plates = sorted(list(all_plates))
            self.txt_plates.delete("1.0", tk.END)
            self.txt_plates.insert(tk.END, "\n".join(sorted_plates))
            self.controller.lbl_status.config(text=f"Plakalar çekildi. Toplam: {len(sorted_plates)}")
            messagebox.showinfo("İşlem Başarılı", f"Kameralardan toplam {len(sorted_plates)} benzersiz plaka çekildi.")
        else:
            self.controller.lbl_status.config(text="Plaka çekilemedi veya veritabanı boş.")
            messagebox.showwarning("Sonuç", "Kameralarda kayıtlı plaka bulunamadı ya da uç nokta yanıt vermedi.")

    def start_upload_plates_thread(self):
        cam_frame = self.controller.frames["CameraManagementFrame"]
        cams = cam_frame.get_selected_camera_list()

        if not cams:
            messagebox.showwarning("Eksik Bilgi", "Lütfen önce Kamera Yönetimi ekranından kamera seçin.")
            return

        raw_text = self.txt_plates.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Eksik Bilgi", "Plaka listesi boş.")
            return

        self.btn_upload.config(state="disabled")
        self.controller.lbl_status.config(text=f"Plakalar {len(cams)} kameraya gönderiliyor...")
        threading.Thread(target=self.upload_plates_parallel, args=(cams,), daemon=True).start()

    def upload_plates_parallel(self, cams):
        start_date = self.entry_start.get().strip() if self.controller.use_date_var.get() else "2026-08-14"
        end_date = self.entry_end.get().strip() if self.controller.use_date_var.get() else "2030-12-31"
        raw_text = self.txt_plates.get("1.0", tk.END).strip()
        plates = [self.controller.clean_plate(line) for line in raw_text.splitlines() if line.strip()]

        summary = []
        with ThreadPoolExecutor(max_workers=len(cams)) as executor:
            futures = [executor.submit(self.send_plates_to_single_camera, cam, plates, start_date, end_date) for cam in cams]
            for future in as_completed(futures):
                ip, succ, fail = future.result()
                summary.append(f"Kamera ({ip}): {succ} Başarılı / {fail} Hatalı")

        self.after(0, lambda: self.finish_upload_plates(summary))

    def send_plates_to_single_camera(self, cam, plates, start_date, end_date):
        success_count, fail_count = 0, 0
        base_url = f"http://{cam['ip']}:{cam['port']}" if cam['port'] else f"http://{cam['ip']}"
        headers = {'Content-Type': 'application/json'}

        # Doğrulanmış tam URL uç noktaları (Önce Postman'de test ettiğiniz kayıt endpoint'i denenecek)
        urls = [
            f"{base_url}/ISAPI/Traffic/channels/1/licensePlateAuditData/record?format=json",
            f"{base_url}/ISAPI/Traffic/channels/1/licensePlateAuditData"
        ]

        for plate_no in plates:
            # Postman'de başarılı olduğunuz JSON şeması
            json_payload = {
                "LicensePlateInfoList": [
                    {
                        "LicensePlate": plate_no,
                        "listType": "whiteList",
                        "createTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "effectiveStartDate": start_date,
                        "effectiveTime": end_date,
                        "id": ""
                    }
                ]
            }

            sent_ok = False
            last_status = None
            last_resp_text = ""

            for url in urls:
                try:
            # PUT metodu ile JSON gönderimi
                    res = requests.put(
                        url, 
                        json=json_payload, 
                        headers=headers, 
                        auth=HTTPDigestAuth(cam['user'], cam['pass']), 
                        timeout=5
                    )
                    last_status = res.status_code
                    last_resp_text = res.text
                    
                    if res.status_code in [200, 201]:
                        sent_ok = True
                        break
                except Exception as ex:
                    last_resp_text = str(ex)

                if sent_ok:
                    break
            
            if sent_ok:
                success_count += 1
            else:
                fail_count += 1
                print(f"[HATA] Kamera IP: {cam['ip']} | Plaka: {plate_no} | Status: {last_status} | Yanıt: {last_resp_text}")

        return cam['ip'], success_count, fail_count

    def finish_upload_plates(self, summary):
        self.btn_upload.config(state="normal")
        self.controller.lbl_status.config(text="Plaka yükleme işlemi tamamlandı.")
        messagebox.showinfo("İşlem Sonucu", "\n".join(summary))

    def start_clear_plates_thread(self):
        cam_frame = self.controller.frames["CameraManagementFrame"]
        cams = cam_frame.get_selected_camera_list()

        if not cams:
            messagebox.showwarning("Eksik Bilgi", "Lütfen önce Kamera Yönetimi ekranından kamera seçin.")
            return

        if not messagebox.askyesno("⚠️ Kritik Onay", f"Seçilen {len(cams)} kameradaki TÜM plaka listesi SİLİNECEKTİR!\n\nOnaylıyor musunuz?", icon="warning"):
            return

        self.btn_clear.config(state="disabled")
        threading.Thread(target=self.clear_all_camera_plates, args=(cams,), daemon=True).start()

    def clear_all_camera_plates(self, cams):
        summary = []
        with ThreadPoolExecutor(max_workers=len(cams)) as executor:
            futures = [executor.submit(self.clear_single_camera_plates, cam) for cam in cams]
            for future in as_completed(futures):
                success, ip = future.result()
                summary.append(f"Kamera ({ip}): {'✅ Temizlendi' if success else '❌ Başarısız'}")
        self.after(0, lambda: self.finish_clear_plates(summary))

    def clear_single_camera_plates(self, cam):
        base_url = f"http://{cam['ip']}:{cam['port']}" if cam['port'] else f"http://{cam['ip']}"
        
        # Arayüzden yakaladığın doğru uç nokta
        url = f"{base_url}/ISAPI/Traffic/channels/1/DelLicensePlateAuditData?format=json"
        
        # Yakaladığın doğru payload
        payload = {
            "id": [],
            "deleteAllEnabled": True
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/javascript, */*'
        }
        
        # Hikvision cihazlarda silme komutları PUT veya POST bekleyebilir, ikisini de deneyelim
        for method in [requests.put, requests.post]:
            try:
                res = method(
                    url, 
                    json=payload, 
                    headers=headers, 
                    auth=HTTPDigestAuth(cam['user'], cam['pass']), 
                    timeout=10
                )
                
                if res.status_code in [200, 201]:
                    return True, cam['ip']
            except Exception as e:
                continue
                
        return False, cam['ip']

    def finish_clear_plates(self, summary):
        self.btn_clear.config(state="normal")
        self.controller.lbl_status.config(text="Silme işlemi tamamlandı.")
        messagebox.showinfo("İşlem Sonucu", "\n".join(summary))

# --- 3. VCA EKRANI ---
class VCAFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        frame_vca = ttk.LabelFrame(self, text="Canlı Plaka Okuma Test Ekranı (iDS-2CD7A46G0)", padding=10)
        frame_vca.pack(fill="both", expand=True, pady=5)

        self.btn_test_mode = ttk.Button(frame_vca, text="🟢 Canlı Okuma Testini Başlat", command=self.toggle_test_mode)
        self.btn_test_mode.pack(fill="x", pady=(5, 10))

        self.txt_live_test = tk.Text(frame_vca, height=15, width=70, bg=controller.input_bg, fg="#00adb5" if controller.is_dark_theme else "#005f73", font=("Consolas", 10), relief="flat")
        self.txt_live_test.pack(fill="both", expand=True)
        self.txt_live_test.insert("1.0", "Test modu kapalı...\n")
        self.txt_live_test.config(state="disabled")

    def apply_theme(self):
        self.txt_live_test.config(bg=self.controller.input_bg, fg="#00adb5" if self.controller.is_dark_theme else "#005f73")

    def toggle_test_mode(self):
        if not self.controller.active_cameras:
            messagebox.showwarning("Uyarı", "Canlı testi başlatmak için önce Kamera Yönetimi ekranından aktif bağlantı kurulmuş olmalıdır.")
            return

        self.controller.test_mode_active = not self.controller.test_mode_active
        if self.controller.test_mode_active:
            self.btn_test_mode.config(text="🔴 Canlı Okuma Testini Durdur")
            self.txt_live_test.config(state="normal")
            self.txt_live_test.delete("1.0", tk.END)
            self.txt_live_test.insert("1.0", "Canlı test başlatıldı, plakalar bekleniyor...\n")
            self.txt_live_test.config(state="disabled")
            threading.Thread(target=self.live_test_polling_loop, daemon=True).start()
        else:
            self.btn_test_mode.config(text="🟢 Canlı Okuma Testini Başlat")
            self.txt_live_test.config(state="normal")
            self.txt_live_test.insert(tk.END, "\nTest durduruldu.")
            self.txt_live_test.config(state="disabled")

    def live_test_polling_loop(self):
        import time
        cam_frame = self.controller.frames["CameraManagementFrame"]
        last_seen_plates = {}

        while self.controller.test_mode_active:
            for ip in self.controller.active_cameras:
                port, user, pwd = cam_frame.get_camera_credentials(ip)
                base_url = f"http://{ip}:{port}" if port else f"http://{ip}"
                log_urls = [
                    f"{base_url}/ISAPI/Traffic/channels/1/plateData",
                    f"{base_url}/ISAPI/Event/notification/httpHosts"
                ]
                for log_url in log_urls:
                    try:
                        res = requests.get(log_url, auth=HTTPDigestAuth(user, pwd), timeout=2)
                        if res.status_code == 200:
                            root = ET.fromstring(res.content)
                            plate_found = None
                            time_found = datetime.now().strftime("%H:%M:%S")

                            for elem in root.iter():
                                if elem.tag.endswith('plateNo') and elem.text:
                                    plate_found = self.controller.clean_plate(elem.text)
                                    break
                            
                            if plate_found and last_seen_plates.get(ip) != plate_found:
                                last_seen_plates[ip] = plate_found
                                log_msg = f"[{time_found}] {ip} -> {plate_found}\n"
                                self.after(0, lambda msg=log_msg: self.append_live_log(msg))
                                break
                    except Exception:
                        pass
            time.sleep(2)

    def append_live_log(self, msg):
        self.txt_live_test.config(state="normal")
        self.txt_live_test.insert("1.0", msg)
        self.txt_live_test.config(state="disabled")


# --- 4. AYARLAR EKRANI ---
class SettingsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        frame_settings = ttk.LabelFrame(self, text="Uygulama Ayarları", padding=15)
        frame_settings.pack(fill="both", expand=True, pady=5)

        ttk.Label(frame_settings, text="Görünüm Teması:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

        self.btn_theme_toggle = ttk.Button(frame_settings, text="☀️ Açık / Koyu Tema Değiştir", command=controller.toggle_theme)
        self.btn_theme_toggle.pack(anchor="w", pady=5)

    def apply_theme(self):
        pass


# --- 5. HAKKINDA EKRANI ---
class AboutFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        frame_about = ttk.LabelFrame(self, text="Hakkında", padding=20)
        frame_about.pack(fill="both", expand=True, pady=5)

        about_text = "Red Güvenlik Sistemleri / iDS-2CD7A46G0 Plaka Yönetim Yazılımı v1.0"
        
        lbl_info = ttk.Label(frame_about, text=about_text, font=("Arial", 11, "bold"), foreground="#00adb5" if controller.is_dark_theme else "#005f73")
        lbl_info.pack(expand=True)

    def apply_theme(self):
        for widget in self.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label):
                    child.config(foreground="#00adb5" if self.controller.is_dark_theme else "#005f73")


if __name__ == "__main__":
    root = tk.Tk()
    app = HikvisionANPRApp(root)
    root.mainloop()
