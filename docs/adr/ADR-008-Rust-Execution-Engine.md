# ADR-008: Rust-Based Execution Engine Evaluation

## Status
Proposed

## Context
High-frequency backtesting, real-time risk valuation, and execution order routing require microsecond-level latency and strict safety guarantees. Python execution scripts and Next.js APIs introduce garbage collection pauses, interpretation overhead, and concurrency limitations.

## Decision
We propose implementing the core execution and backtesting loops in **Rust** as a separate compiled module. The Rust module will be exposed to the Python machine learning service (e.g., using PyO3 bindings) and dashboard services, handling intensive numerical simulations and high-speed routing while leaving orchestration and reporting to Python and Next.js.

## Consequences
- **Performance**: Near-zero computation overhead and deterministic execution times.
- **Safety**: Compile-time concurrency guarantees eliminate data races in multi-threaded backtests.
- **Complexity**: Introducing Rust requires maintaining additional compilation pipelines, cross-compilers, and binding logic (e.g., PyO3 packages).
- **Team Skillset**: Requires developers to have or build proficiency in Rust, increasing training requirements.

## Alternatives Considered
- **Pure Python with Cython/Numba**: Optimizing existing Python math code. Rejected because it does not provide Rust's structural safety, thread safety, and dependency management advantages.
- **Pure C++ Execution Engine**: Implementing in C++. Rejected due to modern dependency package complexity and lack of memory safety guarantees.

## Related Documents
- [06-testing-standard.md](file:///home/zafka/trade-dashboard/docs/book/06-testing-standard.md)
- [08-release-process.md](file:///home/zafka/trade-dashboard/docs/book/08-release-process.md)

## Future Impact
Establishes MoroQuant as a high-performance quantitative trading engine capable of processing millions of data updates per second without architectural redesign.
