# PDF Bank Statement Extraction Benchmark (Test Case 1)

## Purpose
This project is an automated benchmark specifically designed to extract bank statement data from PDFs using sequential vs thread-based processing. It evaluates parsing performance, comparing execution time and CPU usages dynamically.

## Folder Structure
```
test_case_1/
│
├── lib.txt
├── requirements.txt
├── analysis.md
├── benchmark.py
├── README.md
├── .gitignore
│
├── Sequential/
│   ├── main.py
│   ├── input/
│   ├── output/
│   │   ├── excel/
│   │   ├── json/
│
├── Threads/
│   ├── main.py
│   ├── input/
│   ├── output/
│   │   ├── excel/
│   │   ├── json/
```

## Setup Instructions
1. Install Python 3.9+ (tested with python 3.9+)
2. Install dependencies: `pip install -r requirements.txt`

## How to run Sequential
1. Place bank statement PDFs inside `Sequential/input/`.
2. Run `python Sequential/main.py`.
3. Check `Sequential/output/excel/` and `Sequential/output/json/` for results.

## How to run Threads
1. Place bank statement PDFs inside `Threads/input/`.
2. Run `python Threads/main.py`.
3. Check `Threads/output/excel/` and `Threads/output/json/` for results.

## How to run Benchmark
1. Ensure there is at least one multi-page PDF placed inside `Sequential/input/` and `Threads/input/` (must be the SAME file in both places if testing equality, or preferably pass it dynamically - the script handles loading the same file).
2. Run `python benchmark.py`.
3. The benchmark dynamically isolates pages `[1, 8, 16, 24, 32, 50]` from the source document to assess performance.
4. Generates `analysis_graph.png`.

## Outputs
- **Excel** file per PDF containing all extracted transactions.
- **JSON** file per PDF with metadata (account number, bank name) and a numerical summary (total debit, credit, transactions, final balance).
