import os
import shutil
import subprocess
import sys
import zipfile

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
    sys.exit("\nUwaga: nie znaleziono zbudowanego pliku .exe w dist/.")

# --- PACZKI DO ROZESŁANIA (folder wydanie/) ---
os.makedirs("wydanie", exist_ok=True)

# ZIP z samym programem (otwiera się w Windowsie bez dodatkowych programów)
with zipfile.ZipFile(os.path.join("wydanie", "NationFootball.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(zrodlo_exe, "NationFootball.exe")
print(f"ZIP:        {os.path.abspath(os.path.join('wydanie', 'NationFootball.zip'))}")

# Instalator (Inno Setup 6: winget install JRSoftware.InnoSetup)
iscc = next((p for p in (
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
) if os.path.exists(p)), None)
if iscc:
    subprocess.run([iscc, "/Q", "instalator.iss"], check=True)
    print(f"Instalator: {os.path.abspath(os.path.join('wydanie', 'NationFootball_Instalator.exe'))}")
else:
    print("Pominięto instalator - brak Inno Setup 6 (winget install JRSoftware.InnoSetup)")