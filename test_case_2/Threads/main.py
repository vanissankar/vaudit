import os
import glob
import json
import fitz  # PyMuPDF
import re
import camelot
import polars as pl
import xlsxwriter
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from concurrent.futures import ThreadPoolExecutor

INPUT_DIR = os.path.join(os.path.dirname(__file__), "input")
EXCEL_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "excel")
JSON_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "json")

os.makedirs(EXCEL_OUTPUT_DIR, exist_ok=True)
os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)

DATE_HEADERS    = [h.strip().lower() for h in "Date, Transaction Date, Txn Date, Tran Date, Date of Transaction, Transaction Dt, Tran Dt, Value Date, Val Date, Value Dt, Settlement Date, Settlement Dt, Effective Date, Effective Dt, Posting Date, Posted Date, Posting Dt, Post Date, Booking Date, Booking Dt, Book Date, Entry Date, Entry Dt, Record Date, Recorded Date, Processed Date, Processing Date, Process Date, Cleared Date, Clearing Date, Clearance Date, Dt, Txn Dt, Trn Dt, Trx Date, Trx Dt, T Date, Txn Date / Value Date, Date / Value Date, Transaction Date & Time, Date Time, Transaction DateTime".split(',')]
DESC_HEADERS    = [h.strip().lower() for h in "Description, Narration, Particulars, Details, Transaction Details, Transaction Description, Transaction Particulars, Transaction Narration, Description/Narration, Remarks, Comment, Comments, Memo, Transaction Memo, Note, Notes, Reference, Reference Details, Payment Reference, Transaction Reference, Ref No, Ref#, Reference No, Transaction Ref, Transaction Ref No, Cheque Details, Cheque Particulars, Instrument Details, Instrument Number, Instrument No, Instrument Description, Chq No, Cheque No, Check No, Description of Transaction, Payment Details, Transfer Details, Transaction Info, Transaction Information, Transaction Narrative, Transaction Remark, Transaction Note, Payment Narration, Debit Narration, Credit Narration".split(',')]
CREDIT_HEADERS  = [h.strip().lower() for h in "Credit, Credit Amount, Credit Amt, Deposit, Deposits, Deposit Amount, Deposit Amt, Deposited, Cr, Cr., CR, Cr Amount, CR Amount, Credit Value, Credit Value Date, Credit Transaction, Credit Txn, Credit Entry, Credit Amount (INR), Amount Credited, Amount Credit, Amt Credited, Incoming Amount, Incoming Funds, Funds In, Money In, Receipt, Receipts, Received Amount, Payment Received, Transfer In, NEFT Credit, IMPS Credit, RTGS Credit, UPI Credit, Bank Credit, Credit Transaction Amount, Credit Value Amount, Credit (INR), Deposit (INR), Amount (Credit), Credit Amount (Cr), Credit Transaction Amount, Credit Value, Credit Total".split(',')]
DEBIT_HEADERS   = [h.strip().lower() for h in "Debit, Debit Amount, Debit Amt, Withdrawal, Withdrawals, Withdrawal Amount, Withdrawal Amt, Withdrawn, Dr, Dr., DR, Dr Amount, DR Amount, Debit Value, Debit Transaction, Debit Txn, Debit Entry, Debit Amount (INR), Amount Debited, Amount Debit, Amt Debited, Outgoing Amount, Outgoing Funds, Funds Out, Money Out, Payment, Payments, Paid Amount, Payment Made, Transfer Out, NEFT Debit, IMPS Debit, RTGS Debit, UPI Debit, Bank Debit, Debit Transaction Amount, Debit Value Amount, Debit (INR), Withdrawal (INR), Amount (Debit), Debit Amount (Dr), Debit Total".split(',')]
BALANCE_HEADERS = [h.strip().lower() for h in "Balance, Closing Balance, Running Balance, Available Balance, Ledger Balance, Account Balance, Current Balance, Balance Amount, Balance Amt, Balance (INR), Bal, Bal., BAL, Balance After Transaction, Transaction Balance, Available Bal, Ledger Bal, Closing Bal, Current Bal, Net Balance, Net Bal, Account Bal, Remaining Balance, Remaining Bal, Balance Forward, Balance B/F, Balance C/F, Final Balance".split(',')]

