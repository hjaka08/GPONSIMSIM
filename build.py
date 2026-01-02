import glob, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed


def making(job):
    frames, gems = job["frames_csv"], job["gems_csv"]

    if all(os.path.isfile(p) and os.path.getsize(p) > 0 for p in (frames, gems)):
        return job, "SKIP", "already exists"

    os.makedirs(os.path.dirname(frames), exist_ok=True)
    tmp_f, tmp_g = frames + ".tmp", gems + ".tmp"

   




    cmd = [sys.executable, "generate.py",
           "--pcap", job["pcap"],
           "--frames-csv", tmp_f,
           "--gems-csv", tmp_g,
           "--pcbd-bytes", "40"]

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return job, "FAIL", f"exception: {e!r}"

    if proc.returncode != 0 or not (os.path.isfile(tmp_f) and os.path.isfile(tmp_g)):
        for p in (tmp_f, tmp_g):
            if os.path.isfile(p):
                try: os.remove(p)
                except OSError: pass
        err = (proc.stderr or "").strip().splitlines()
        return job, "FAIL", err[-1] if err else f"ret={proc.returncode}"

    os.replace(tmp_f, frames)
    os.replace(tmp_g, gems)
    return job, "OK", f"{time.time()-t0:.1f}s"


jobs = []
for pcap in sorted(glob.glob("pcaps/*/*/*.pcap")):
    run   = os.path.splitext(os.path.basename(pcap))[0]
    cid   = os.path.basename(os.path.dirname(pcap))
    group = os.path.basename(os.path.dirname(os.path.dirname(pcap)))
    out_dir = os.path.join("data", group, cid)
    jobs.append({
        "group": group, "id": cid, "run": run, "pcap": pcap,
        "frames_csv": os.path.join(out_dir, f"{run}.csv"),
        "gems_csv":   os.path.join(out_dir, f"{run}.gems.csv"),
    })

if not jobs:
    sys.exit("Negative; there's no pcap files.. ")



ok, fail, skip = 0, 0, 0
t0 = time.time()

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(making, j) for j in jobs]
    for i, fut in enumerate(as_completed(futures), 1):
        job, status, msg = fut.result()
        if   status == "OK":   ok   += 1
        elif status == "SKIP": skip += 1
        else:                  fail += 1
        if i % 10 == 0 or i == len(futures):
            print(f"[{i}/{len(futures)}] OK={ok} SKIP={skip} FAIL={fail}")

print(f"끝. OK={ok} SKIP={skip} FAIL={fail} ")
print("ROGER Affirmative; success")

if fail > 0:
    sys.exit("Negative; hmmm there's failed work")