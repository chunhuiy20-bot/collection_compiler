import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils.pdf.PdfUtils import PdfUtils

pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "4-3013-0003850747.pdf")
images = PdfUtils.pdf_to_single_jpg(pdf_path)

for img in images:
    print(img)
