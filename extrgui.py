import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image
import numpy as np

# ------------------------------------------------------------
# Hjälpfunktioner för bitexpansion och nedskalning
# ------------------------------------------------------------

def expand_3_to_8(v3: int) -> int:
    # 3 bitar till 8 bitar: (v<<5)|(v<<2)|(v>>1)
    v3 &= 0x7
    return (v3 << 5) | (v3 << 2) | (v3 >> 1)

def expand_4_to_8(v4: int) -> int:
    # 4 bitar till 8 bitar: (v<<4)|v
    v4 &= 0xF
    return (v4 << 4) | v4

def expand_5_to_8(v5: int) -> int:
    # 5 bitar till 8 bitar: (v<<3)|(v>>2)
    v5 &= 0x1F
    return (v5 << 3) | (v5 >> 2)

def scale_8_to_3(value: int) -> int:
    # 8 bitar till 3 bitar
    return (int(value) >> 5) & 0x7

def scale_8_to_4(value: int) -> int:
    # 8 bitar till 4 bitar
    return (int(value) >> 4) & 0xF

def scale_8_to_5(value: int) -> int:
    # 8 bitar till 5 bitar
    return (int(value) >> 3) & 0x1F

# ------------------------------------------------------------
# Avkodning N64 -> PNG-buffert enligt ZAPD-logiken
# ------------------------------------------------------------

