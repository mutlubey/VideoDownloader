# pip install pyinstaller
import os, urllib.request, zipfile, PyInstaller.__main__

if not os.path.exists("ffmpeg.exe"):
    print("FFmpeg indiriliyor...")
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    urllib.request.urlretrieve(url, "ffmpeg.zip")
    with zipfile.ZipFile("ffmpeg.zip") as z:
        for name in z.namelist():
            if name.endswith(("ffmpeg.exe", "ffprobe.exe")):
                z.extract(name)
                os.rename(name, os.path.basename(name))
    os.remove("ffmpeg.zip")
    print("FFmpeg hazır.")

PyInstaller.__main__.run([
    "inderme.py", "--clean", "--onefile", "--noconsole",
    "--name=Video Download Manager", "--icon=icon.ico",
    "--add-data=icon.png;.", "--add-data=ffmpeg.exe;.", "--add-data=ffprobe.exe;.",
])
