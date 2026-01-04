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


    print(f"pairs   : {pairs_csv}")


if __name__ == "__main__":
    main()
