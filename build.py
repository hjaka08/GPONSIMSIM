import glob, os, subprocess, sys

# pcaps/<group>/<vid>/<run>.pcap 를 전부 generate.py 로 돌린다

for pcap in sorted(glob.glob("pcaps/*/*/*.pcap")):
    run   = os.path.splitext(os.path.basename(pcap))[0]
    cid   = os.path.basename(os.path.dirname(pcap))
    group = os.path.basename(os.path.dirname(os.path.dirname(pcap)))
    out_dir = os.path.join("data", group, cid)
    os.makedirs(out_dir, exist_ok=True)

    frames = os.path.join(out_dir, f"{run}.csv")
    gems   = os.path.join(out_dir, f"{run}.gems.csv")

    cmd = [sys.executable, "generate.py",
           "--pcap", pcap,
           "--frames-csv", frames,
           "--gems-csv", gems,
           "--pcbd-bytes", "40"]

    print(" ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        sys.exit("Negative; generate.py failed")

print("ROGER Affirmative; success")
