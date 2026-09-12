"""Generate a macOS .icns icon from the SeasonFall PNG (runs on any OS).

Modern macOS reads PNG-encoded icon chunks, so packing PNGs of the standard
sizes into an icns container produces a fully valid Finder/Dock icon.
"""
import io
import struct

from PIL import Image

SRC = "packaging/seasonfall.png"
OUT = "packaging/seasonfall.icns"

src = Image.open(SRC).convert("RGBA")

chunks = b""
for cid, size in ((b"ic07", 128), (b"ic08", 256), (b"ic09", 512)):
    img = src.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()
    chunks += cid + struct.pack(">I", len(data) + 8) + data

with open(OUT, "wb") as f:
    f.write(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)

print("wrote", OUT, len(chunks) + 8, "bytes")
