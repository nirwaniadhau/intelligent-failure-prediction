"""
Prometheus Metrics Exporter for ML Anomaly Detection & Root Cause Analysis
===========================================================================
Exports core metrics + engineered features from Prometheus into a structured
dataset suitable for training anomaly detection and failure prediction models.

Features:
- Core metrics (latency, errors, memory, CPU, event loop)
- Engineered features (error ratio, latency percentiles, memory growth rate, etc.)
- RCA labels (fault type, service, endpoint)
- Balanced normal/faulty rows targeting 10k+ samples
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

PROM_URL = "http://localhost:9090/api/v1/query_range"

SERVICES = ["order-service", "auth-service"]

# Step in seconds — lower = more rows, higher resolution
STEP_SECONDS = 5

# ─────────────────────────────────────────────
# Core Metrics (directly from Prometheus)
# ─────────────────────────────────────────────

CORE_METRICS = {
    # Requests
    "request_rate":         'rate(http_requests_total[5m])',
    "request_count":        'http_requests_total',

    # Latency (sum/count for average; histogram for percentiles)
    "latency_sum":          'http_request_duration_ms_sum',
    "latency_count":        'http_request_duration_ms_count',

    # Latency percentiles from histogram buckets
    "latency_p95":          'histogram_quantile(0.95, rate(http_request_duration_ms_bucket[5m]))',
    "latency_p99":          'histogram_quantile(0.99, rate(http_request_duration_ms_bucket[5m]))',

    # Errors
    "error_rate":           'rate(http_errors_total[5m])',
    "error_count":          'http_errors_total',

    # Active requests (concurrency)
    "active_requests":      'http_active_requests',

    # System — Memory
    "memory_bytes":         'process_resident_memory_bytes',
    "heap_used_bytes":      'nodejs_heap_size_used_bytes',
    "heap_total_bytes":     'nodejs_heap_size_total_bytes',

    # System — CPU proxy
    "cpu_usage":            'rate(process_cpu_seconds_total[5m])',

    # System — Event loop
    "event_loop_lag_sec":   'nodejs_eventloop_lag_seconds',
}

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def fetch_metric(name: str, query: str, start: int, end: int, step: int) -> pd.DataFrame | None:
    """Query Prometheus range API and return a tidy DataFrame."""
    params = {"query": query, "start": start, "end": end, "step": step}
    try:
        resp = requests.get(PROM_URL, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        print(f"  [ERROR] HTTP request failed for '{name}': {e}")
        return None

    data = result.get("data", {}).get("result", [])
    if not data:
        print(f"  [WARN]  No data returned for '{name}'")
        return None

    # Flatten: take first result series (most metrics are single series)
    values = data[0]["values"]
    df = pd.DataFrame(values, columns=["timestamp", name])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df[name] = pd.to_numeric(df[name], errors="coerce")
    return df


def merge_dataframes(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Outer-join all DataFrames on timestamp."""
    if not dfs:
        raise ValueError("No dataframes to merge.")
    dataset = dfs[0]
    for df in dfs[1:]:
        dataset = pd.merge(dataset, df, on="timestamp", how="outer")
    return dataset.sort_values("timestamp").reset_index(drop=True)


