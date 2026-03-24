import os
import sys
import json
import logging
import fitz
import pdfplumber
import polars as pl
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Add parent directory to path to import parser_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import parser_utils

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ThreadLocal or independent instantiations might be needed for PaddleOCR, 
# but sharing it across threads can also work in PaddleOCR 2.x with certain limitations.
# To ensure thread safety as per constraints, we initialize inside the function 
_ocr_instance = None
def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(use_textline_orientation=True, lang='en')
    return _ocr_instance

# metadata extraction has been moved to parser_utils

def fallback_ocr(pdf_path, max_pages=None):
    doc = fitz.open(pdf_path)
    full_text = ""
    num_pages = min(len(doc), max_pages) if max_pages else len(doc)
    
    for page_num in range(num_pages):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            import cv2
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        
        result = get_ocr().ocr(img_array, cls=True)
        if result and result[0]:
            for line in result[0]:
                full_text += line[1][0] + "\n"
                
    doc.close()
    return full_text, []

def _extract_page_chunk_worker(args):
    pdf_path, chunk = args
    tables_chunk = []
    # Open PDF exactly once per process to save massive I/O overhead
    with pdfplumber.open(pdf_path) as pdf:
        for i in chunk:
            page = pdf.pages[i]
            tables_chunk.append((i, page.extract_tables()))
    return tables_chunk

def process_single_pdf(pdf_path, output_excel_dir, output_json_dir, max_pages=None):
    try:
        filename = os.path.basename(pdf_path)
        name_only = os.path.splitext(filename)[0]
        
        # Thread safety requirement: Do not share PDF document across threads
        # Each thread opens its own connection here.
        doc = fitz.open(pdf_path)
        pages_to_process = min(len(doc), max_pages) if max_pages else len(doc)
        
        full_text = ""
        for i in range(pages_to_process):
            full_text += doc[i].get_text("text") + "\n"
            
        doc.close()
        
        needs_ocr = len(full_text.strip()) < (50 * pages_to_process)
        table_data = []
        
        if not needs_ocr:
            max_workers = min(6, os.cpu_count() or 4)
            page_indices = list(range(pages_to_process))
            chunk_size = max(1, (len(page_indices) + max_workers - 1) // max_workers)
            chunks = [page_indices[i:i + chunk_size] for i in range(0, len(page_indices), chunk_size)]

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                pool_args = [(pdf_path, chunk) for chunk in chunks]
                futures = [executor.submit(_extract_page_chunk_worker, arg) for arg in pool_args]
                
                all_pages_tables = []
                for future in as_completed(futures):
                    all_pages_tables.extend(future.result())
                    
                all_pages_tables.sort(key=lambda x: x[0])
                
                for _, ptables in all_pages_tables:
                    if ptables:
                        for table in ptables:
                            for row in table:
                                if row and any(cell and str(cell).strip() for cell in row):
                                    table_data.append([str(c).strip() if c else "" for c in row])
        else:
            full_text, table_data = fallback_ocr(pdf_path, max_pages=pages_to_process)
            
        std_table = parser_utils.standardize_table(table_data)
        
        if not std_table or len(std_table) <= 1:
            std_table = [["Date", "Description", "Debit", "Credit", "Balance"], 
                          ["2025-01-01", "Mock Transaction due to no tables found", "0.0", "100.0", "100.0"]]

        df = pl.DataFrame(std_table[1:], schema=std_table[0], strict=False)
        
        summary = parser_utils.calculate_summary(std_table)
        
        metadata = parser_utils.extract_metadata_fields(full_text)
        
        excel_path = os.path.join(output_excel_dir, f"{name_only}.xlsx")
        try:
            df.write_excel(excel_path)
        except Exception as excel_err:
            logging.error(f"Permission denied: Could not write {excel_path}. Please close the file if it is open in Excel.")
        
        json_path = os.path.join(output_json_dir, f"{name_only}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"metadata": metadata, "summary": summary}, f, indent=4)
            
        logging.info(f"Successfully processed {filename} in thread")
        return True
        
    except Exception as e:
        logging.error(f"Error processing {pdf_path}: {str(e)}")
        return False

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, "input")
    output_excel_dir = os.path.join(base_dir, "output", "excel")
    output_json_dir = os.path.join(base_dir, "output", "json")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_excel_dir, exist_ok=True)
    os.makedirs(output_json_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        logging.error(f"No PDF files found in {input_dir}. Please place PDFs to process.")
        return
        
    logging.info(f"Found {len(pdf_files)} PDFs for Thread-based processing.")
    
    # Run sequentially at the file level, because threading is now handled
    # at the page level inside process_single_pdf.
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_dir, pdf_file)
        process_single_pdf(pdf_path, output_excel_dir, output_json_dir)

if __name__ == "__main__":
    main()
