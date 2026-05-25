"""
scripts/tools/ocr_test.py
OCR validation tool — runs RapidOCR on a test image and prints results.

Usage:
    python scripts/tools/ocr_test.py <image_path>
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_test.py <image_path>")
        print("Example: python ocr_test.py test_capture.png")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    try:
        from rapidocr_onnxruntime import RapidOCR
        reader = RapidOCR()
        print(f"RapidOCR engine initialized.")
        print(f"Processing: {image_path}")

        output = reader(image_path)

        if output is None or not output[0]:
            print("No text detected.")
            sys.exit(0)

        result, elapse = output

        print(f"\nDetected {len(result)} text regions:")
        print("-" * 60)
        best_text = ""
        best_conf = -1.0
        for i, entry in enumerate(result):
            if len(entry) >= 3:
                box, text, conf = entry[0], entry[1], entry[2]
                print(f"  [{i}] Text: '{text}'  |  Confidence: {conf:.3f}")
                if conf > best_conf:
                    best_conf = conf
                    best_text = text
        print("-" * 60)

        # Best match
        if best_conf >= 0.0:
            print(f"\nBest match: '{best_text}' (conf: {best_conf:.3f})")

    except ImportError as e:
        print(f"Error: rapidocr_onnxruntime not installed. Run: pip install rapidocr-onnxruntime")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()