BANK_NAME_OPTS       = [h.strip().lower() for h in "Bank Name, Bank, Bank Name / Branch, Branch Bank, Issuing Bank, Bank Details, Bank Information, Banking Institution, Bank Name & Branch, Bank & Branch, Bank Name (Branch), Branch Bank Name, Branch of Bank, Bank Identification, Bank Identifier, Banking Entity, Bank Title".split(',')]
ACCOUNT_HOLDER_OPTS  = [h.strip().lower() for h in "Account Holder, Account Name, Name, Customer Name, Account Holder Name, Name of Account Holder, Account Title, Customer, Client Name, Name as per Bank, Account Owner, Beneficiary Name, Name (Account Holder), Holder Name, Account Holder Details".split(',')]
ACCOUNT_NUMBER_OPTS  = [h.strip().lower() for h in "Account Number, Account No, A/C No, A/C Number, A/C No., Account Number., Account #, Account ID, Customer Account Number, Bank Account Number, Account Identifier, Account Reference Number, Account Code, Customer Account ID, A/c No, Ac No".split(',')]
IFSC_OPTS            = [h.strip().lower() for h in "IFSC, IFSC Code, IFSC No, IFSC Number, IFSC Identifier, IFSC Branch Code, Bank IFSC, IFSC Code (Branch), Branch IFSC Code, Bank Routing Code, Routing Code, Electronic Clearing Code".split(',')]
BRANCH_OPTS          = [h.strip().lower() for h in "Branch, Branch Name, Branch Office, Branch Location, Branch Address, Bank Branch, Branch Details, Home Branch, Servicing Branch, Branch Code & Name, Branch Office Name, Branch Identifier, Branch Location Name".split(',')]
STATEMENT_DATE_OPTS  = [h.strip().lower() for h in "Statement Date, Statement Generated On, Statement Period End, Statement Issued Date, Date of Statement, Report Date, Statement Generated Date, Statement As On Date".split(',')]

_doctr_predictor = None


def get_doctr_predictor():
    global _doctr_predictor
    if _doctr_predictor is None:
        _doctr_predictor = ocr_predictor(pretrained=True)
    return _doctr_predictor


def extract_metadata_from_text(text):
    data = {"Bank Name": "", "Account Holder Name": "", "Account Number": "",
            "IFSC Code": "", "Branch Name": "", "Statement Date": ""}

    acc_match = re.search(r'(?i)(?:A/c No\.|Account\s*No\.?|Account\s*Number)\s*[:\-]?\s*(\d{9,18})', text)
    if acc_match:
        data["Account Number"] = acc_match.group(1)

    ifsc_match = re.search(r'(?i)(?:IFSC|RTGS/NEFT IFSC|IFSC Code)\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})', text)
    if ifsc_match:
        data["IFSC Code"] = ifsc_match.group(1)

    date_match = re.search(r'(?i)(?:Statement\s*Date|Date|Period)\s*[:\-]?\s*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})', text)
    if date_match:
        data["Statement Date"] = date_match.group(1)

    lines = text.split('\n')
    for i, line in enumerate(lines):
        lx = line.strip().lower()
        if not lx:
            continue

        def get_val(key_opt):
            if lx.startswith(key_opt):
                raw = line[len(key_opt):].strip()
                if raw.startswith(':') or raw.startswith('-'):
                    raw = raw[1:].strip()
                if raw:
                    return raw
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
            return None

        for opt in BANK_NAME_OPTS:
            v = get_val(opt)
            if v and not data["Bank Name"]: data["Bank Name"] = v
        for opt in ACCOUNT_HOLDER_OPTS:
            v = get_val(opt)
            if v and not data["Account Holder Name"]: data["Account Holder Name"] = v
        for opt in ACCOUNT_NUMBER_OPTS:
            v = get_val(opt)
            if v and not data["Account Number"]: data["Account Number"] = v
        for opt in IFSC_OPTS:
            v = get_val(opt)
            if v and not data["IFSC Code"]: data["IFSC Code"] = v
        for opt in BRANCH_OPTS:
            v = get_val(opt)
            if v and not data["Branch Name"]: data["Branch Name"] = v
        for opt in STATEMENT_DATE_OPTS:
            v = get_val(opt)
            if v and not data["Statement Date"]: data["Statement Date"] = v

    return data


