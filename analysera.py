import os
import re

# Konfiguration
CLEAN_FOLDER = r"C:\pajton\denna\clean"
NTSC_ROM = r"C:\pajton\zeldantsc.z64"
OUTPUT_REPORT = r"C:\pajton\bitmap_analysis.txt"
OUTPUT_SETTINGS = r"C:\pajton\NTSC v1.0.txt"

def find_all_occurrences(rom_data, search_data):
    """Hitta alla förekomster av en bytesekvens i ROM:en"""
    occurrences = []
    start = 0
    while True:
        pos = rom_data.find(search_data, start)
        if pos == -1:
            break
        occurrences.append(pos)
        start = pos + 1
    return occurrences

def extract_name_from_path(file_path):
    """Extrahera namn från filsökvägen (utan förlängning och mappar)"""
    filename = os.path.basename(file_path)
    return os.path.splitext(filename)[0]

def parse_pal_settings(settings_file):
    """Läs PAL-inställningsfilen för att få struktur"""
    settings = []
    current_dir = ""
    current_format = ""
    current_width = 0
    current_height = 0
    
    with open(settings_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            if parts[0] == 'Dir':
                current_dir = parts[1]
            elif parts[0] == 'Set' and parts[1] == 'TexS':
                size = parts[2].split('x')
                current_width, current_height = int(size[0]), int(size[1])
            elif parts[0] == 'Exp':
                current_format = parts[1]
                address = parts[2]
                name = parts[3]
                settings.append({
                    'dir': current_dir,
                    'format': current_format,
                    'width': current_width,
                    'height': current_height,
                    'address': address,
                    'name': name
                })
    
    return settings

def main():
    # Läs NTSC-romfilen
    print(f"Läser NTSC-romfilen: {NTSC_ROM}")
    with open(NTSC_ROM, 'rb') as f:
        rom_data = f.read()
    print(f"Romstorlek: {len(rom_data)} bytes")
    
    # Samla in alla bitmap-filer från clean-mappen
    print(f"\nSöker efter bitmap-filer i: {CLEAN_FOLDER}")
    bitmap_files = {}
    for root, dirs, files in os.walk(CLEAN_FOLDER):
        for file in files:
            if file.endswith('.bin'):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    bitmap_data = f.read()
                relative_path = os.path.relpath(file_path, CLEAN_FOLDER)
                bitmap_files[relative_path] = bitmap_data
    
    print(f"Hittade {len(bitmap_files)} bitmap-filer")
    
    # Analysera varje bitmap
    results = {}
    print("\nAnalyserar bitmaps...")
    for i, (file_path, bitmap_data) in enumerate(bitmap_files.items(), 1):
        name = extract_name_from_path(file_path)
        print(f"  [{i}/{len(bitmap_files)}] {name}...", end='', flush=True)
        
        occurrences = find_all_occurrences(rom_data, bitmap_data)
        results[file_path] = {
            'name': name,
            'size': len(bitmap_data),
            'occurrences': occurrences,
            'count': len(occurrences)
        }
        print(f" {len(occurrences)} förekomst(er)")
    
    # Skriv rapport
    print(f"\nSkriver rapport till: {OUTPUT_REPORT}")
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BITMAP-ANALYS FÖR NTSC-ROM\n")
        f.write("=" * 80 + "\n\n")
        
        # Sammanfattning
        total_found = sum(1 for r in results.values() if r['count'] > 0)
        total_missing = sum(1 for r in results.values() if r['count'] == 0)
        total_duplicates = sum(r['count'] - 1 for r in results.values() if r['count'] > 1)
        
        f.write(f"Totalt bitmaps: {len(results)}\n")
        f.write(f"Hittade: {total_found}\n")
        f.write(f"Saknade: {total_missing}\n")
        f.write(f"Dubbletter: {total_duplicates}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Detaljer för varje bitmap
        f.write("DETALJERAD LISTA:\n\n")
        for file_path in sorted(results.keys()):
            result = results[file_path]
            f.write(f"Namn: {result['name']}\n")
            f.write(f"Storlek: {result['size']} bytes\n")
            f.write(f"Förekomster: {result['count']}\n")
            
            if result['count'] > 0:
                if result['count'] <= 5:
                    f.write("Offsets: ")
                    offsets_hex = [f"0x{offset:X}" for offset in result['occurrences']]
                    f.write(", ".join(offsets_hex))
                    f.write("\n")
                else:
                    f.write(f"Offsets: (För många för att visa - {result['count']} förekomster)\n")
                    f.write(f"Första offset: 0x{result['occurrences'][0]:X}\n")
            else:
                f.write("Status: SAKNAS I NTSC-ROM\n")
            
            f.write("\n")
    
    # Läs PAL-inställningar för struktur
    print(f"\nSkapar NTSC-inställningsfil...")
    pal_settings_path = r"C:\pajton\PAL v1.0.txt"
    pal_settings = parse_pal_settings(pal_settings_path)
    
    # Skapa NTSC-inställningsfil
    with open(OUTPUT_SETTINGS, 'w', encoding='utf-8') as f:
        current_dir = ""
        current_format = ""
        current_size = ""
        
        for setting in pal_settings:
            # Är vi i en ny Dir?
            if setting['dir'] != current_dir:
                current_dir = setting['dir']
                f.write(f"Dir {current_dir}\n")
            
            # Är det en ny Set TexS?
            new_size = f"{setting['width']}x{setting['height']}"
            if new_size != current_size or setting['format'] != current_format:
                current_size = new_size
                current_format = setting['format']
                f.write(f"Set TexS {current_size}\n")
            
            # Hitta motsvarande bitmap i resultaten
            found = False
            for file_path, result in results.items():
                if result['name'] == setting['name'] and result['count'] > 0:
                    # Använd första förekomsten
                    offset = result['occurrences'][0]
                    f.write(f"Exp {setting['format']} {offset:X} {setting['name']}\n")
                    found = True
                    break
            
            if not found:
                # Kommentera ut saknade bitmap
                f.write(f"# Exp {setting['format']} XXXX {setting['name']} (SAKNAS - SÖK MANUELLT)\n")
    
    print(f"NTSC-inställningsfilen skapad: {OUTPUT_SETTINGS}")
    print("\nAnalys slutförd!")
    print(f"\nRapport sparad: {OUTPUT_REPORT}")
    print(f"Inställningsfil sparad: {OUTPUT_SETTINGS}")

if __name__ == "__main__":
    main()