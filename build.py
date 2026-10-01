import os
import shutil
import subprocess
import sys

print("--- BUDOWANIE APLIKACJI NATIONFOOTBALL ---")

# Uruchomienie PyInstallera w trybie pojedynczego pliku (przenośny .exe)
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--noconsole",
    "--clean",
    "--name", "NationFootball",
    "--icon", "ball.ico",         # <--- TUTAJ DODALIŚMY IKONKĘ PIŁKI!
    # tło i ikona okna muszą być w środku .exe - u innych użytkowników nie ma folderu projektu
    "--add-data", "tlo.png;.",
    "--add-data", "ball.ico;.",
    "test_flashscore.py"
]

print("Trwa kompilacja kodu przez PyInstaller...")
subprocess.run(cmd, check=True)

# Skopiowanie gotowego pliku .exe do głównego folderu projektu, żeby nie trzeba było szukać w dist/
zrodlo_exe = os.path.join("dist", "NationFootball.exe")
cel_exe = "NationFootball.exe"
if os.path.exists(zrodlo_exe):
    shutil.copy2(zrodlo_exe, cel_exe)
    print(f"\nGotowe! Aplikacja znajduje się w: {os.path.abspath(cel_exe)}")
else:
    print("\nUwaga: nie znaleziono zbudowanego pliku .exe w dist/.")