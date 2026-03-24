import re

def extract_metadata(first_page_text):
    """
    Extracts Account Number, Bank Name, and Holder Name from raw text.
    """
    metadata = {
        "Account Number": "Not Found",
        "Bank Name": "Not Found",
        "Account Holder Name": "Not Found",
        "Statement Period": "Not Found"
    }
    
    # Account Number: usually 11-16 digits
    acc_match = re.search(r'Account\s*Number\s*[:\-]?\s*(\d{10,20})', first_page_text, re.I)
    if acc_match:
        metadata["Account Number"] = acc_match.group(1)
        
    # Bank Name: Search for common keywords
    if "STATE BANK OF INDIA" in first_page_text.upper():
        metadata["Bank Name"] = "State Bank of India"
    elif "HDFC BANK" in first_page_text.upper():
        metadata["Bank Name"] = "HDFC Bank"
        
    # Account Holder: Search for "Name" or "Mr/Ms"
    name_match = re.search(r'Name\s*[:\-]?\s*([A-Z\s]{5,30})', first_page_text, re.I)
    if name_match:
        metadata["Account Holder Name"] = name_match.group(1).strip()
        
    return metadata
