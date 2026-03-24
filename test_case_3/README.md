# Test Case 3: Custom Rule-Based Parsing Engine

This project contains a high-performance bank statement extraction engine built from scratch using word coordinates and regex patterns.

## Architecture
- **engine/**: Modular parsing engine logic.
- **Sequential/**: Linear processing implementation.
- **Threads/**: Concurrent processing (ThreadPoolExecutor).
- **benchmark.py**: Performance comparison suite.

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Place your bank statement PDF in `Sequential/input/`.
3. Run benchmark: `python benchmark.py`.
4. Check `analysis_graph.png` and `analysis.md` for results.

## Performance
Test Case 3 is designed for speed. By bypassing heavy table detection libraries, it achieves near-instant extraction for structured PDFs.