def normalize_transactions(tables):
    """
    Global-flatten approach:
      1. Concatenate every row from every Camelot table into one stream.
      2. Find the FIRST header row (requiring >= 3 matched column types).
      3. Build a header signature to skip repeated headers on subsequent pages.
      4. Map each data row to [Date, Description, Credit, Debit, Balance].
      5. Collapse orphan continuation lines into the previous row's description.
    """
    standard_columns = ["Date", "Description", "Credit", "Debit", "Balance"]

    def clean_header(txt):
        return re.sub(r'[^a-zA-Z0-9]', '', str(txt)).lower()

    def is_date(s):
        return bool(re.search(r'\d{2}[/\-]\d{2}[/\-]\d{4}|\d{2}[/\-]\d{2}[/\-]\d{2}', str(s)))

    date_h_clean    = [clean_header(h) for h in DATE_HEADERS]
    desc_h_clean    = [clean_header(h) for h in DESC_HEADERS]
    credit_h_clean  = [clean_header(h) for h in CREDIT_HEADERS]
    debit_h_clean   = [clean_header(h) for h in DEBIT_HEADERS]
    balance_h_clean = [clean_header(h) for h in BALANCE_HEADERS]

    # ── 1. Flatten all tables → one list of raw rows ──────────────────────────
    raw_rows = []
    for table in tables:
        for row in table.data:
            cleaned = [str(c).replace('\n', ' ').strip() for c in row]
            if any(cleaned):
                raw_rows.append(cleaned)

    if not raw_rows:
        return []

    # ── 2. Locate the first header row ───────────────────────────────────────
    col_map = {}
    header_row_idx = -1

    for i, row in enumerate(raw_rows):
        tmp = {}
        hits = 0
        for j, cell in enumerate(row):
            v = clean_header(cell)
            if not v:
                continue
            if   v in date_h_clean    and "Date"        not in tmp: tmp["Date"]        = j; hits += 1
            elif v in desc_h_clean    and "Description" not in tmp: tmp["Description"] = j; hits += 1
            elif v in credit_h_clean  and "Credit"      not in tmp: tmp["Credit"]      = j; hits += 1
            elif v in debit_h_clean   and "Debit"       not in tmp: tmp["Debit"]       = j; hits += 1
            elif v in balance_h_clean and "Balance"     not in tmp: tmp["Balance"]     = j; hits += 1

        if hits >= 3:
            col_map = tmp
            header_row_idx = i
            break

    if not col_map:
        return []

    # Build a signature of the header cell values to detect repeats
    hdr = raw_rows[header_row_idx]
    header_sig = tuple(clean_header(hdr[j]) for j in sorted(col_map.values()) if j < len(hdr))

    # ── 3. Convert every data row after the header ────────────────────────────
    all_rows = []
    for row in raw_rows[header_row_idx + 1:]:
        # Skip any row that matches the header signature (page-repeat)
        row_sig = tuple(clean_header(row[j]) for j in sorted(col_map.values()) if j < len(row))
        if row_sig == header_sig:
            continue

        std_row = ["", "", "", "", ""]
        for col_name in standard_columns:
            if col_name in col_map:
                idx = col_map[col_name]
                if idx < len(row):
                    std_row[standard_columns.index(col_name)] = row[idx]

        if any(std_row):
            all_rows.append(std_row)

    # ── 4. Collapse multi-line orphaned description continuations ─────────────
    merged_rows = []
    for r in all_rows:
        is_orphan = (not is_date(r[0])
                     and not r[2] and not r[3] and not r[4]
                     and bool(r[1]))
        if is_orphan and merged_rows:
            merged_rows[-1][1] += " " + r[1]
        else:
            merged_rows.append(r)

    return merged_rows


def parse_float(val):
    s = str(val).replace(',', '').replace(' ', '')
    m = re.search(r'-?\d+\.\d+|-?\d+', s)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None


