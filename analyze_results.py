#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from collections import defaultdict

try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import colormaps
    plt.rcParams.update({"figure.max_open_warning": 0})
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

RESULTS_DIR = "./results"
data = defaultdict(lambda: defaultdict(dict))

for proxy in os.listdir(RESULTS_DIR):
    proxy_path = os.path.join(RESULTS_DIR, proxy)
    if not os.path.isdir(proxy_path):
        continue

    for f in os.listdir(proxy_path):
        if not f.endswith(".txt"):
            continue

        with open(os.path.join(proxy_path, f)) as file:
            content = file.read()

        m = {}
        is_rewrk = "Req/Sec:" in content or "Transfer Rate:" in content

        if is_rewrk:
            patterns = {
                "rps": (r"Req/Sec:\s*([\d.]+)", 0),
                "lat": (r"Avg\s+Stdev[^\n]*\n\s+([\d.]+)ms", re.MULTILINE),
                "std": (r"Avg\s+Stdev[^\n]*\n\s+[\d.]+ms\s+([\d.]+)ms", re.MULTILINE),
                "max": (r"Avg\s+Stdev[^\n]*\n\s+[\d.]+ms\s+[\d.]+ms\s+[\d.]+ms\s+([\d.]+)ms", re.MULTILINE),
                "tot": (r"Requests:\s*\n[^\n]*Total:\s+(\d+)", re.MULTILINE),
                "tx": (r"Transfer Rate:\s+([\d.]+)\s*(MB|KB|GB)/Sec", 0),
                "err": (r"(\d+)\s+Errors:", 0),
            }
        else:
            patterns = {
                "rps": (r"Requests/sec:\s*([\d.]+)", 0),
                "tx": (r"Transfer/sec:\s*([\d.]+)\s*(MB|KB|GB)", 0),
                "lat": (r"Latency\s+([\d.]+)\s*(us|ms|s)", 0),
                "std": (r"Latency\s+[\d.]+\s*(us|ms|s)\s+([\d.]+)\s*(us|ms|s)", 0),
                "max": (r"Latency\s+[\d.]+\s*(us|ms|s)\s+[\d.]+\s*(us|ms|s)\s+([\d.]+)\s*(us|ms|s)", 0),
                "tot": (r"(\d+)\s+requests in", 0),
                "err": (r"Non-2xx or 3xx responses:\s*(\d+)", 0),
            }

        for k, (p, flags) in patterns.items():
            match = re.search(p, content, flags)
            if match:
                try:
                    if k == "tx":
                        v = float(match.group(1))
                        u = match.group(2) if len(match.groups()) > 1 else "MB"
                        m["tx"] = v / 1024 if u == "KB" else v * 1024 if u == "GB" else v
                    elif k in ["lat", "std", "max"]:
                        if is_rewrk:
                            m[k] = float(match.group(1))
                        else:
                            if k == "lat":
                                v, u = float(match.group(1)), match.group(2)
                            elif k == "std":
                                v, u = float(match.group(2)), match.group(3)
                            else:
                                v, u = float(match.group(3)), match.group(4)
                            m[k] = v / 1000 if u == "us" else v * 1000 if u == "s" else v
                    else:
                        m[k] = float(match.group(1))
                except (ValueError, IndexError) as e:
                    print(f"Warning: Failed to parse {k} from {proxy}/{f}: {e}", file=sys.stderr)

        if is_rewrk:
            err_match = re.search(r"(\d+)\s+Errors:\s*(.+?)$", content, re.MULTILINE)
            if err_match and m.get("err", 0) > 0:
                m["err_type"] = err_match.group(2).strip()
        else:
            err_match = re.search(r"Non-2xx or 3xx responses:\s*(\d+)\s*(.+?)$", content, re.MULTILINE)
            if err_match and m.get("err", 0) > 0:
                m["err_type"] = err_match.group(2).strip()

        if m.get("err", 0) > m.get("tot", 0):
            m["err"] = m.get("tot", 0)

        data[proxy][f[:-4]] = m

print("\n" + "=" * 120)
print("REVERSE PROXY BENCHMARK (~20KB JSON)")
print("=" * 120)