# ─────────────────────────────────────────────
# Engineered Features
# ─────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive ML-ready features from raw metrics.

    Added features:
    - error_ratio           : errors / requests (fault indicator)
    - avg_latency_ms        : latency_sum / latency_count
    - heap_utilization      : heap_used / heap_total (GC pressure)
    - memory_growth_rate    : rolling delta of memory over ~10 min window
    - throughput_variance   : rolling stddev of request_rate (instability)
    - cpu_x_latency         : cpu_usage * avg_latency (composite stress score)
    - latency_spike         : binary flag — latency > 2× rolling mean
    - memory_leak_flag      : binary flag — memory monotonically rising > 5 steps
    """
    df = df.copy()

    # Average latency
    if "latency_sum" in df.columns and "latency_count" in df.columns:
        df["avg_latency_ms"] = df["latency_sum"] / df["latency_count"].replace(0, np.nan)

    # Error ratio
    if "error_rate" in df.columns and "request_rate" in df.columns:
        df["error_ratio"] = df["error_rate"] / df["request_rate"].replace(0, np.nan)
        df["error_ratio"] = df["error_ratio"].clip(0, 1)

    # Heap utilization
    if "heap_used_bytes" in df.columns and "heap_total_bytes" in df.columns:
        df["heap_utilization"] = df["heap_used_bytes"] / df["heap_total_bytes"].replace(0, np.nan)

    # Memory growth rate (rolling delta over ~10 min window)
    if "memory_bytes" in df.columns:
        window = max(1, int(600 / STEP_SECONDS))   # 10 min in rows
        df["memory_growth_rate"] = df["memory_bytes"].diff(periods=window) / window

    # Throughput variance (rolling stddev of request rate over 1h)
    if "request_rate" in df.columns:
        window = max(1, int(3600 / STEP_SECONDS))  # 1 hour in rows
        df["throughput_variance"] = df["request_rate"].rolling(window=window, min_periods=1).std()

    # Composite: CPU × latency stress score
    if "cpu_usage" in df.columns and "avg_latency_ms" in df.columns:
        df["cpu_x_latency"] = df["cpu_usage"] * df["avg_latency_ms"]

    # Binary flag: latency spike (>2× rolling 10-min mean)
    if "avg_latency_ms" in df.columns:
        rolling_mean = df["avg_latency_ms"].rolling(
            window=max(1, int(600 / STEP_SECONDS)), min_periods=1
        ).mean()
        df["latency_spike"] = (df["avg_latency_ms"] > 2 * rolling_mean).astype(int)

    # Binary flag: memory leak (monotonically rising for ≥5 consecutive rows)
    if "memory_bytes" in df.columns:
        rising = df["memory_bytes"].diff() > 0
        df["memory_leak_flag"] = (
            rising.rolling(window=5, min_periods=5).sum() == 5
        ).astype(int)

    return df


# ─────────────────────────────────────────────
# RCA Labels
# ─────────────────────────────────────────────

def add_rca_labels(df: pd.DataFrame, service: str, fault_active: bool, fault_type: str | None) -> pd.DataFrame:
    """
    Attach ground-truth labels for Root Cause Analysis (supervised ML).

    Columns added:
    - service      : 'order-service' | 'auth-service'
    - fault_type   : 'normal' | 'cpu-spike' | 'memory-leak' | 'latency' | 'error-storm'
    - is_anomaly   : 0 (normal) | 1 (faulty) — binary target for anomaly detection
    """
    df = df.copy()
    df["service"] = service
    df["fault_type"] = fault_type if fault_active and fault_type else "normal"
    df["is_anomaly"] = 0 if not fault_active else 1
    return df


# ─────────────────────────────────────────────
# Main Export Pipeline
# ─────────────────────────────────────────────

def export_metrics(
    duration_minutes: int,
    step: int,
    service: str,
    fault_type: str | None,
    output_path: str,
    append: bool = False,
):
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=duration_minutes)
    start_ts = int(start_time.timestamp())
    end_ts = int(end_time.timestamp())

    print(f"\n{'═'*60}")
    print(f"  Exporting metrics for: {service}")
    print(f"  Window : {start_time.strftime('%H:%M:%S')} → {end_time.strftime('%H:%M:%S')}  ({duration_minutes} min)")
    print(f"  Step   : {step}s  |  Fault: {fault_type or 'none (normal)'}")
    print(f"{'═'*60}")

    collected = []
    for name, query in CORE_METRICS.items():
        print(f"  Fetching {name}...")
        df = fetch_metric(name, query, start_ts, end_ts, step)
        if df is not None:
            collected.append(df)

    if not collected:
        print("[ERROR] No metrics collected. Is Prometheus running?")
        return

    dataset = merge_dataframes(collected)
    dataset = engineer_features(dataset)
    dataset = add_rca_labels(dataset, service, fault_type is not None, fault_type)

    # Reorder columns: timestamp first, labels last
    label_cols = ["service", "fault_type", "is_anomaly"]
    feature_cols = [c for c in dataset.columns if c not in ["timestamp"] + label_cols]
    dataset = dataset[["timestamp"] + feature_cols + label_cols]

    # Save / append
    mode = "a" if append and os.path.exists(output_path) else "w"
    header = not (append and os.path.exists(output_path))
    dataset.to_csv(output_path, mode=mode, header=header, index=False)

    print(f"\n  ✓ Rows exported : {len(dataset)}")
    print(f"  ✓ Features      : {len(dataset.columns)}")
    print(f"  ✓ Saved to      : {output_path}")
    return dataset


# ─────────────────────────────────────────────
# Dataset Summary
# ─────────────────────────────────────────────

def print_summary(path: str):
    df = pd.read_csv(path)
    print(f"\n{'═'*60}")
    print(f"  DATASET SUMMARY — {path}")
    print(f"{'═'*60}")
    print(f"  Total rows    : {len(df)}")
    print(f"  Total features: {len(df.columns)}")
    if "is_anomaly" in df.columns:
        counts = df["is_anomaly"].value_counts()
        print(f"  Normal rows   : {counts.get(0, 0)}")
        print(f"  Anomaly rows  : {counts.get(1, 0)}")
    if "fault_type" in df.columns:
        print(f"\n  Fault type distribution:")
        print(df["fault_type"].value_counts().to_string(header=False))
    print(f"\n  Columns:")
    for col in df.columns:
        print(f"    - {col}")
    print(f"{'═'*60}\n")


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────

FAULT_CHOICES = ["cpu-spike", "memory-leak", "latency", "error-storm"]

def main():
    global STEP_SECONDS
    parser = argparse.ArgumentParser(
        description="Export Prometheus metrics to ML-ready CSV dataset."
    )
    parser.add_argument(
        "--duration", type=int, default=10,
        help="Minutes of history to export (default: 10)"
    )
    parser.add_argument(
        "--step", type=int, default=STEP_SECONDS,
        help=f"Scrape step in seconds (default: {STEP_SECONDS})"
    )
    parser.add_argument(
        "--service", type=str, default="order-service",
        choices=SERVICES,
        help="Service to label in the dataset"
    )
    parser.add_argument(
        "--fault", type=str, default=None,
        choices=FAULT_CHOICES,
        help="Fault type active during this export window (omit for normal traffic)"
    )
    parser.add_argument(
        "--output", type=str, default="metrics_dataset.csv",
        help="Output CSV file path (default: metrics_dataset.csv)"
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing CSV instead of overwriting (useful for building balanced datasets)"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print dataset summary after export"
    )
    parser.add_argument(
        "--all-services", action="store_true",
        help="Export metrics for all services and merge into one file"
    )

    args = parser.parse_args()

    # Update global step for feature engineering windows
    STEP_SECONDS = args.step

    if args.all_services:
        for i, svc in enumerate(SERVICES):
            export_metrics(
                duration_minutes=args.duration,
                step=args.step,
                service=svc,
                fault_type=args.fault,
                output_path=args.output,
                append=(args.append or i > 0),  # append after first service
            )
    else:
        export_metrics(
            duration_minutes=args.duration,
            step=args.step,
            service=args.service,
            fault_type=args.fault,
            output_path=args.output,
            append=args.append,
        )

    if args.summary:
        print_summary(args.output)


if __name__ == "__main__":
    main()