def process_pdf(filepath):
    filename = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]
    print(f"Threads: Processing {filename}")

    metadata = {"filename": filename, "page_count": 0, "ocr_used": False}
    with fitz.open(filepath) as doc:
        metadata["page_count"] = len(doc)
        if len(doc) > 0:
            metadata.update(extract_metadata_from_text(doc[0].get_text()))

    tables = []
    try:
        tables = camelot.read_pdf(filepath, pages='all', flavor='stream')
    except Exception as e:
        print(f"Camelot exception on {filename}: {e}")

    transactions = normalize_transactions(tables)

    if not transactions:
        metadata["ocr_used"] = True
        print(f"Fallback to docTR OCR for {filename}")
        predictor = get_doctr_predictor()
        doc_doctr = DocumentFile.from_pdf(filepath)
        result = predictor(doc_doctr)
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    text = " ".join([word.value for word in line.words])
                    transactions.append([text, "", "", "", ""])

    if not transactions:
        transactions = [["No data", "No data", "", "", ""]]

    df_pl = pl.DataFrame(transactions, schema=["Date", "Description", "Credit", "Debit", "Balance"], orient="row")

    # ── Ledger-based summary ─────────────────────────────────────────────────
    total_debit     = 0.0
    total_credit    = 0.0
    opening_balance = None
    real_tx_count   = 0

    for row in transactions:
        if len(row) < 5:
            continue
        desc_padded = " " + re.sub(r'\s+', ' ', str(row[1]).lower()) + " "
        is_opening = any(x in desc_padded for x in
                         [" brought forward ", " opening balance ", " b/f ", " balance b/f "])
        is_closing = any(x in desc_padded for x in
                         [" carried forward ", " closing balance ", " c/f ", " balance c/f "])

        c_val = parse_float(row[2])
        d_val = parse_float(row[3])
        b_val = parse_float(row[4])

        if is_opening:
            if b_val is not None:   opening_balance = b_val
            elif c_val is not None: opening_balance = c_val
            elif d_val is not None: opening_balance = -d_val
            continue

        if is_closing:
            continue

        actual_c = c_val if c_val is not None else 0.0
        actual_d = d_val if d_val is not None else 0.0

        if actual_c > 0 or actual_d > 0 or b_val is not None:
            real_tx_count += 1

        if opening_balance is None and b_val is not None:
            opening_balance = b_val - actual_c + actual_d

        total_credit += actual_c
        total_debit  += actual_d

    if opening_balance is None:
        opening_balance = 0.0

    calculated_balance = opening_balance + total_credit - total_debit

    summary = {
        "debit":              round(total_debit,          2),
        "credit":             round(total_credit,         2),
        "transactions_count": real_tx_count,
        "balance":            round(calculated_balance,   2),
    }

    # ── Excel output ─────────────────────────────────────────────────────────
    excel_path = os.path.join(EXCEL_OUTPUT_DIR, f"{name_no_ext}.xlsx")
    try:
        workbook  = xlsxwriter.Workbook(excel_path)
        worksheet = workbook.add_worksheet()
        bold      = workbook.add_format({'bold': True})

        meta_fields = [
            ("Bank Name",          metadata.get("Bank Name",          "")),
            ("Account Holder Name",metadata.get("Account Holder Name","")),
            ("Account Number",     metadata.get("Account Number",     "")),
            ("IFSC Code",          metadata.get("IFSC Code",          "")),
            ("Branch Name",        metadata.get("Branch Name",        "")),
            ("Statement Date",     metadata.get("Statement Date",     "")),
        ]
        for row_num, (label, value) in enumerate(meta_fields):
            worksheet.write(row_num, 0, label, bold)
            worksheet.write(row_num, 1, value)

        headers = ["Date", "Description", "Credit", "Debit", "Balance"]
        for col_num, h in enumerate(headers):
            worksheet.write(7, col_num, h, bold)

        for row_num, row_data in enumerate(transactions):
            for col_num, cell_data in enumerate(row_data):
                worksheet.write(row_num + 8, col_num, str(cell_data))

        workbook.close()
    except Exception as e:
        print(f"Warning: Could not write Excel file (is it open?): {e}")

    # ── JSON output ──────────────────────────────────────────────────────────
    json_path = os.path.join(JSON_OUTPUT_DIR, f"{name_no_ext}.json")
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump({"metadata": metadata, "summary": summary}, f, indent=4)

    return True



