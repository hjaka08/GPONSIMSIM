import csv
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# gems.csv 에서 t_start_us 랑 pli 만 있으면 그림은 그려진다

def read_gems_csv(path):
    t_list, pli_list = [], []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                t_list.append(float(row["t_start_us"]) / 1e6)
                pli_list.append(float(row["pli"]))
            except Exception:
                continue

    t = np.asarray(t_list)
    pli = np.asarray(pli_list)
    order = np.argsort(t)
    return t[order], pli[order]


data_root = Path("data")
out_dir = Path("out_cumsum")
out_dir.mkdir(parents=True, exist_ok=True)

for i in range(1, 11):
    vid = f"vid{i:03d}"
    plt.figure()
    for run in ["run1", "run2", "run3"]:
        p = data_root / "youtube" / vid / f"{run}.gems.csv"
        if not p.exists():
            continue
        t, pli = read_gems_csv(p)
        plt.plot(t - t[0], np.cumsum(pli), label=f"{vid}/{run}")

    plt.title(f"Cumulative PLI vs Time ({vid})")
    plt.xlabel("Time since start (s)")
    plt.ylabel("Cumulative PLI (bytes)")
    plt.legend(loc="best")
    plt.savefig(out_dir / f"cumsum_{vid}.png", bbox_inches="tight", dpi=200)
    plt.close()

print("done")
