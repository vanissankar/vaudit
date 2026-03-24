def group_words_into_rows(words, y_threshold=2.0):
    """
    Groups words into horizontal rows based on Y-coordinate alignment.
    'words' is a list of (x0, y0, x1, y1, text, ...) tuples.
    Returns a list of rows, where each row is a list of words sorted by X0.
    """
    if not words:
        return []

    # Sort words by Y-top (y1) primarily, then X-left (x0)
    sorted_words = sorted(words, key=lambda w: (w[1], w[0]))
    
    rows = []
    if not sorted_words:
        return rows

    current_row = [sorted_words[0]]
    last_y = sorted_words[0][1]

    for i in range(1, len(sorted_words)):
        word = sorted_words[i]
        curr_y = word[1]
        
        # If the vertical gap is small, it's the same row
        if abs(curr_y - last_y) <= y_threshold:
            current_row.append(word)
        else:
            # Sort current row by x0 before finalizing
            rows.append(sorted(current_row, key=lambda w: w[0]))
            current_row = [word]
            last_y = curr_y
            
    if current_row:
        rows.append(sorted(current_row, key=lambda w: w[0]))
        
    return rows

def rows_to_text(rows):
    """Converts grouped words into simple strings."""
    text_rows = []
    for row in rows:
        text_rows.append(" ".join([w[4] for w in row]))
    return text_rows