def process_single_pdf(filepath, excel_dir=None, json_dir=None, pages=None):
    """Benchmark-friendly entry point. pages=N limits processing to first N pages."""
    import tempfile

    if excel_dir is None: excel_dir = EXCEL_OUTPUT_DIR
    if json_dir  is None: json_dir  = JSON_OUTPUT_DIR
    os.makedirs(excel_dir, exist_ok=True)
    os.makedirs(json_dir,  exist_ok=True)

    filename    = os.path.basename(filepath)
    name_no_ext = os.path.splitext(filename)[0]
    print(f"Threads: Processing {filename} (pages={pages or 'all'})")

    work_path = filepath
    tmp_file  = None
    if pages is not None:
        tmp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_file.close()
        with fitz.open(filepath) as src:
            sub = fitz.open()
            for i in range(min(pages, len(src))):
                sub.insert_pdf(src, from_page=i, to_page=i)
            sub.save(tmp_file.name)
            sub.close()
        work_path = tmp_file.name

    try:
        metadata = {"filename": filename, "page_count": 0, "ocr_used": False}
        with fitz.open(work_path) as doc:
            metadata["page_count"] = len(doc)
            if len(doc) > 0:
                metadata.update(extract_metadata_from_text(doc[0].get_text()))

        tables = []
        try:
            tables = camelot.read_pdf(work_path, pages='all', flavor='stream')
        except Exception as e:
            print(f"Camelot exception: {e}")

        transactions = normalize_transactions(tables)

        if not transactions:
            metadata["ocr_used"] = True
            predictor = get_doctr_predictor()
            doc_doctr = DocumentFile.from_pdf(work_path)
            result    = predictor(doc_doctr)
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        text = " ".join([word.value for word in line.words])
                        transactions.append([text, "", "", "", ""])

        if not transactions:
            transactions = [["No data", "No data", "", "", ""]]

        total_debit     = 0.0
        total_credit    = 0.0
        opening_balance = None
        real_tx_count   = 0

        for row in transactions:
            if len(row) < 5: continue
            desc_padded = " " + re.sub(r'\s+', ' ', str(row[1]).lower()) + " "
            is_opening = any(x in desc_padded for x in
                             [" brought forward ", " opening balance ", " b/f ", " balance b/f "])
            is_closing = any(x in desc_padded for x in
                             [" carried forward ", " closing balance ", " c/f ", " balance c/f "])
            c_val = parse_float(row[2]); d_val = parse_float(row[3]); b_val = parse_float(row[4])
            if is_opening:
                if b_val is not None: opening_balance = b_val
                elif c_val is not None: opening_balance = c_val
                elif d_val is not None: opening_balance = -d_val
                continue
            if is_closing: continue
            actual_c = c_val if c_val is not None else 0.0
            actual_d = d_val if d_val is not None else 0.0
            if actual_c > 0 or actual_d > 0 or b_val is not None: real_tx_count += 1
            if opening_balance is None and b_val is not None:
                opening_balance = b_val - actual_c + actual_d
            total_credit += actual_c; total_debit += actual_d

        if opening_balance is None: opening_balance = 0.0
        calculated_balance = opening_balance + total_credit - total_debit
        summary = {
            "debit":              round(total_debit,        2),
            "credit":             round(total_credit,       2),
            "transactions_count": real_tx_count,
            "balance":            round(calculated_balance, 2),
        }

        excel_path = os.path.join(excel_dir, f"{name_no_ext}.xlsx")
        try:
            workbook  = xlsxwriter.Workbook(excel_path)
            worksheet = workbook.add_worksheet()
            bold      = workbook.add_format({'bold': True})
            for row_num, (label, value) in enumerate([
                ("Bank Name",          metadata.get("Bank Name",          "")),
                ("Account Holder Name",metadata.get("Account Holder Name","")),
                ("Account Number",     metadata.get("Account Number",     "")),
                ("IFSC Code",          metadata.get("IFSC Code",          "")),
                ("Branch Name",        metadata.get("Branch Name",        "")),
                ("Statement Date",     metadata.get("Statement Date",     "")),
            ]):
                worksheet.write(row_num, 0, label, bold)
                worksheet.write(row_num, 1, value)
            for col_num, h in enumerate(["Date", "Description", "Credit", "Debit", "Balance"]):
                worksheet.write(7, col_num, h, bold)
            for row_num, row_data in enumerate(transactions):
                for col_num, cell_data in enumerate(row_data):
                    worksheet.write(row_num + 8, col_num, str(cell_data))
            workbook.close()
        except Exception as e:
            print(f"Warning: Could not write Excel file: {e}")

        json_path = os.path.join(json_dir, f"{name_no_ext}.json")
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump({"metadata": metadata, "summary": summary}, f, indent=4)

    finally:
        if tmp_file and os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)

    return True


def main():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    pdfs = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {INPUT_DIR}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(process_single_pdf, pdfs))


if __name__ == '__main__':
    main()
