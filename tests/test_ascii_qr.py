"""Smoke test for ASCII QR generation pipeline."""
import io
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode


def test_ascii_qr_roundtrip():
    """Generate QR PNG → decode with pyzbar → regenerate as ASCII."""
    # 1. Generate a test QR code PNG
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data("https://example.com/test-qr")
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # 2. Decode with pyzbar
    img2 = Image.open(io.BytesIO(png_bytes))
    decoded = pyzbar_decode(img2)
    assert len(decoded) > 0, "pyzbar should decode the QR code"
    assert decoded[0].data.decode("utf-8") == "https://example.com/test-qr"

    # 3. Re-encode as ASCII using half-block chars
    qr2 = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=1,
    )
    qr2.add_data(decoded[0].data.decode("utf-8"))
    qr2.make(fit=True)
    modules = qr2.get_matrix()
    lines = []
    for r in range(0, len(modules), 2):
        line = ""
        for c in range(len(modules[0])):
            top = modules[r][c]
            bot = modules[r + 1][c] if r + 1 < len(modules) else False
            if top and bot:
                line += "█"
            elif top and not bot:
                line += "▀"
            elif not top and bot:
                line += "▄"
            else:
                line += " "
        lines.append(line)

    ascii_qr = "\n".join(lines)
    assert len(ascii_qr) > 50, "ASCII QR should have meaningful content"
    assert "█" in ascii_qr, "ASCII QR should contain block characters"
    print(ascii_qr)
    print("✅ ASCII QR generation works!")


def test_generate_ascii_qr_method():
    """Test XiaohongshuPublisher._generate_ascii_qr with real PNG."""
    from app.services.xiaohongshu_publisher import XiaohongshuPublisher

    # Generate a test PNG
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data("https://www.xiaohongshu.com/login/qr/test")
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = XiaohongshuPublisher._generate_ascii_qr(buf.getvalue())
    assert result is not None, "_generate_ascii_qr should return ASCII art"
    assert "█" in result
    print(result)


def test_generate_ascii_qr_bad_input():
    """_generate_ascii_qr should return None for invalid input."""
    from app.services.xiaohongshu_publisher import XiaohongshuPublisher

    result = XiaohongshuPublisher._generate_ascii_qr(b"not-a-png")
    assert result is None


if __name__ == "__main__":
    test_ascii_qr_roundtrip()
    test_generate_ascii_qr_method()
    test_generate_ascii_qr_bad_input()
    print("\n✅ All tests passed!")
