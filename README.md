# RadialConvert

Convert any file to any format from a circular menu that pops up at your cursor (a Windows take on radial-menu apps like Tangerine on macOS).

## Setup (Windows)

```powershell
pip install -r requirements.txt
winget install Gyan.FFmpeg          # audio + video
winget install JohnMacFarlane.Pandoc # markdown / html / epub / docx
winget install TheDocumentFoundation.LibreOffice  # office docs + PDF export
```

Only the formats whose tools are installed appear in the ring, so you can start with just `pip install` (images + spreadsheets/CSV/JSON work immediately).

## Run

```powershell
python main.py
```

- A tray icon and a small orange **⇄ drop circle** appear. Drag any file onto the circle, or double-click it to browse.
- The ring of target formats opens at your cursor. Click one (or press 1-9). Esc / right-click / click outside cancels.
- The converted file is saved next to the original; click the "Done" notification to open the folder.

## Explorer right-click entry

```powershell
python register_context_menu.py            # add
python register_context_menu.py --remove   # remove
```

Right-click any file -> **Convert with RadialConvert** (Windows 11: under "Show more options"). The ring opens at the cursor.

## What converts to what

| Input | Outputs | Backend |
|---|---|---|
| png jpg webp bmp gif tiff ico | png jpg webp bmp gif tiff ico pdf | Pillow |
| mp3 wav flac ogg m4a aac wma opus | mp3 wav flac ogg m4a aac | ffmpeg |
| mp4 mkv webm avi mov flv wmv | mp4 mkv webm avi mov gif mp3 | ffmpeg |
| md html txt rtf epub | docx pdf html md txt epub odt | pandoc (+ LibreOffice for PDF) |
| doc docx odt ppt pptx odp | pdf docx odt txt html (md for docx/odt) | LibreOffice / pandoc |
| csv tsv json xls xlsx ods | csv xlsx json tsv pdf | pandas / LibreOffice |

## Adding a format

1. Add the extension to `KINDS` and target to `TARGETS` in `converter.py`.
2. Add a branch in `_tools_needed` and `convert` if it needs a new backend.

The menu picks it up automatically.

## Package as an .exe

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name RadialConvert main.py
```

## Ideas for next steps

- Global hotkey to open the menu for the file selected in Explorer
- PDF -> image/text (PyMuPDF), batch conversion, per-format quality settings
- Animated open/close and hover effects on the ring
