import argparse
from dataclasses import dataclass

from scapy.all import PcapReader


BCH_POLY = (1 << 12) | (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 3) | 1


def bch_rem(data27):
    reg = data27 << 12
    for b in range(38, 11, -1):
        if (reg >> b) & 1:
            reg ^= BCH_POLY << (b - 12)
    return reg & 0xFFF


def gem_header(pli, port_id, pti):
    data27 = (pli << 15) | (port_id << 3) | pti
    bch = bch_rem(data27)
    code39 = (data27 << 12) | bch
    par = bin(code39).count("1") & 1
    hec13 = (bch << 1) | par
    return ((data27 << 13) | hec13).to_bytes(5, "big")


def iter_pcap(path):
    with PcapReader(path) as pr:
        for pkt in pr:
            yield float(getattr(pkt, "time", 0.0)), bytes(pkt)


@dataclass
class Gem:
    gid: int
    pti: int
    pli: int
    header: bytes
    payload: bytes
    arrival_us: float


PORT_ID   = 0x101
MAX_PLI   = 4095         # PLI가 12bit라서 4095가 최대 (G.984.3 8.3.1)
GEM_HDR   = 5            # GEM 헤더 5바이트
LINE_RATE = 2.48832e9    #GPON이므로 2.5Gbps..
FRAME_US  = 125.0        # GTC 프레임 하나가 125us (38880 byte)


def build_gems(pcap_path):
    gems = []
    gid = 0
    first = None

    for ts, eth in iter_pcap(pcap_path):
        if first is None:
            first = ts
        rel_us = max(0.0, (ts - first) * 1e6)

        off, n = 0, len(eth)
        while off < n:
            take = min(MAX_PLI, n - off)
            is_last = off + take == n
            pti = 0b001 if is_last else 0b000    # 마지막 조각이면 001
            frag = eth[off:off + take]
            hdr = gem_header(take, PORT_ID, pti)

            gems.append(Gem(gid, pti, take, hdr, frag, rel_us))
            gid += 1
            off += take

    return gems


def pack(gems, out_bin, pcbd_bytes):
    frame_total = int(round(LINE_RATE * FRAME_US * 1e-6 / 8.0))   # 38880
    budget = frame_total - pcbd_bytes
    if budget <= 0:
        raise ValueError("pcbd_bytes too big")

    with open(out_bin, "wb") as fb:
        used = 0
        fb.write(b"\x00" * pcbd_bytes)

        for g in gems:
            if budget - used < GEM_HDR + 1:
                fb.write(b"\x00" * (budget - used))
                fb.write(b"\x00" * pcbd_bytes)
                used = 0

            fb.write(g.header)
            used += GEM_HDR
            fb.write(g.payload)
            used += g.pli

        if used < budget:
            fb.write(b"\x00" * (budget - used))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", required=True)
    args = ap.parse_args()

    gems = build_gems(args.pcap)
    pack(gems, "out_gtc.bin", 40)
    print("gem =", len(gems))


if __name__ == "__main__":
    main()
