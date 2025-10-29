# Performance Benchmarks

Performance benchmarks for CST-LSP using pytest-benchmark.

## Running Benchmarks

### Run all benchmarks:
```bash
pytest tests/benchmarks/ --benchmark-only
```

### Run specific benchmark group:
```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-group=search-common-symbol
pytest tests/benchmarks/ --benchmark-only --benchmark-group=cache-effectiveness
pytest tests/benchmarks/ --benchmark-only --benchmark-group=scalability
```

### Save and compare benchmarks:
```bash
# Save baseline
pytest tests/benchmarks/ --benchmark-only --benchmark-save=baseline

# Run new benchmarks and compare
pytest tests/benchmarks/ --benchmark-only --benchmark-compare=baseline
```

## Benchmark Groups

### Symbol Search Performance
Tests RipGrepSymbolFinder search speed across different project sizes:
- Small (10 files, ~500 lines)
- Medium (50 files, ~5000 lines)
- Large (200 files, ~20000 lines)

### Caching Effectiveness
Measures cache hit performance vs cache misses:
- First vs second search (cache hit)
- Multiple symbol searches (cache misses)

### Search Pattern Complexity
Tests different symbol types:
- Class definitions
- Function definitions
- Enum definitions

### Scalability Analysis
Measures how performance scales with project size.

## Interpreting Results

Benchmark output shows:
- **Min/Max/Mean**: Time range for operation
- **Median**: Typical performance
- **StdDev**: Performance consistency
- **IQR**: Interquartile range (50% of measurements)
- **OPS**: Operations per second

Good performance indicators:
- Low Mean/Median (< 1ms for symbol search)
- Low StdDev (consistent performance)
- Linear scaling with project size
