# RadialConvert

Convert any file to any format from a circular menu that pops up at your cursor (a Windows take on radial-menu apps like Tangerine on macOS).

## For users

1. Download `RadialConvert-Setup-x.y.z.exe` from the **Releases** page.
2. Run it. Windows may say "Windows protected your PC" because the app isn't code-signed: click **More info -> Run anyway**.
3. Leave "Add Convert with RadialConvert to the right-click menu" ticked.

Using it:
- Right-click any file -> **Convert with RadialConvert** (Windows 11: under *Show more options*), or drag a file onto the orange circle, or double-click the circle to browse.
- Click a format in the ring (or press 1-9). Esc, right-click or clicking outside cancels.
- The converted file is saved next to the original and Explorer opens with it selected.

Supported: images, audio, video (ffmpeg bundled), PDF -> images/text, Markdown/HTML/text/EPUB (pandoc bundled), CSV/JSON/Excel. Word/PowerPoint/PDF export needs [LibreOffice](https://www.libreoffice.org/) installed (free); those formats appear in the ring automatically once it is.

Troubleshooting: tray icon -> **Open log file**.

## For developers

### Run from source

```powershell
pip install -r requirements.txt
python tools\fetch_tools.py      # optional: downloads ffmpeg + pandoc into ./bin
python main.py                   # tray + drop circle
python main.py "C:\path\file"    # open the ring for one file
python register_context_menu.py  # right-click entry (add --remove to undo)
```

### Build the exe and installer

```powershell
.\build.ps1 -Version 1.0.0
```

This installs dependencies, generates the icon, downloads ffmpeg (LGPL build) and pandoc, runs PyInstaller (`dist\RadialConvert\RadialConvert.exe`) and, if [Inno Setup 6](https://jrsoftware.org/isdl.php) is installed, builds `dist\RadialConvert-Setup-1.0.0.exe`.

### Publish a release (GitHub)

```powershell
git add .
git commit -m "Release 1.0.0"
git push
git tag v1.0.0
git push origin v1.0.0
```

The workflow in `.github/workflows/release.yml` builds the installer on GitHub and attaches it to a release for that tag.

### Licences

The installer ships ffmpeg (LGPL build) and pandoc (GPL). Their licence files are copied to `bin\licenses`; keep them in the installer and link to the upstream sources (https://ffmpeg.org, https://pandoc.org) on your download page.

### Adding a format

1. Add the extension to `KINDS` and the target to `TARGETS` in `converter.py`.
2. Add a branch in `_tools_needed` and `convert` if it needs a new backend.

The menu picks it up automatically.

### Files

| File | Purpose |
|---|---|
| `main.py` | tray app, drop circle, command-line entry |
| `radial_menu.py` | the circular menu widget |
| `converter.py` | conversion engine and backend detection |
| `shell_integration.py` | Explorer right-click entry (source and exe) |
| `RadialConvert.spec`, `build.ps1`, `installer.iss` | packaging |
| `tools/` | icon generator, ffmpeg/pandoc downloader |
