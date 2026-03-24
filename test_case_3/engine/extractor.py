import fitz

def extract_words_from_pdf(filepath):
    """
    Extracts words from PDF with their bounding boxes (x0, y0, x1, y1).
    Returns a list of pages, each containing a list of words.
    """
    pages_data = []
    with fitz.open(filepath) as doc:
        for page in doc:
            # get_text_words returns (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text_words()
            pages_data.append(words)
    return pages_data
