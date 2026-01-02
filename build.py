import glob, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed


def making(job):
    frames, gems = job["frames_csv"], job["gems_csv"]
    os.makedirs(os.path.dirname(frames), exist_ok=True)

    cmd = [sys.executable, "generate.py",
           "--pcap", job["pcap"],
           "--frames-csv", frames,
           "--gems-csv", gems,
           "--pcbd-bytes", "40"]

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return job, "FAIL", f"ret={proc.returncode}"
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

ok, fail = 0, 0
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(making, j) for j in jobs]
    for i, fut in enumerate(as_completed(futures), 1):
        job, status, msg = fut.result()
        if status == "OK":
            ok += 1
        else:
            fail += 1
        if i % 10 == 0 or i == len(futures):
            print(f"[{i}/{len(futures)}] OK={ok} FAIL={fail}")

print(f"끝. OK={ok} FAIL={fail} ")
print("ROGER Affirmative; success")