for sc in sorted(set(s for p in data.values() for s in p.keys())):
    print(f"\n{sc.upper().replace('_', ' ')}")
    print("-" * 155)
    print(f"{'Proxy':<15} {'Req/s':<12} {'Lat(ms)':<12} {'Max(ms)':<12} {'Total':<12} {'MB/s':<12} {'Errors':<12} {'Error%':<10} {'Error Type':<30}")
    print("-" * 155)

    for px in sorted(data.keys()):
        if sc in data[px]:
            d = data[px][sc]
            err = d.get("err", 0)
            tot = d.get("tot", 0)
            err_pct = (err / tot * 100) if tot > 0 else 0
            err_type = d.get("err_type", "-")
            print(
                f"{px:<15} {d.get('rps', 0):<12.0f} {d.get('lat', 0):<12.2f} {d.get('max', 0):<12.2f} "
                f"{tot:<12.0f} {d.get('tx', 0):<12.1f} {err:<12.0f} {err_pct:<10.2f}% {err_type:<30}"
            )

if HAS_PLOT:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_dir = os.path.join(RESULTS_DIR, "charts")
    os.makedirs(chart_dir, exist_ok=True)

    pxs = sorted(data.keys())
    scs = sorted(set(s for p in data.values() for s in p.keys()))

    fig = plt.figure(figsize=(18, 11))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.3, top=0.93, bottom=0.07, left=0.06, right=0.96)

    a1 = fig.add_subplot(gs[0, 0])
    a2 = fig.add_subplot(gs[0, 1])
    a3 = fig.add_subplot(gs[1, 0])
    a4 = fig.add_subplot(gs[1, 1])

    fig.suptitle("Reverse Proxy Performance Comparison", fontsize=18)

    x = np.arange(len(scs))
    w = 0.25

    cmap = colormaps['tab10']
    c = [cmap(i / len(pxs)) for i in range(len(pxs))]

    for i, px in enumerate(pxs):
        vals = [data[px].get(s, {}).get("rps", 0) for s in scs]
        errs = [data[px].get(s, {}).get("err", 0) for s in scs]
        tots = [data[px].get(s, {}).get("tot", 1) for s in scs]
        err_pcts = [(e/t*100) if t > 0 else 0 for e, t in zip(errs, tots)]

        bars = a1.bar(x + w * (i - 1), vals, w, label=px.capitalize(),
                      color=c[i])

        for j, bar in enumerate(bars):
            if bar.get_height() > 0:
                label = f"{bar.get_height():.0f}"
                a1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        label, ha="center", va="bottom", fontsize=7)

    a1.set_xlabel("Scenario")
    a1.set_ylabel("Requests/s")
    a1.set_title("Throughput (Requests/sec)", fontsize=14, pad=15)
    a1.set_xticks(x)
    a1.set_xticklabels([s.replace("_", "\n") for s in scs])
    a1.set_yscale('log')
    a1.legend()
    a1.grid(axis="y", alpha=0.5, linestyle='--')

    for i, px in enumerate(pxs):
        vals = [data[px].get(s, {}).get("tx", 0) for s in scs]
        errs = [data[px].get(s, {}).get("err", 0) for s in scs]
        tots = [data[px].get(s, {}).get("tot", 1) for s in scs]
        err_pcts = [(e/t*100) if t > 0 else 0 for e, t in zip(errs, tots)]

        bars = a2.bar(x + w * (i - 1), vals, w, label=px.capitalize(),
                      color=c[i])

        for j, bar in enumerate(bars):
            if bar.get_height() > 0:
                label = f"{bar.get_height():.0f}"
                a2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        label, ha="center", va="bottom", fontsize=7)

    a2.set_xlabel("Scenario")
    a2.set_ylabel("MB/s")
    a2.set_title("Throughput (MB/sec)", fontsize=14, pad=15)
    a2.set_xticks(x)
    a2.set_xticklabels([s.replace("_", "\n") for s in scs])
    a2.set_yscale('log')
    a2.legend()
    a2.grid(axis="y", alpha=0.5, linestyle='--')

    for i, px in enumerate(pxs):
        lats = [data[px].get(s, {}).get("lat", 0) for s in scs]
        stds = [data[px].get(s, {}).get("std", 0) for s in scs]
        yerr_lower = [min(lat, std) for lat, std in zip(lats, stds)]
        yerr_upper = stds

        bars = a3.bar(x + w * (i - 1), lats, w, yerr=[yerr_lower, yerr_upper],
                      label=px.capitalize(), color=c[i])

        for j, bar in enumerate(bars):
            if bar.get_height() > 0:
                a3.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + stds[j],
                        f"{bar.get_height():.1f}", ha="center", va="bottom",
                        fontsize=7)

    a3.set_xlabel("Scenario")
    a3.set_ylabel("Latency (ms)")
    aNT = "Average Latency with Standard Deviation"
    a3.set_title(aNT, fontsize=14, pad=15)
    a3.set_xticks(x)
    a3.set_xticklabels([s.replace("_", "\n") for s in scs])
    a3.set_yscale('log')
    a3.legend()
    a3.grid(axis="y", alpha=0.5, linestyle='--')

    for i, px in enumerate(pxs):
        errs = [data[px].get(s, {}).get("err", 0) for s in scs]
        tots = [data[px].get(s, {}).get("tot", 1) for s in scs]
        err_pcts = [(e/t*100) if t > 0 else 0 for e, t in zip(errs, tots)]

        bars = a4.bar(x + w * (i - 1), err_pcts, w, label=px.capitalize(),
                      color=c[i])

        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0.01:
                if height >= 1:
                    label = f"{height:.1f}%"
                elif height >= 0.01:
                    label = f"{height:.2f}%"
                else:
                    label = f"{height:.3f}%"

                a4.text(bar.get_x() + bar.get_width() / 2, height,
                        label, ha="center", va="bottom", fontsize=7)

    a4.set_xlabel("Scenario")
    a4.set_ylabel("Error Rate (%)")
    a4.set_title("Error Rate (% of Failed Requests)", fontsize=14, pad=15)
    a4.set_xticks(x)
    a4.set_xticklabels([s.replace("_", "\n") for s in scs])

    all_err_pcts = []
    for px in pxs:
        for s in scs:
            err = data[px].get(s, {}).get("err", 0)
            tot = data[px].get(s, {}).get("tot", 1)
            if tot > 0:
                all_err_pcts.append((err/tot*100))

    if all_err_pcts:
        max_err = max(all_err_pcts)
        min_pos_err = min([p for p in all_err_pcts if p > 0] or [1])

        if max_err > 0 and min_pos_err / max_err < 0.01:
            a4.set_yscale('log')
            a4.set_ylim(bottom=0.001)
        else:
            a4.set_ylim(bottom=0)
    else:
        a4.set_ylim(bottom=0)


    a4.legend()
    a4.grid(axis="y", alpha=0.5, linestyle='--')

    chart_file = os.path.join(chart_dir, f"summary_{timestamp}.png")
    plt.savefig(chart_file, dpi=120, bbox_inches="tight")
    try:
        os.chmod(chart_file, 0o777)
        os.chmod(chart_dir, 0o777)
    except PermissionError:
        pass
    print(f"\n✓ Simplified Chart: ./results/charts/summary_{timestamp}.png")

error_types_found = set()
for px in data.values():
    for scenario in px.values():
        if "err_type" in scenario:
            error_types_found.add(scenario["err_type"])

if error_types_found:
    print("\n" + "=" * 120)
    print("ERROR TYPES FOUND")
    print("=" * 120)
    for err_type in sorted(error_types_found):
        print(f"  • {err_type}")
    print("=" * 120 + "\n")
else:
    print("\n" + "=" * 120)
    print("No errors detected in any benchmarks")
    print("=" * 120 + "\n")

report_file = os.path.join(RESULTS_DIR, "report.json")
if os.path.exists(report_file):
    os.remove(report_file)

try:
    os.chmod(RESULTS_DIR, 0o777)
except PermissionError:
    pass
