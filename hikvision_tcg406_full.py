import threading
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from requests.auth import HTTPDigestAuth


class ANPRManagementApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Hikvision ANPR Yönetim Sistemi")
    self.root.geometry("900x600")

    # Tema ve Arayüz Ayarları (Mevcut yapınıza uygun)
    self.setup_styles()
    self.create_widgets()

  def setup_styles(self):
    self.style = ttk.Style()
    self.style.theme_use("clam")
    # Modern ve kararlı renk paleti
    self.style.configure(
        "TButton", font=("Arial", 10, "bold"), padding=6, relief="flat"
    )
    self.style.configure("TLabel", font=("Arial", 10))
    self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))

  def create_widgets(self):
    # Üst Bilgi / Bağlantı Paneli
    top_frame = ttk.LabelFrame(
        self.root, text=" Kamera Bağlantı Ayarları ", padding=10
    )
    top_frame.pack(fill="x", padx=10, pady=10)

    ttk.Label(top_frame, text="Kamera IP:").grid(
        row=0, column=0, sticky="w", padx=5
    )
    self.ip_entry = ttk.Entry(top_frame, width=18)
    self.ip_entry.insert(0, "192.168.1.141")
    self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(top_frame, text="Kullanıcı Adı:").grid(
        row=0, column=2, sticky="w", padx=5
    )
    self.user_entry = ttk.Entry(top_frame, width=12)
    self.user_entry.insert(0, "admin")
    self.user_entry.grid(row=0, column=3, padx=5, pady=5)

    ttk.Label(top_frame, text="Şifre:").grid(row=0, column=4, sticky="w", padx=5)
    self.pass_entry = ttk.Entry(top_frame, width=12, show="*")
    self.pass_entry.grid(row=0, column=5, padx=5, pady=5)

    # İşlem / Plaka Ekleme Paneli
    action_frame = ttk.LabelFrame(
        self.root, text=" Beyaz Liste Plaka İşlemleri ", padding=10
    )
    action_frame.pack(fill="x", padx=10, pady=5)

    ttk.Label(action_frame, text="Plaka No:").grid(
        row=0, column=0, sticky="w", padx=5
    )
    self.plate_entry = ttk.Entry(action_frame, width=18)
    self.plate_entry.grid(row=0, column=1, padx=5, pady=5)

    self.add_button = ttk.Button(
        action_frame, text="Plaka Ekle (JSON)", command=self.start_add_plate_thread
    )
    self.add_button.grid(row=0, column=2, padx=15, pady=5)

    # Log / Durum Ekranı
    log_frame = ttk.LabelFrame(
        self.root, text=" İşlem Logları ve Yanıtlar ", padding=10
    )
    log_frame.pack(fill="both", expand=True, padx=10, pady=10)

    self.log_text = tk.Text(log_frame, wrap="word", height=12, font=("Consolas", 9))
    self.log_text.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(
        log_frame, orient="vertical", command=self.log_text.yview
    )
    scrollbar.pack(side="right", fill="y")
    self.log_text.configure(yscrollcommand=scrollbar.set)

  def log_message(self, message):
    self.log_text.insert("end", message + "\n")
    self.log_text.see("end")

  def start_add_plate_thread(self):
    # Arayüzün donmaması için işlemi arka plan iş parçacığına (thread) alıyoruz
    ip = self.ip_entry.get().strip()
    user = self.user_entry.get().strip()
    password = self.pass_entry.get().strip()
    plate = self.plate_entry.get().strip().upper()

    if not ip or not plate:
      messagebox.showwarning(
          "Eksik Bilgi", "Lütfen Kamera IP adresini ve Plaka bilgisini girin!"
      )
      return

    self.add_button.config(state="disabled")
    threading.Thread(
        target=self.send_plate_request,
        args=(ip, user, password, plate),
        daemon=True,
    ).start()

  def send_plate_request(self, ip, username, password, plate_number):
    # F12 ile yakaladığımız güncel ve doğru V5.10.0 endpoint adresi
    url = f"http://{ip}/ISAPI/Traffic/channels/1/licensePlateAuditData/record?format=json"

    # Kameranın kesinlikle kabul ettiği JSON şema yapısı
    payload = {
        "LicensePlateAuditData": {
            "plateNo": plate_number,
            "listType": "allowList",
            "beginTime": "2026-08-01T00:00:00",
            "endTime": "2029-08-31T23:59:59",
        }
    }

    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
      self.log_message(f"[{plate_number}] Kameraya istek gönderiliyor...")
      response = requests.post(
          url,
          json=payload,
          headers=headers,
          auth=HTTPDigestAuth(username, password),
          timeout=5,
      )

      self.log_message(f"HTTP Durum Kodu: {response.status_code}")
      self.log_message(f"Sunucu Yanıtı: {response.text}")

      if response.status_code == 200:
        self.root.after(
            0,
            lambda: messagebox. 성공(
                "Başarılı", f"'{plate_number}' başarıyla eklendi!"
            ),
        )
      else:
        self.root.after(
            0,
            lambda: messagebox.showerror(
                "Hata", f"Kamera hata kodu döndürdü: {response.status_code}"
            ),
        )

    except requests.exceptions.RequestException as e:
      self.log_message(f"Bağlantı Hatası: {str(e)}")
      self.root.after(
          0,
          lambda: messagebox.showerror(
              "Bağlantı Hatası", f"Cihaza erişilemedi:\n{e}"
          ),
      )
    finally:
      self.root.after(0, lambda: self.add_button.config(state="normal"))


if __name__ == "__main__":
  root = tk.Tk()
  app = ANPRManagementApp(root)
  root.mainloop()
