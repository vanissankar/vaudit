# Test Case 2

This project benchmarks PDF bank statement extraction using an optimized set of libraries:
- **PyMuPDF**: Core PDF parsing
- **Camelot**: Primary table extraction
- **docTR**: OCR fallback (only utilized when Camelot is insufficient)
- **Polars**: High-speed data processing
- **xlsxwriter**: Native Excel exports
- **psutil**: System metrics measurement
- **matplotlib**: Graphing

## Architecture
- `Sequential/`: Processes PDF documents synchronously in a linear pipeline.
- `Threads/`: Implements a multi-threaded processing model via ThreadPoolExecutor (max workers: 4-6) to speed up batch document processing.
- `benchmark.py`: Central testing suite measuring Pages vs Time and CPU usage between Sequential and Threads implementations.

## Setup Instructions
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Place test bank statement PDFs inside `Sequential/input` or `Threads/input`.
3. Execution:
   ```bash
   python Sequential/main.py
   python Threads/main.py
   ```
4. Benchmark:
   ```bash
   python benchmark.py
   ```

Outputs will be saved dynamically to `output/excel` and `output/json` in their respective mode folders.