def decode_to_png_array_and_mode(data: bytes, width: int, height: int, fmt: str):
    """
    Returnerar (numpy_array, mode_str) där mode_str är 'RGB' eller 'RGBA'
    och arrayen är i rätt form för Image.fromarray.
    Stöder formaten: I4, I8, IA4, IA8, IA16, RGBA16, RGBA32.
    'RGBA3' mappas till RGBA16.
    """
    format_norm = fmt.upper()
    if format_norm == 'RGBA3':
        format_norm = 'RGBA16'

    if format_norm == 'I4':
        # 2 pixlar per byte, 4 bit grå som expanderas till 8 och dupliceras till RGB
        img = np.zeros((height, width, 3), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(0, width, 2):
                byte = data[idx]
                idx += 1
                g0_4 = (byte >> 4) & 0xF
                g1_4 = byte & 0xF
                g0 = expand_4_to_8(g0_4)
                g1 = expand_4_to_8(g1_4)
                img[y, x, :] = [g0, g0, g0]
                if x + 1 < width:
                    img[y, x + 1, :] = [g1, g1, g1]
        return img, 'RGB'

    elif format_norm == 'I8':
        # 1 pixel per byte, ren gråskala dupliceras till RGB
        img = np.zeros((height, width, 3), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(width):
                g = data[idx]
                idx += 1
                img[y, x, :] = [g, g, g]
        return img, 'RGB'

    elif format_norm == 'IA4':
        # 2 pixlar per byte, varje nibble: ggg a
        img = np.zeros((height, width, 4), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(0, width, 2):
                byte = data[idx]
                idx += 1
                for i in range(2):
                    nibble = (byte >> 4) & 0xF if i == 0 else (byte & 0xF)
                    grayscale_4bit = nibble & 0b1110  # Behåll 4-bit struktur
                    a1 = nibble & 0x1
                    g = (grayscale_4bit << 4) | (grayscale_4bit << 1) | (grayscale_4bit >> 2)
                    a = 255 if a1 else 0
                    xx = x + i
                    if xx < width:
                        img[y, xx, :] = [g, g, g, a]
        return img, 'RGBA'

    elif format_norm == 'IA8':
        # 1 byte per pixel, övre 4 bit grå, nedre 4 bit alfa
        img = np.zeros((height, width, 4), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(width):
                byte = data[idx]
                idx += 1
                g4 = (byte >> 4) & 0xF
                a4 = byte & 0xF
                g = expand_4_to_8(g4)
                a = expand_4_to_8(a4)
                img[y, x, :] = [g, g, g, a]
        return img, 'RGBA'

    elif format_norm == 'IA16':
        # 2 byte per pixel, 8 bit grå och 8 bit alfa
        img = np.zeros((height, width, 4), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(width):
                g = data[idx]
                a = data[idx + 1]
                idx += 2
                img[y, x, :] = [g, g, g, a]
        return img, 'RGBA'

    elif format_norm == 'RGBA16':
        # 2 byte per pixel, rgb5a1
        img = np.zeros((height, width, 4), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(width):
                hi = data[idx]
                lo = data[idx + 1]
                idx += 2
                val = (hi << 8) | lo
                r5 = (val >> 11) & 0x1F
                g5 = (val >> 6) & 0x1F
                b5 = (val >> 1) & 0x1F
                a1 = val & 0x1
                r = expand_5_to_8(r5)
                g = expand_5_to_8(g5)
                b = expand_5_to_8(b5)
                a = 255 if a1 else 0
                img[y, x, :] = [r, g, b, a]
        return img, 'RGBA'

    elif format_norm == 'RGBA32':
        # 4 byte per pixel, 8 bit vardera för RGBA
        img = np.zeros((height, width, 4), dtype=np.uint8)
        idx = 0
        for y in range(height):
            for x in range(width):
                r = data[idx]
                g = data[idx + 1]
                b = data[idx + 2]
                a = data[idx + 3]
                idx += 4
                img[y, x, :] = [r, g, b, a]
        return img, 'RGBA'

    else:
        raise ValueError(f"Okänt eller ej implementerat format: {fmt}")

# ------------------------------------------------------------
# Kodning PNG-buffert -> N64 enligt ZAPD-logiken
# ------------------------------------------------------------

def encode_from_png_array(img_array: np.ndarray, fmt: str) -> bytearray:
    """
    img_array är en numpy-array från en redan konverterad PIL-bild i rätt mode.
    fmt stöder: I4, I8, IA4, IA8, IA16, RGBA16, RGBA32.
    'RGBA3' mappas till RGBA16.
    """
    format_norm = fmt.upper()
    if format_norm == 'RGBA3':
        format_norm = 'RGBA16'

    h, w = img_array.shape[0], img_array.shape[1]
    out = bytearray()

    if format_norm == 'I4':
        # Förväntar gråskaleinnehåll, använd rödkanalen om 3-kanalers RGB
        if img_array.ndim == 3 and img_array.shape[2] == 3:
            gray = img_array[:, :, 0]
        elif img_array.ndim == 2:
            gray = img_array
        else:
            # Om det är RGBA, ta r
            gray = img_array[:, :, 0]
        for y in range(h):
            x = 0
            while x < w:
                g0 = scale_8_to_4(int(gray[y, x]))
                if x + 1 < w:
                    g1 = scale_8_to_4(int(gray[y, x + 1]))
                else:
                    g1 = 0
                out.append((g0 << 4) | g1)
                x += 2
        return out

    elif format_norm == 'I8':
        if img_array.ndim == 3:
            gray = img_array[:, :, 0]
        else:
            gray = img_array
        for y in range(h):
            for x in range(w):
                out.append(int(gray[y, x]) & 0xFF)
        return out

    elif format_norm == 'IA4':
        # Källa ska vara grå med alfa. Om RGB eller RGBA, använd r och alpha.
        if img_array.ndim == 2:
            r = img_array
            a = np.full_like(r, 255)
        elif img_array.shape[2] == 4:
            r = img_array[:, :, 0]
            a = img_array[:, :, 3]
        elif img_array.shape[2] == 2:
            r = img_array[:, :, 0]
            a = img_array[:, :, 1]
        else:
            r = img_array[:, :, 0]
            a = np.full((h, w), 255, dtype=np.uint8)

        for y in range(h):
            x = 0
            while x < w:
                g0_3 = scale_8_to_3(int(r[y, x]))
                a0_1 = 1 if int(a[y, x]) != 0 else 0
                nib0 = ((g0_3 << 1) & 0xE) | a0_1

                if x + 1 < w:
                    g1_3 = scale_8_to_3(int(r[y, x + 1]))
                    a1_1 = 1 if int(a[y, x + 1]) != 0 else 0
                    nib1 = ((g1_3 << 1) & 0xE) | a1_1
                else:
                    nib1 = 0

                out.append(((nib0 & 0xF) << 4) | (nib1 & 0xF))
                x += 2
        return out

    elif format_norm == 'IA8':
        # 4 bit grå, 4 bit alfa
        if img_array.ndim == 2:
            r = img_array
            a = np.full_like(r, 255)
        elif img_array.shape[2] == 4:
            r = img_array[:, :, 0]
            a = img_array[:, :, 3]
        elif img_array.shape[2] == 2:
            r = img_array[:, :, 0]
            a = img_array[:, :, 1]
        else:
            r = img_array[:, :, 0]
            a = np.full((h, w), 255, dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                g4 = scale_8_to_4(int(r[y, x]))
                a4 = scale_8_to_4(int(a[y, x]))
                out.append(((g4 & 0xF) << 4) | (a4 & 0xF))
        return out

    elif format_norm == 'IA16':
        # 8 bit grå och 8 bit alfa
        if img_array.ndim == 2:
            r = img_array
            a = np.full_like(r, 255)
        elif img_array.shape[2] == 4:
            r = img_array[:, :, 0]
            a = img_array[:, :, 3]
        elif img_array.shape[2] == 2:
            r = img_array[:, :, 0]
            a = img_array[:, :, 1]
        else:
            r = img_array[:, :, 0]
            a = np.full((h, w), 255, dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                out.append(int(r[y, x]) & 0xFF)
                out.append(int(a[y, x]) & 0xFF)
        return out

    elif format_norm == 'RGBA16':
        # 5 bit r, 5 bit g, 5 bit b, 1 bit a
        # Alfabit via tröskel 128, inte bara a!=0
        if img_array.ndim == 2:
            r = g = b = img_array
            a = np.full_like(r, 255)
        elif img_array.shape[2] == 4:
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            a = img_array[:, :, 3]
        elif img_array.shape[2] == 3:
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            a = np.full((h, w), 255, dtype=np.uint8)
        else:
            raise ValueError("Oväntat bildformat vid RGBA16-kodning")

        for y in range(h):
            for x in range(w):
                R5 = scale_8_to_5(int(r[y, x]))
                G5 = scale_8_to_5(int(g[y, x]))
                B5 = scale_8_to_5(int(b[y, x]))
                A1 = 1 if int(a[y, x]) != 0 else 0
                word = ((R5 & 0x1F) << 11) | ((G5 & 0x1F) << 6) | ((B5 & 0x1F) << 1) | (A1 & 0x1)
                out.append((word >> 8) & 0xFF)
                out.append(word & 0xFF)
        return out

    elif format_norm == 'RGBA32':
        # 8 bit vardera för RGBA, 4 byte per pixel
        if img_array.ndim == 2:
            r = g = b = img_array
            a = np.full_like(r, 255)
        elif img_array.shape[2] == 4:
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            a = img_array[:, :, 3]
        elif img_array.shape[2] == 3:
            r = img_array[:, :, 0]
            g = img_array[:, :, 1]
            b = img_array[:, :, 2]
            a = np.full((h, w), 255, dtype=np.uint8)
        else:
            raise ValueError("Oväntat bildformat vid RGBA32-kodning")

        for y in range(h):
            for x in range(w):
                out.append(int(r[y, x]) & 0xFF)
                out.append(int(g[y, x]) & 0xFF)
                out.append(int(b[y, x]) & 0xFF)
                out.append(int(a[y, x]) & 0xFF)
        return out

    else:
        raise ValueError(f"Okänt eller ej implementerat format: {fmt}")

# ------------------------------------------------------------
# Wrapper-funktioner för att läsa, spara PNG och skriva tillbaka
# ------------------------------------------------------------

def extract_and_convert(filename, output_folder, width, height, fmt, address, name, subfolder=''):
    # Bytes per pixel enligt N64-rådata
    fmt_norm = fmt.upper()
    if fmt_norm == 'RGBA3':
        fmt_norm = 'RGBA16'
    if fmt_norm in ['I4', 'IA4']:
        bpp = 0.5
    elif fmt_norm in ['I8', 'IA8']:
        bpp = 1
    elif fmt_norm in ['IA16', 'RGBA16']:
        bpp = 2
    elif fmt_norm == 'RGBA32':
        bpp = 4
    else:
        raise ValueError(f"Okänt format: {fmt}")

    total_bytes = int(width * height * bpp)

    full_output_folder = os.path.join(output_folder, subfolder) if subfolder else output_folder
    clean_folder = os.path.join(output_folder, 'clean', subfolder)
    os.makedirs(full_output_folder, exist_ok=True)
    os.makedirs(clean_folder, exist_ok=True)

    with open(filename, 'rb') as f:
        f.seek(address)
        data = f.read(total_bytes)

    clean_file_path = os.path.join(clean_folder, f"{name}.bin")
    with open(clean_file_path, 'wb') as clean_file:
        clean_file.write(data)
        print(f"Okonverterad data för '{name}' har sparats i '{clean_file_path}'")

    try:
        arr, mode = decode_to_png_array_and_mode(data, width, height, fmt_norm)
        img = Image.fromarray(arr, mode)
        img.save(os.path.join(full_output_folder, f"{name}.png"))
        print(f"Bilden '{name}.png' har sparats i '{full_output_folder}'")
    except ValueError as e:
        print(f"Fel vid konvertering av '{name}': {e}")

def parse_settings_and_extract(file_path, image_file, output_folder):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    width = height = None
    subfolder = ''
    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue
        parts = line.strip().split()
        if parts[0] == 'Dir':
            subfolder = parts[1]
        elif parts[0] == 'Set' and parts[1] == 'TexS':
            size = parts[2].split('x')
            width, height = map(int, size)
        elif parts[0] == 'Exp':
            current_format = parts[1]
            address = int(parts[2], 16)
            name = parts[3]
            extract_and_convert(image_file, output_folder, width, height, current_format, address, name, subfolder)

def inject_image(filename, input_image_path, width, height, fmt, address):
    try:
        fmt_norm = fmt.upper()
        if fmt_norm == 'RGBA3':
            fmt_norm = 'RGBA16'

        # Välj korrekt PIL-mode för inläsning före kodning
        if fmt_norm in ['I4', 'I8']:
            pil_mode = 'L'         # gråskala utan alfa
        elif fmt_norm in ['IA4', 'IA8', 'IA16']:
            pil_mode = 'LA'        # gråskala med alfa
        elif fmt_norm in ['RGBA16', 'RGBA32']:
            pil_mode = 'RGBA'      # färg med alfa
        else:
            raise ValueError(f"Okänt format: {fmt}")

        print(f"Öppnar bild för injektering: {input_image_path}")
        image = Image.open(input_image_path).convert(pil_mode).resize((width, height))
        img_array = np.array(image)

        encoded = encode_from_png_array(img_array, fmt_norm)

        with open(filename, 'r+b') as f:
            f.seek(address)
            f.write(encoded)
            print(f"Injicerat '{input_image_path}' till '{filename}' på adress {address:X}")
    except Exception as e:
        print(f"Fel vid injektering av '{input_image_path}': {e}")

def parse_settings_and_inject(file_path, image_file, output_folder):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    width = height = None
    subfolder = ''
    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue
        parts = line.strip().split()
        if parts[0] == 'Dir':
            subfolder = parts[1]
        elif parts[0] == 'Set' and parts[1] == 'TexS':
            size = parts[2].split('x')
            width, height = map(int, size)
            print(f"Inställningar: {width}x{height}")
        elif parts[0] == 'Exp':
            current_format = parts[1]
            address = int(parts[2], 16)
            name = parts[3]
            input_image_path = os.path.join(output_folder, subfolder, f"{name}.png")
            print(f"Försöker injicera: {input_image_path} på adress {address:X}")
            if os.path.exists(input_image_path):
                inject_image(image_file, input_image_path, width, height, current_format, address)
            else:
                print(f"Filen '{input_image_path}' hittades inte.")

# ------------------------------------------------------------
# GUI
# ------------------------------------------------------------

class ImageExtractorApp:
    def __init__(self, master):
        self.master = master
        master.title('Bildextraherare')
        master.geometry('360x300')

        control_frame = tk.Frame(master)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        self.settings_label = tk.Label(control_frame, text="Välj settings-fil:")
        self.settings_label.grid(row=0, column=0, sticky='ew', pady=5)
        self.settings_var = tk.StringVar()
        self.settings_menu = ttk.Combobox(control_frame, textvariable=self.settings_var)
        self.settings_menu.grid(row=0, column=1, padx=10)
        self.populate_settings_menu()

        self.overwrite_var = tk.BooleanVar()
        self.overwrite_check = tk.Checkbutton(control_frame, text="RW", variable=self.overwrite_var, command=self.update_start_button_state)
        self.overwrite_check.grid(row=0, column=2, sticky='w')

        self.file_button = tk.Button(control_frame, text="Välj Z64-fil", command=self.load_image_file)
        self.file_button.grid(row=1, column=0, sticky='ew', pady=5)
        self.file_path_label = tk.Label(control_frame, text="")
        self.file_path_label.grid(row=1, column=1, columnspan=2, padx=10)

        self.folder_button = tk.Button(control_frame, text="Välj destination", command=self.choose_destination)
        self.folder_button.grid(row=2, column=0, sticky='ew', pady=5)
        self.folder_path_label = tk.Label(control_frame, text="")
        self.folder_path_label.grid(row=2, column=1, columnspan=2, padx=10)

        self.start_button = tk.Button(control_frame, text="Starta konvertering", command=self.start_conversion)
        self.start_button.grid(row=3, column=0, sticky='ew', pady=5)

        self.inject_button = tk.Button(control_frame, text="Starta injektering", command=self.start_injection)
        self.inject_button.grid(row=4, column=0, sticky='ew', pady=5)

        self.run_button = tk.Button(control_frame, text="Starta Project64", command=self.start_project64)
        self.run_button.grid(row=5, column=0, sticky='ew', pady=5)

        self.status_label = tk.Label(control_frame, text="", wraplength=300)
        self.status_label.grid(row=6, column=0, columnspan=3, pady=5)

    def populate_settings_menu(self):
        settings_files = [f for f in os.listdir('.') if f.endswith('.txt')]
        self.settings_menu['values'] = settings_files
        if 'PAL v1.0.txt' in settings_files:
            self.settings_var.set('PAL v1.0.txt')

    def load_image_file(self):
        self.image_file_path = filedialog.askopenfilename(filetypes=[("Z64 files", "*.z64")])
        if self.image_file_path:
            self.file_path_label.config(text=self.image_file_path)
            self.status_label.config(text="Z64-fil vald.")
            print(f"Z64-fil vald: {self.image_file_path}")

    def choose_destination(self):
        self.output_folder = filedialog.askdirectory()
        if self.output_folder:
            self.folder_path_label.config(text=self.output_folder)
            self.status_label.config(text="Destination vald.")
            print(f"Destination vald: {self.output_folder}")
            self.update_start_button_state()

    def update_start_button_state(self):
        if hasattr(self, 'output_folder'):
            if os.listdir(self.output_folder) and not self.overwrite_var.get():
                self.start_button.config(state=tk.DISABLED)
            else:
                self.start_button.config(state=tk.NORMAL)

    def start_conversion(self):
        if hasattr(self, 'image_file_path') and hasattr(self, 'output_folder'):
            settings_path = self.settings_var.get()
            print(f"Startar konvertering med inställningar från: {settings_path}")
            parse_settings_and_extract(settings_path, self.image_file_path, self.output_folder)
            self.status_label.config(text="Konvertering slutförd.")
            self.update_start_button_state()
        else:
            self.status_label.config(text="Välj både en Z64-fil och en destination först.")
            print("Välj både en Z64-fil och en destination först.")

    def start_injection(self):
        if hasattr(self, 'image_file_path') and hasattr(self, 'output_folder'):
            settings_path = self.settings_var.get()
            print(f"Startar injektering med inställningar från: {settings_path}")
            parse_settings_and_inject(settings_path, self.image_file_path, self.output_folder)
            self.status_label.config(text="Injektering slutförd.")
        else:
            self.status_label.config(text="Välj både en Z64-fil och en destination först.")
            print("Välj både en Z64-fil och en destination först.")

    def start_project64(self):
        if hasattr(self, 'image_file_path'):
            project64_path = r"C:\Program Files (x86)\Project64 3.0\Project64.exe"
            try:
                print(f"Startar Project64 med fil: {self.image_file_path}")
                subprocess.run([project64_path, self.image_file_path])
                self.status_label.config(text="Project64 startad.")
            except Exception as e:
                self.status_label.config(text=f"Fel vid start av Project64: {e}")
                print(f"Fel vid start av Project64: {e}")
        else:
            self.status_label.config(text="Välj en Z64-fil först.")
            print("Välj en Z64-fil först.")

# ------------------------------------------------------------
# Programstart
# ------------------------------------------------------------

root = tk.Tk()
app = ImageExtractorApp(root)
root.mainloop()