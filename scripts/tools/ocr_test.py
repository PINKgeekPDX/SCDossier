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

        result = reader(image_path)

        if result is None:
            print("No text detected.")
            sys.exit(0)

        boxes, txts, scores = result

        if not txts or not scores:
            print("No text detected.")
            sys.exit(0)

        print(f"\nDetected {len(txts)} text regions:")
        print("-" * 60)
        for i, (text, conf) in enumerate(zip(txts, scores)):
            print(f"  [{i}] Text: '{text}'  |  Confidence: {conf:.3f}")
        print("-" * 60)

        # Best match
        best_idx = scores.index(max(scores))
        print(f"\nBest match: '{txts[best_idx]}' (conf: {scores[best_idx]:.3f})")

    except ImportError as e:
        print(f"Error: rapidocr_onnxruntime not installed. Run: pip install rapidocr-onnxruntime")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()