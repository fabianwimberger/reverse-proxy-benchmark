#!/usr/bin/env python3
"""Print a one-line summary of a vegeta JSON report."""

import json
import sys

with open(sys.argv[1]) as f:
    d = json.load(f)

ok = d["success"] * 100
p50 = d["latencies"]["50th"] / 1e6
p99 = d["latencies"]["99th"] / 1e6
rate = d.get("rate", 0)
print(f"ok={ok:6.2f}%  p50={p50:7.2f}ms  p99={p99:7.2f}ms  rate={rate:>5.0f}/s")
