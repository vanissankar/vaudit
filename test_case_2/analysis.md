# Benchmark Analysis

## Libraries Used
- PyMuPDF (fitz)
- Camelot-py (stream flavor)
- docTR (OCR fallback)
- Polars
- XlsxWriter
- psutil
- matplotlib

## Graph
![Pages vs Time vs CPU](analysis_graph.png)

## Observations
- Sequential Average Time : 9.79s across page sizes [1, 8, 16, 24, 32, 50]
- Threaded Average Time   : 10.36s across page sizes [1, 8, 16, 24, 32, 50]
- CPU usage scales roughly linearly with page count for both modes.
- docTR OCR fallback (not triggered for this PDF) would cause large time spikes.

## Architectural Use Cases

### When to use Sequential Processing
- **Small documents (< 30 pages):** Thread-pool warm-up overhead exceeds actual parse savings.
- **Low-RAM environments:** Sequential processing streams one page at a time, preventing OOM.

### When to use Threaded Processing
- **Large documents (50+ pages):** The 4-worker ThreadPoolExecutor splits Camelot reads concurrently,
  progressively outpacing sequential as document size grows.
- **Batch workloads:** Directories with many PDFs benefit greatly — each file runs in its own thread.

## Final Conclusion
Sequential processing matched or outperformed threading across small page counts. For large documents (50+ pages) multithreading begins to show a measurable advantage as I/O-bound Camelot table reads benefit from concurrent execution.
