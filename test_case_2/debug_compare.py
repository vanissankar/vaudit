import camelot
import pdfplumber
import os

pdf_path = r"c:\Users\aniss\Desktop\New Report\test_case_2\Sequential\input\DepositAccountStatement-3_unlocked.pdf"

print("--- Camelot Stream ---")
try:
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
    print(f"Total Tables found: {len(tables)}")
    total_rows = sum(len(t.data) for t in tables)
    print(f"Total Rows found by Camelot: {total_rows}")
except Exception as e:
    print(f"Camelot error: {e}")

print("\n--- pdfplumber ---")
try:
    with pdfplumber.open(pdf_path) as pdf:
        pp_rows = 0
        for page in pdf.pages:
            ts = page.extract_tables()
            for t in ts:
                pp_rows += len(t)
        print(f"Total Rows found by pdfplumber: {pp_rows}")
except Exception as e:
    print(f"pdfplumber error: {e}")
