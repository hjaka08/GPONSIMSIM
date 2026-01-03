import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_vids(spec: str) -> List[str]:
    spec = spec.strip()
    out: List[str] = []

    if "-" in spec and all(p.strip().isdigit() for p in spec.split("-", 1)):
        a_s, b_s = spec.split("-", 1)
        a, b = int(a_s), int(b_s)
        if a > b:
            a, b = b, a
        for i in range(a, b + 1):
            out.append(f"vid{i:03d}")
        return out

    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for p in parts:
        if p.startswith("vid"):
            out.append(p)
        else:
            n = int(p)
            out.append(f"vid{n:03d}")
    return out


def read_gems_csv(path: Path) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    t_list: List[float] = []
    pli_list: List[float] = []

    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "t_start_us" not in row or "pli" not in row:
                    continue
                try:
                    t_list.append(float(row["t_start_us"]) / 1e6)  
                    pli_list.append(float(row["pli"]))             
                except Exception:
                    continue
    except FileNotFoundError:
        return None

    if not t_list:
        return None

    t = np.asarray(t_list, dtype=np.float64)
    pli = np.asarray(pli_list, dtype=np.float64)

    order = np.argsort(t)
    t = t[order]
    pli = pli[order]
    return t, pli


def make_cumsum_series(t: np.ndarray, pli: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    c = np.cumsum(pli)
    t0 = float(t[0])
    return (t - t0), c


def plot_per_video(
    data_root: Path,
    out_dir: Path,
    vids: List[str],
    runs: List[str],
) -> None:
    yt_root = data_root / "youtube"
    out_dir.mkdir(parents=True, exist_ok=True)

    for vid in vids:
        plt.figure()
        found_any = False

        for run in runs:
            p = yt_root / vid / f"{run}.gems.csv"
            parsed = read_gems_csv(p)
            if parsed is None:
                continue
            t, pli = parsed
            x, y = make_cumsum_series(t, pli)
            plt.plot(x, y, label=f"{vid}/{run}")
            found_any = True

        if not found_any:
            plt.close()
            continue

        plt.title(f"Cumulative PLI vs Time ({vid})")
        plt.xlabel("Time since start (s)")
        plt.ylabel("Cumulative PLI (bytes)")
        plt.legend(loc="best")
        plt.savefig(out_dir / f"cumsum_{vid}.png", bbox_inches="tight", dpi=200)
        plt.close()


def plot_all_vids_run3(
    data_root: Path,
    out_dir: Path,
    vids: List[str],
    run: str = "run3",
) -> None:
    yt_root = data_root / "youtube"
    out_dir.mkdir(parents=True, exist_ok=True)

    plt.figure()
    found = 0
    for vid in vids:
        p = yt_root / vid / f"{run}.gems.csv"
        parsed = read_gems_csv(p)
        if parsed is None:
            continue
        t, pli = parsed
        x, y = make_cumsum_series(t, pli)
        plt.plot(x, y, label=vid)
        found += 1

    if found == 0:
        plt.close()
        return

    plt.title(f"Cumulative PLI vs Time (all vids, {run})")
    plt.xlabel("Time since start (s)")
    plt.ylabel("Cumulative PLI (bytes)")
    plt.legend(loc="best", ncols=2, fontsize=8)
    plt.savefig(out_dir / f"cumsum_all_vids_{run}.png", bbox_inches="tight", dpi=200)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser("Plot cumulative PLI curves from gems.csv (no CNN).")
    ap.add_argument("--data-root", required=True, help="Root dir containing youtube/<vid>/run*.gems.csv")
    ap.add_argument("--out-dir", default="out_cumsum", help="Output directory for PNGs")
    ap.add_argument("--vids", default="1-10", help='Video set. e.g., "1-10" or "001,002,010"')
    ap.add_argument("--runs", default="run1,run2,run3", help='Runs to overlay per video, e.g., "run1,run3"')
    ap.add_argument("--also-all-run3", action="store_true", help="Also make one plot overlaying all vids (run3 only)")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    out_dir = Path(args.out_dir)

    vids = parse_vids(args.vids)
    runs = [r.strip() for r in args.runs.split(",") if r.strip()]

    plot_per_video(data_root, out_dir, vids, runs)

    if args.also_all_run3:
        plot_all_vids_run3(data_root, out_dir, vids, run="run3")

    print(f"Done. Wrote plots to: {out_dir}")


if __name__ == "__main__":
    main()
