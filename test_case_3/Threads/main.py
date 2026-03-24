import os
import sys
import glob
import re
import fitz
from concurrent.futures import ThreadPoolExecutor

# Add engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from engine.extractor import extract_words_from_pdf
from engine.row_builder import group_words_into_rows
from engine.parser import parse_row_with_coords, is_date, parse_amount
from engine.detector import extract_metadata
from engine.exporter import export_to_excel, export_to_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
EXCEL_OUTPUT_DIR = os.path.join(BASE_DIR, "output", "excel")
JSON_OUTPUT_DIR = os.path.join(BASE_DIR, "output", "json")

def process_single_pdf(filepath, excel_dir=None, json_dir=None, pages=None):
    """
    Main extraction pipeline for a single PDF - Thread Safe.
    Each thread opens its own document.
    """
    if excel_dir is None: excel_dir = EXCEL_OUTPUT_DIR
    if json_dir is None: json_dir = JSON_OUTPUT_DIR
    os.makedirs(excel_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]
    
    # 1. Extraction (Word-level)
    all_pages_words = []
    # Each thread MUST open its own handle
    with fitz.open(filepath) as doc:
        first_page_text = doc[0].get_text()
        metadata = extract_metadata(first_page_text)
        metadata["filename"] = filename
        metadata["page_count"] = len(doc)
        
        max_p = min(pages, len(doc)) if pages else len(doc)
        for i in range(max_p):
            all_pages_words.append(doc[i].get_text_words())

    # 2. Row Building & Parsing
    all_transactions = []
    for page_words in all_pages_words:
        rows = group_words_into_rows(page_words)
        for row_words in rows:
            parsed_cols = parse_row_with_coords(row_words)
            if is_date(parsed_cols[0]):
                all_transactions.append(parsed_cols)
            elif all_transactions and parsed_cols[2]:
                # Description continuation
                all_transactions[-1][2] += " " + parsed_cols[2]

    # 3. Summary
    total_debit = 0.0
    total_credit = 0.0
    for row in all_transactions:
        d = parse_amount(row[3])
        c = parse_amount(row[4])
        if d: total_debit += d
        if c: total_credit += c
        
    final_balance = 0.0
    if all_transactions:
        last_b = parse_amount(all_transactions[-1][5])
        if last_b is not None:
            final_balance = last_b

    summary = {
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "number_of_transactions": len(all_transactions),
        "final_balance": final_balance
    }

    # 4. Export
    excel_path = os.path.join(excel_dir, f"{name_no_ext}.xlsx")
    json_path = os.path.join(json_dir, f"{name_no_ext}.json")
    
    export_to_excel(all_transactions, metadata, excel_path)
    export_to_json(metadata, summary, json_path)
    
    return True

def main():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    
    pdfs = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdfs:
        print(f"WARNING: No PDFs found in {INPUT_DIR}")
        return

    # Use ThreadPoolExecutor for concurrent processing
    # Max workers 4-6 as requested
    with ThreadPoolExecutor(max_workers=6) as executor:
        executor.map(process_single_pdf, pdfs)

if __name__ == "__main__":
    main()
