import re

# Possible headers for mapping
COLUMN_MAPPINGS = {
    "Date": ["Date", "Transaction Date", "Txn Date", "Tran Date", "Date of Transaction", "Transaction Dt", "Tran Dt", "Value Date", "Val Date", "Value Dt", "Settlement Date", "Settlement Dt", "Effective Date", "Effective Dt", "Posting Date", "Posted Date", "Posting Dt", "Post Date", "Booking Date", "Booking Dt", "Book Date", "Entry Date", "Entry Dt", "Record Date", "Recorded Date", "Processed Date", "Processing Date", "Process Date", "Cleared Date", "Clearing Date", "Clearance Date", "Dt", "Txn Dt", "Trn Dt", "Trx Date", "Trx Dt", "T Date", "Txn Date / Value Date", "Date / Value Date", "Transaction Date & Time", "Date Time", "Transaction DateTime"],
    "Description": ["Description", "Narration", "Particulars", "Details", "Transaction Details", "Transaction Description", "Transaction Particulars", "Transaction Narration", "Description/Narration", "Remarks", "Comment", "Comments", "Memo", "Transaction Memo", "Note", "Notes", "Reference", "Reference Details", "Payment Reference", "Transaction Reference", "Ref No", "Ref#", "Reference No", "Transaction Ref", "Transaction Ref No", "Cheque Details", "Cheque Particulars", "Instrument Details", "Instrument Number", "Instrument No", "Instrument Description", "Chq No", "Cheque No", "Check No", "Description of Transaction", "Payment Details", "Transfer Details", "Transaction Info", "Transaction Information", "Transaction Narrative", "Transaction Remark", "Transaction Note", "Payment Narration", "Debit Narration", "Credit Narration"],
    "Credit": ["Credit", "Credit Amount", "Credit Amt", "Deposit", "Deposits", "Deposit Amount", "Deposit Amt", "Deposited", "Cr", "Cr.", "CR", "Cr Amount", "CR Amount", "Credit Value", "Credit Value Date", "Credit Transaction", "Credit Txn", "Credit Entry", "Credit Amount (INR)", "Amount Credited", "Amount Credit", "Amt Credited", "Incoming Amount", "Incoming Funds", "Funds In", "Money In", "Receipt", "Receipts", "Received Amount", "Payment Received", "Transfer In", "NEFT Credit", "IMPS Credit", "RTGS Credit", "UPI Credit", "Bank Credit", "Credit Transaction Amount", "Credit Value Amount", "Credit (INR)", "Deposit (INR)", "Amount (Credit)", "Credit Amount (Cr)", "Credit Value", "Credit Total"],
    "Debit": ["Debit", "Debit Amount", "Debit Amt", "Withdrawal", "Withdrawals", "Withdrawal Amount", "Withdrawal Amt", "Withdrawn", "Dr", "Dr.", "DR", "Dr Amount", "DR Amount", "Debit Value", "Debit Transaction", "Debit Txn", "Debit Entry", "Debit Amount (INR)", "Amount Debited", "Amount Debit", "Amt Debited", "Outgoing Amount", "Outgoing Funds", "Funds Out", "Money Out", "Payment", "Payments", "Paid Amount", "Payment Made", "Transfer Out", "NEFT Debit", "IMPS Debit", "RTGS Debit", "UPI Debit", "Bank Debit", "Debit Transaction Amount", "Debit Value Amount", "Debit (INR)", "Withdrawal (INR)", "Amount (Debit)", "Debit Amount (Dr)", "Debit Total"],
    "Balance": ["Balance", "Closing Balance", "Running Balance", "Available Balance", "Ledger Balance", "Account Balance", "Current Balance", "Balance Amount", "Balance Amt", "Balance (INR)", "Bal", "Bal.", "BAL", "Balance After Transaction", "Transaction Balance", "Available Bal", "Ledger Bal", "Closing Bal", "Current Bal", "Net Balance", "Net Bal", "Account Bal", "Remaining Balance", "Remaining Bal", "Balance Forward", "Balance B/F", "Balance C/F", "Final Balance"]
}

METADATA_MAPPINGS = {
    "Bank Name": ["Bank Name", "Bank", "Bank Name / Branch", "Branch Bank", "Issuing Bank", "Bank Details", "Bank Information", "Banking Institution", "Bank Name & Branch", "Bank & Branch", "Bank Name (Branch)", "Branch Bank Name", "Branch of Bank", "Bank Identification", "Bank Identifier", "Banking Entity", "Bank Title"],
    "Account Holder Name": ["Account Holder", "Account Name", "Name", "Customer Name", "Account Holder Name", "Name of Account Holder", "Account Title", "Customer", "Client Name", "Name as per Bank", "Account Owner", "Beneficiary Name", "Name (Account Holder)", "Holder Name", "Account Holder Details"],
    "Account Number": ["Account Number", "Account No", "A/C No", "A/C Number", "A/C No.", "Account Number.", "Account #", "Account ID", "Customer Account Number", "Bank Account Number", "Account Identifier", "Account Reference Number", "Account Code", "Customer Account ID", "A/c No", "Ac No"],
    "IFSC Code": ["IFSC", "IFSC Code", "IFSC No", "IFSC Number", "IFSC Identifier", "IFSC Branch Code", "Bank IFSC", "IFSC Code (Branch)", "Branch IFSC Code", "Bank Routing Code", "Routing Code", "Electronic Clearing Code"],
    "Branch Name": ["Branch", "Branch Name", "Branch Office", "Branch Location", "Branch Address", "Bank Branch", "Branch Details", "Home Branch", "Servicing Branch", "Branch Code & Name", "Branch Office Name", "Branch Identifier", "Branch Location Name"],
    "Statement Date": ["Statement Date", "Statement Generated On", "Statement Period End", "Statement Issued Date", "Date of Statement", "Report Date", "Statement Generated Date", "Statement As On Date"]
}

