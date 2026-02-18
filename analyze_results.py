#!/usr/bin/env python3
"""
Reverse Proxy Benchmark Analysis Script

Parses vegeta JSON output and generates publication-quality comparison charts.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any

try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import colormaps
    from matplotlib.axes import Axes

    plt.rcParams.update({"figure.max_open_warning": 0})
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

RESULTS_DIR = "./results"
CHART_DPI = 150
FIGURE_SIZE = (16, 10)


def parse_vegeta_json(filepath: str) -> dict[str, Any] | None:
    """Parse vegeta JSON report output."""
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except (IOError, OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
        return None

    # Calculate error count from status_codes
    status_codes = data.get("status_codes", {})
    total_requests = data.get("requests", 0)
    successful = status_codes.get("200", 0)
    error_count = total_requests - successful

    # Convert nanoseconds to milliseconds for latency values
    latencies = data.get("latencies", {})

    return {
        "rps": data.get("rate", 0),
        "throughput": data.get("throughput", 0),
        "requests": total_requests,
        "success": data.get("success", 0),
        "errors": error_count,
        "lat_mean": latencies.get("mean", 0) / 1e6,  # ns to ms
        "lat_min": latencies.get("min", 0) / 1e6,
        "lat_max": latencies.get("max", 0) / 1e6,
        "lat_p50": latencies.get("50th", 0) / 1e6,
        "lat_p90": latencies.get("90th", 0) / 1e6,
        "lat_p95": latencies.get("95th", 0) / 1e6,
        "lat_p99": latencies.get("99th", 0) / 1e6,
        "bytes_in": data.get("bytes_in", {}).get("total", 0),
        "bytes_out": data.get("bytes_out", {}).get("total", 0),
        "error_list": data.get("errors", []),
    }


def calculate_error_rate(metrics: dict[str, Any]) -> float:
    """Calculate error rate as percentage."""
    total = metrics.get("requests", 0)
    failed = metrics.get("errors", 0)

    if total == 0:
        return 0.0
    return (failed / total) * 100


def load_data() -> dict[str, dict[str, dict[str, Any]]]:
    """Load all benchmark results from the results directory."""
    data: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))

    if not os.path.exists(RESULTS_DIR):
        print(f"Error: Results directory '{RESULTS_DIR}' not found", file=sys.stderr)
        return data

    for proxy in os.listdir(RESULTS_DIR):
        proxy_path = os.path.join(RESULTS_DIR, proxy)
        if not os.path.isdir(proxy_path):
            continue

        for filename in os.listdir(proxy_path):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(proxy_path, filename)
            scenario = filename[:-5]  # Remove .json extension
            metrics = parse_vegeta_json(filepath)

            if metrics:
                data[proxy][scenario] = metrics

    return data


def format_scenario_name(scenario: str) -> str:
    """Format scenario name for display."""
    mapping = {
        "http": "HTTP/1.1",
        "https": "HTTPS/1.1",
        "https_http2": "HTTPS/2",
    }
    return mapping.get(scenario, scenario.replace("_", " ").title())


def print_results(data: dict[str, dict[str, dict[str, Any]]]) -> None:
    """Print formatted benchmark results table."""
    print("\n" + "=" * 150)
    print("REVERSE PROXY BENCHMARK RESULTS (~20KB JSON Payload | Tool: Vegeta)")
    print("=" * 150)
    print("=" * 150)

    all_scenarios = sorted(set(s for proxy_data in data.values() for s in proxy_data.keys()))

    for scenario in all_scenarios:
        print(f"\n{format_scenario_name(scenario).replace(chr(10), ' ')}")
        print("-" * 150)
        print(
            f"{'Proxy':<18} {'Req/s':>10} {'Throughput':>12} {'Mean(ms)':>10} "
            f"{'P99(ms)':>10} {'Max(ms)':>10} {'Success':>10} {'Errors':>8} {'Error%':>8}"
        )
        print("-" * 150)

        for proxy in sorted(data.keys()):
            if scenario not in data[proxy]:
                continue

            m = data[proxy][scenario]
            err_rate = calculate_error_rate(m)

            print(
                f"{proxy:<18} "
                f"{m.get('rps', 0):>10.1f} "
                f"{m.get('throughput', 0):>12.1f} "
                f"{m.get('lat_mean', 0):>10.2f} "
                f"{m.get('lat_p99', 0):>10.2f} "
                f"{m.get('lat_max', 0):>10.2f} "
                f"{m.get('success', 0)*100:>9.1f}% "
                f"{m.get('errors', 0):>8.0f} "
                f"{err_rate:>7.2f}%"
            )


def format_proxy_label(proxy: str) -> str:
    """Format proxy name for display in legend."""
    return proxy.capitalize()


def create_scientific_chart(data: dict[str, dict[str, dict[str, Any]]]) -> None:
    """Generate publication-quality benchmark comparison charts.

    Design principles:
    - 1x3 layout focusing on key metrics: Throughput, Latency, Error Rate
    - Colorblind-friendly palette (Okabe-Ito)
    - Clear axis labeling with units
    - Grouped by proxy type for easy comparison
    - Log scales clearly indicated with visual grid lines
    - Minimal clutter - no redundant labels
    """
    if not HAS_PLOT:
        print("\nNote: Install matplotlib and numpy for chart generation")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_dir = os.path.join(RESULTS_DIR, "charts")
    os.makedirs(chart_dir, exist_ok=True)

    proxies = sorted(data.keys())
    scenarios = sorted(set(s for proxy_data in data.values() for s in proxy_data.keys()))

    # Define scenario order for logical presentation
    scenario_order = ["http", "https", "https_http2"]
    scenarios = [s for s in scenario_order if s in scenarios]

    # Okabe-Ito colorblind-friendly palette
    colors = {
        "caddy": "#E69F00",      # Orange
        "nginx": "#56B4E9",      # Sky blue
        "traefik": "#009E73",    # Bluish green
    }

    # Single row layout: Throughput | Latency | Error Rate
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.patch.set_facecolor("white")

    # Clean title without redundant information
    fig.suptitle(
        "Reverse Proxy Performance Benchmark",
        fontsize=14, fontweight="semibold", y=0.98
    )

    ax_throughput, ax_latency, ax_errors = axes

    x = np.arange(len(scenarios))
    width = 0.25

    # Shared styling function
    def style_axis(ax, ylabel: str, title: str, use_log: bool = True, log_min: float = None) -> None:
        ax.set_xlabel("Protocol", fontsize=10, fontweight="medium")
        ax.set_ylabel(ylabel, fontsize=10, fontweight="medium")
        ax.set_title(title, fontsize=11, fontweight="semibold", pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels([format_scenario_name(s) for s in scenarios], fontsize=9)
        if use_log:
            ax.set_yscale("log")
            if log_min is not None:
                ax.set_ylim(bottom=log_min)
            ax.grid(axis="y", alpha=0.2, linestyle=":", linewidth=0.7, which="both")
        else:
            ax.grid(axis="y", alpha=0.2, linestyle=":", linewidth=0.7)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Plot 1: Throughput (Successful requests per second)
    for i, proxy in enumerate(proxies):
        values = [data[proxy].get(s, {}).get("throughput", 0) for s in scenarios]
        ax_throughput.bar(
            x + width * (i - 1), values, width,
            label=format_proxy_label(proxy),
            color=colors.get(proxy, f"C{i}"),
            alpha=0.85,
            edgecolor="white", linewidth=1.2
        )

    style_axis(
        ax_throughput,
        ylabel="Throughput (req/s)",
        title="Throughput (higher is better)",
        use_log=True,
        log_min=0.1
    )
    ax_throughput.legend(
        loc="lower left",
        framealpha=0.95,
        fontsize=9,
        edgecolor="#cccccc",
        title="Proxy"
    )

    # Plot 2: Latency (P95)
    for i, proxy in enumerate(proxies):
        p95s = [data[proxy].get(s, {}).get("lat_p95", 0) for s in scenarios]

        ax_latency.bar(
            x + width * (i - 1), p95s, width,
            label=format_proxy_label(proxy),
            color=colors.get(proxy, f"C{i}"),
            alpha=0.85,
            edgecolor="white", linewidth=1.2
        )

    style_axis(
        ax_latency,
        ylabel="Latency (ms)",
        title="P95 latency (lower is better)",
        use_log=True,
        log_min=0.1
    )

    # Plot 3: Error Rate
    all_err_rates = []
    for i, proxy in enumerate(proxies):
        err_rates = []
        for s in scenarios:
            m = data[proxy].get(s, {})
            err_rates.append(calculate_error_rate(m))
        all_err_rates.extend(err_rates)

        ax_errors.bar(
            x + width * (i - 1), err_rates, width,
            label=format_proxy_label(proxy),
            color=colors.get(proxy, f"C{i}"),
            alpha=0.85,
            edgecolor="white", linewidth=1.2
        )

    # Use log scale only if there are non-zero error rates
    use_log_errors = any(v > 0 for v in all_err_rates)
    style_axis(
        ax_errors,
        ylabel="Error Rate (%)",
        title="Error rate (lower is better)",
        use_log=use_log_errors
    )

    # Footer with metadata
    footer = (
        f"Tool: Vegeta v12.13.0 | "
        f"Payload: ~20KB JSON | "
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    fig.text(0.5, 0.01, footer, ha="center", fontsize=8, color="#666666", style="italic")

    plt.tight_layout(rect=[0, 0.02, 1, 0.94])

    chart_path = os.path.join(chart_dir, f"benchmark_{timestamp}.png")
    plt.savefig(chart_path, dpi=CHART_DPI, bbox_inches="tight", facecolor="white")
    plt.close()

    print(f"\n✓ Chart saved: {chart_path}")


def print_error_summary(data: dict[str, dict[str, dict[str, Any]]]) -> None:
    """Print summary of error types encountered."""
    error_types: set[str] = set()

    for proxy_data in data.values():
        for scenario_data in proxy_data.values():
            for err in scenario_data.get("error_list", []):
                error_types.add(err)

    print("\n" + "=" * 150)
    if error_types:
        print("ERROR TYPES SUMMARY")
        print("=" * 150)
        for err_type in sorted(error_types):
            print(f"  • {err_type}")
    else:
        print("No errors detected in any benchmarks")
    print("=" * 150)


def main() -> int:
    """Main entry point."""
    data = load_data()

    if not data:
        print("Error: No benchmark data found in 'results/' directory", file=sys.stderr)
        return 1

    print_results(data)

    if HAS_PLOT:
        create_scientific_chart(data)

    print_error_summary(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
