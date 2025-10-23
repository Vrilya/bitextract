#!/usr/bin/env python3
"""
ROM Compression Script
Automatiskt komprimerar .z64 ROM-filer med rätt parametrar baserat på version
Läser konfiguration från rom_config.txt
"""

import subprocess
import sys
import os
from pathlib import Path


def load_config(config_file='rom_config.txt'):
    """Läser konfigurationen från rom_config.txt"""
    configs = {}
    
    if not os.path.exists(config_file):
        print(f"❌ Fel: Konfigurationsfilen '{config_file}' hittades inte!")
        print(f"   Filen måste ligga i samma mapp som skriptet.")
        return None
    
    current_section = None
    
    with open(config_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Hoppa över tomma rader
            if not line:
                continue
            
            # Kolla om det är en sektion (t.ex. [pal10])
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1].lower()
                configs[current_section] = ''
            elif current_section:
                # Lägg till kommandoraden till den aktuella sektionen
                configs[current_section] = line
    
    return configs


def detect_rom_version(filename, available_versions):
    """Identifierar ROM-versionen baserat på filnamnet"""
    filename_lower = filename.lower()
    
    for version in available_versions:
        if version in filename_lower:
            return version
    
    return None


def build_command(input_file, output_file, config_params):
    """Bygger kommandosträngen för komprimering"""
    cmd_str = (
        f'z64compress-v1.0.2-win32.exe '
        f'--in "{input_file}" '
        f'--out "{output_file}" '
        f'--mb 32 '
        f'--codec yaz '
        f'{config_params}'
    )
    
    return cmd_str


def compress_rom(input_file, configs):
    """Komprimerar en ROM-fil"""
    # Kontrollera att filen finns
    if not os.path.exists(input_file):
        print(f"❌ Fel: Filen '{input_file}' hittades inte!")
        return False
    
    # Kontrollera filformat
    if not input_file.lower().endswith('.z64'):
        print(f"❌ Fel: Filen måste vara en .z64-fil!")
        return False
    
    # Identifiera version
    version = detect_rom_version(input_file, configs.keys())
    if not version:
        print(f"❌ Fel: Kunde inte identifiera ROM-version från filnamnet!")
        print(f"   Filnamnet måste innehålla något av: {', '.join(configs.keys())}")
        return False
    
    print(f"✓ Identifierad version: {version.upper()}")
    
    # Skapa utdatafilnamn
    path = Path(input_file)
    output_file = str(path.with_name(f"{path.stem}_recompressed{path.suffix}"))
    
    print(f"✓ Input:  {input_file}")
    print(f"✓ Output: {output_file}")
    
    # Bygg kommando
    cmd_str = build_command(input_file, output_file, configs[version])
    
    # Visa kommandot
    print(f"\n📋 Kör kommando:")
    print(cmd_str)
    print()
    
    # Kör komprimering
    try:
        result = subprocess.run(cmd_str, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"\n✅ Komprimering klar! Utdatafil: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Fel vid komprimering:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print(f"❌ Fel: z64compress-v1.0.2-win32.exe hittades inte!")
        print(f"   Se till att programmet finns i samma mapp eller i PATH.")
        return False


def main():
    # Ladda konfiguration
    configs = load_config()
    if not configs:
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("ROM Compression Script")
        print("=" * 50)
        print("\nAnvändning:")
        print(f"  python {sys.argv[0]} <rom-fil.z64>")
        print("\nStödda versioner (från rom_config.txt):")
        for version in configs.keys():
            print(f"  - {version.upper()}")
        print("\nExempel:")
        print(f"  python {sys.argv[0]} zelda_pal10.z64")
        print(f"  python {sys.argv[0]} game_ntsc12.z64")
        print("\nOm du vill ändra komprimeringsparametrar,")
        print("redigera rom_config.txt och klistra in från z64compress output.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    success = compress_rom(input_file, configs)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()