def clean_text_for_matching(text):
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def get_standard_column(header):
    header_clean = clean_text_for_matching(header)
    for std_name, variations in COLUMN_MAPPINGS.items():
        if any(clean_text_for_matching(var) == header_clean for var in variations):
            return std_name
    return None

def standardize_table(raw_data):
    """
    Finds the header row, normalizes columns to Date, Description, Credit, Debit, Balance.
    Returns standard rows and discards earlier lines.
    """
    if not raw_data: return []
    
    header_idx = -1
    col_mapping = {}  # original_idx -> Standard Name
    
    for idx, row in enumerate(raw_data):
        found_std_cols = {}
        for c_idx, cell in enumerate(row):
            std = get_standard_column(cell)
            if std:
                found_std_cols[c_idx] = std
        
        # Consider it a header row if it has at least 3 recognizable columns (Date, Desc, Amount/Bal)
        if len(found_std_cols) >= 3:
            header_idx = idx
            col_mapping = found_std_cols
            break
            
    if header_idx == -1:
        # Fallback if no header found or recognized
        return []
        
    extracted_data = []
    # Add standard header
    extracted_data.append(["Date", "Description", "Debit", "Credit", "Balance"])
    
    # Process data rows
    for row in raw_data[header_idx + 1:]:
        standard_row = {"Date": "", "Description": "", "Debit": "", "Credit": "", "Balance": ""}
        empty_row = True
        
        for c_idx, std_name in col_mapping.items():
            if c_idx < len(row):
                val = str(row[c_idx]).strip()
                if val:
                    empty_row = False
                    standard_row[std_name] = val
                    
        # Many statements have a single "Amount" col, but the prompt separates Credit/Debit globally.
        # If columns mix, we rely on mapping. The prompt explicitly separated Credit vs Debit possibilities.
        if not empty_row:
            extracted_data.append([
                standard_row["Date"], standard_row["Description"], 
                standard_row["Debit"], standard_row["Credit"], standard_row["Balance"]
            ])
            
    return extracted_data

def extract_metadata_fields(full_text):
    """
    Searches the full text for metadata fields using variations.
    """
    metadata = {
        "Bank Name": "UNKNOWN",
        "Account Holder Name": "UNKNOWN",
        "Account Number": "UNKNOWN",
        "IFSC Code": "UNKNOWN",
        "Branch Name": "UNKNOWN",
        "Statement Date": "UNKNOWN"
    }
    
    lines = full_text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        
        for std_key, variations in METADATA_MAPPINGS.items():
            if metadata[std_key] != "UNKNOWN":
                continue # Already found
                
            for var in variations:
                # Look for "Header: Value" or "Header Value"
                pattern = r'(?i)\b' + re.escape(var) + r'\b[:\-\s]+(.*)'
                match = re.search(pattern, line_clean)
                if match:
                    val = match.group(1).strip()
                    if val:
                        metadata[std_key] = val
                        break
                        
    return metadata

def calculate_summary(std_table):
    if not std_table or len(std_table) <= 1:
        return {"total_debit": 0.0, "total_credit": 0.0, "number_of_transactions": 0, "final_balance": 0.0}

    header = std_table[0]
    try:
        debit_idx = header.index("Debit")
        credit_idx = header.index("Credit")
        balance_idx = header.index("Balance")
    except ValueError:
        return {"total_debit": 0.0, "total_credit": 0.0, "number_of_transactions": 0, "final_balance": 0.0}

    total_debit = 0.0
    total_credit = 0.0
    final_balance = 0.0

    def parse_amount(val):
        if not val: return 0.0
        # Remove commas, currency symbols, and spaces
        clean_str = re.sub(r'[^\d\.\-]', '', str(val))
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    for row in std_table[1:]:
        d_val = parse_amount(row[debit_idx] if debit_idx < len(row) else "")
        c_val = parse_amount(row[credit_idx] if credit_idx < len(row) else "")
        raw_b = row[balance_idx] if balance_idx < len(row) else ""
        b_val = parse_amount(raw_b)
        
        total_debit += d_val
        total_credit += c_val
        
        if b_val != 0.0 or str(raw_b).strip() in ["0", "0.0", "0.00"]:
            final_balance = b_val

    return {
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "number_of_transactions": len(std_table) - 1,
        "final_balance": round(final_balance, 2)
    }
