import argparse

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", required=True)
    args = ap.parse_args()

    n = 0
    for ts, eth in iter_pcap(args.pcap):
        n += 1
    print("packets =", n)


if __name__ == "__main__":
    main()
