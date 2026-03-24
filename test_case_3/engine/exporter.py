import pandas as pd
import json
import os

def export_to_excel(transactions, metadata, output_path):
    """
    Exports transactions to Excel with metadata at the top.
    Reference: Test Case 1/2 style.
    """
    # Create DataFrame for transactions
    df = pd.DataFrame(transactions, columns=["Txn Date", "Value Date", "Description", "Debit", "Credit", "Balance"])
    
    # Create writer
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    workbook = writer.book
    sheet_name = 'Statement'
    
    # Formats
    header_format = workbook.add_format({
        'bold': True, 
        'bg_color': '#D7E4BC', 
        'border': 1,
        'align': 'center'
    })
    meta_label_format = workbook.add_format({'bold': True, 'font_color': '#1F4E78'})
    meta_value_format = workbook.add_format({'font_color': '#3B3838'})
    
    # 1. Write Metadata at the top
    row_idx = 0
    # Create a dummy DataFrame just to get the writer initialized if needed, 
    # but we'll use direct worksheet access for the top part.
    df.to_excel(writer, sheet_name=sheet_name, startrow=8, index=False)
    worksheet = writer.sheets[sheet_name]
    
    metadata_fields = [
        ("Account Name", metadata.get("Account Holder Name", "N/A")),
        ("Account Number", metadata.get("Account Number", "N/A")),
        ("Bank Name", metadata.get("Bank Name", "N/A")),
        ("Statement Period", metadata.get("Statement Period", "N/A")),
        ("Filename", metadata.get("filename", "N/A")),
        ("Total Pages", metadata.get("page_count", "N/A"))
    ]
    
    for label, value in metadata_fields:
        worksheet.write(row_idx, 0, label, meta_label_format)
        worksheet.write(row_idx, 1, str(value), meta_value_format)
        row_idx += 1
    
    # 2. Format Transaction Headers (at row 8)
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(8, col_num, value, header_format)
        
    # 3. Auto-adjust column widths
    for i, col in enumerate(df.columns):
        # find max length in that column
        column_len = df[col].astype(str).str.len().max()
        column_len = max(column_len, len(col)) + 2
        worksheet.set_column(i, i, column_len)

    writer.close()

def export_to_json(metadata, summary, output_path):
    data = {"metadata": metadata, "summary": summary}
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
