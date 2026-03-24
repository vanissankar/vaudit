import re

def is_date(text):
    """Checks if text looks like a date (dd/mm/yyyy or dd-mm-yyyy)."""
    return bool(re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', text))

def parse_amount(text):
    """Parses a string into a float amount, handling commas and spaces."""
    if not text:
        return None
    # Remove all but digits, dots, and negative signs
    clean = re.sub(r'[^0-9.\-]', '', text)
    try:
        if clean:
            return float(clean)
    except ValueError:
        pass
    return None

def parse_transaction_row(text_row):
    """
    Splits a raw text row into common bank statement fields.
    Heuristics:
    - Date is usually at the start.
    - Balance is usually at the end.
    - Description is middle.
    - Credits/Debits are between description and balance.
    """
    # Simple split-based heuristic for sample SBI-style statements
    parts = text_row.split()
    if len(parts) < 4:
        return None

    # Check for date at start
    if not is_date(parts[0]):
        return None
        
    # Heuristic for SBI: TXN DATE | VALUE DATE | DESCRIPTION | DEBIT | CREDIT | BALANCE
    # We'll use a more flexible regex-based scan
    
    # Identify all numbers in the row
    # This regex finds floats with optional commas
    matches = list(re.finditer(r'-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text_row))
    
    if len(matches) < 1:
        return None # No amounts found
        
    # Dates
    dates = list(re.finditer(r'\d{2}[/-]\d{2}[/-]\d{2,4}', text_row))
    if not dates:
        return None
        
    # Structure: [Date] ... [Amount1] [Amount2] ... [Balance]
    # We'll take the first date as Date, the last as Balance.
    # The rest depends on positions.
    
    # For SBI specifically (based on test_case_2 knowledge):
    # TxnDate, ValueDate, Description, Debit, Credit, Balance
    
    txn_date = dates[0].group(0)
    val_date = dates[1].group(0) if len(dates) > 1 else ""
    
    # Description is between the dates and the first amount
    # or after one date if only one exists.
    desc_start = dates[-1].end()
    
    # Amounts are usually at the end
    # We look for the last 3 possible amount slots
    amounts = []
    for m in matches:
        # Ignore strings that are parts of dates
        is_date_part = False
        for d in dates:
            if m.start() >= d.start() and m.end() <= d.end():
                is_date_part = True
                break
        if not is_date_part:
            amounts.append(m)

    # Heuristic: Balance is last. Credit/Debit are before it.
    balance_val = amounts[-1].group(0) if amounts else ""
    
    # If we have 2 more amounts, they are Credit and Debit.
    # If only 1 more, we need to check if it's Credit or Debit based on position.
    # (In SBI, Debit is col 4, Credit is col 5, Balance is col 6)
    
    # Let's keep it simple for now:
    # We'll use the raw text row and try to split by large spaces or use standard column positions.
    # But since we have row_builder, we have coordinates!
    return None # We should use coordinates for better results

def parse_row_with_coords(row_words):
    """
    Uses word coordinates to map text to columns.
    Assumes SBI column layout (6 columns).
    """
    # New mapping based on debug coords:
    # TxnDate: ~38, ValDate: ~103, Desc: ~168, Debit: ~364, Credit: ~430, Balance: ~495
    
    cols = ["", "", "", "", "", ""] 
    
    for w in row_words:
        x0 = w[0]
        text = w[4]
        
        if x0 < 90:
            cols[0] += " " + text
        elif x0 < 160:
            cols[1] += " " + text
        elif x0 < 350:
            cols[2] += " " + text
        elif x0 < 420:
            cols[3] += " " + text
        elif x0 < 485:
            cols[4] += " " + text
        else:
            cols[5] += " " + text
            
    return [c.strip() for c in cols]
