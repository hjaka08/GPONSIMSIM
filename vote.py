import csv
import math
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def ldata(path):
    if not path.exists():
        return None
    ts, pls = [], []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                ts.append(float(row["t_start_us"]) / 1e6)
                pls.append(float(row["pli"]))
            except (KeyError, ValueError):
                pass
    if not ts:
        return None
    t = np.asarray(ts)
    p = np.asarray(pls)
    o = np.argsort(t)
    return t[o], p[o]


def pearson(a, b):
    n = min(a.size, b.size)
    if n < 2:
        return float("nan")
    a, b = a[:n], b[:n]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def rmse(a, b):
    n = min(a.size, b.size)
    if n == 0:
        return float("nan")
    d = a[:n] - b[:n]
    return float(math.sqrt(float((d * d).mean())))


def main():
    data_root  = Path("data2")
    out_dir    = Path("out_vote2")
    vids       = [f"vid{i:03d}" for i in range(1, 11)]
    runs       = ["run1", "run2", "run3"]
    bin_s      = 0.1               
    db_runs    = ["run1", "run2"]   
    query_runs = ["run3"]          

    out_dir.mkdir(parents=True, exist_ok=True)


    series = {}
    for vid in vids:
        for run in runs:
            got = ldata(data_root / "youtube" / vid / f"{run}.gems.csv")
            if got is None:
                continue
            t, pli = got
            t = t - t[0]
            nb = int(t.max() // bin_s) + 1
            x = np.zeros(nb)
            np.add.at(x, np.clip((t // bin_s).astype(np.int64), 0, nb - 1), pli)
            c = np.cumsum(x)
            if c[-1] > 1e-9:
                c = c / c[-1]
            series[(vid, run)] = c

    if not series:
        raise SystemExit("FILE NOT FOND")


    rows = []
    for vid in vids:
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                a = series.get((vid, runs[i]))
                b = series.get((vid, runs[j]))
                if a is None or b is None:
                    continue
                rows.append(("same", vid, runs[i], vid, runs[j],
                             pearson(a, b), rmse(a, b)))

    for i in range(len(vids)):
        for j in range(i + 1, len(vids)):
            for r1 in runs:
                for r2 in runs:
                    a = series.get((vids[i], r1))
                    b = series.get((vids[j], r2))
                    if a is None or b is None:
                        continue
                    rows.append(("different", vids[i], r1, vids[j], r2,
                                 pearson(a, b), rmse(a, b)))

    pairs_csv = out_dir / "pli_similarity_pairs.csv"
    with open(pairs_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_type", "vid_a", "run_a", "vid_b", "run_b",
                    "pearson_r", "rmse"])
        w.writerows(rows)


    summary = []

    for name, key, col, higher_better in [
        ("Pearson", "pearson_r", 5, True),
        ("RMSE",    "rmse",      6, False),
    ]:
        same = np.array([r[col] for r in rows if r[0] == "same"], dtype=np.float64)
        diff = np.array([r[col] for r in rows if r[0] == "different"], dtype=np.float64)
        same = same[np.isfinite(same)]
        diff = diff[np.isfinite(diff)]

        summary.append(f"=== {name} ===")
        if same.size:
            summary.append(f"same      n={same.size:4d}  mean={same.mean():.4g}  "
                           f"median={np.median(same):.4g}  "
                           f"min={same.min():.4g}  max={same.max():.4g}")
        if diff.size:
            summary.append(f"different n={diff.size:4d}  mean={diff.mean():.4g}  "
                           f"median={np.median(diff):.4g}  "
                           f"min={diff.min():.4g}  max={diff.max():.4g}")

        if same.size and diff.size:
            pos = same if higher_better else -same
            neg = diff if higher_better else -diff
            d = pos[:, None] - neg[None, :]
            auc = float((d > 0).mean() + 0.5 * (d == 0).mean())
            summary.append(f"AUC = {auc:.4g}")
        summary.append("")

        plt.figure()
        plt.boxplot([same, diff], tick_labels=["same", "different"], showfliers=True)
        plt.title(f"{name} (cumsum, normalize=final)")
        plt.ylabel("corr (higher=more similar)" if higher_better
                   else "dist (lower=more similar)")
        plt.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(out_dir / f"box_{key}.png", dpi=200)
        plt.close()


    (out_dir / "summary.txt").write_text("\n".join(summary), encoding="utf-8")

    print(f"pairs   : {pairs_csv}")
    print(f"summary : {out_dir / 'summary.txt'}")


if __name__ == "__main__":
    main()
