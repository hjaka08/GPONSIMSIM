import argparse
import csv
from dataclasses import dataclass


# BCH(39,12,2) generator: x^12 + x^10 + x^8 + x^5 + x^4 + x^3 + 1 
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
    
    from scapy.all import PcapReader
    with PcapReader(path) as pr:
        for pkt in pr:
            yield float(getattr(pkt, "time", 0.0)), bytes(pkt)
    


def aes_ctr(key, nonce, data):
    # G.984.3 12.2 : 다운스트림은 GEM 페이로드만 AES로 암호화한다.
    # 길이는 그대로라서 PLI 값은 안 바뀜 -> 사실 실험에는 필요 없을지도?
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
    ctr = Counter.new(128, initial_value=nonce)
    return AES.new(key, AES.MODE_CTR, counter=ctr).encrypt(data)


@dataclass
class Gem:
    gid: int
    pti: int
    pli: int
    header: bytes
    payload: bytes
    arrival_us: float


ENC_KEY   = None         # 16바이트 키를 넣으면 페이로드를 AES-CTR로 암호화
PORT_ID   = 0x101
MAX_PLI   = 4095
GEM_HDR   = 5            
LINE_RATE = 2.48832e9    #GPON이므로 2.5Gbps..
FRAME_US  = 125.0        


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
            pti = 0b001 if is_last else 0b000
            frag = eth[off:off + take]
            hdr = gem_header(take, PORT_ID, pti)



            if ENC_KEY is not None:
                frag = aes_ctr(ENC_KEY, gid, frag)

            gems.append(Gem(gid, pti, take, hdr, frag, rel_us))
            gid += 1
            off += take

    return gems


def pack(gems, out_bin, frames_csv, gems_csv, pcbd_bytes):
    frame_total = int(round(LINE_RATE * FRAME_US * 1e-6 / 8.0))
    budget = frame_total - pcbd_bytes
    if budget <= 0:
        raise ValueError("pcbd_bytes too big")

    starts = []
    cur = 0.0
    for g in gems:
        s = max(g.arrival_us, cur)
        starts.append(s)
        cur = s + (GEM_HDR + g.pli) * 8.0 / LINE_RATE * 1e6

    with open(out_bin, "wb") as fb, \
         open(frames_csv, "w", newline="", encoding="utf-8") as ff, \
         open(gems_csv,   "w", newline="", encoding="utf-8") as fg:

        fw = csv.writer(ff)
        fw.writerow(["frame_idx", "t_start_us", "t_end_us",
                     "frame_bytes_total", "pcbd_bytes", "payload_used_bytes"])

        gw = csv.writer(fg)
        gw.writerow(["gem_id", "port_id", "pti", "pli",
                     "start_frame", "start_off_in_payload",
                     "end_frame",   "end_off_in_payload",
                     "t_start_us",  "t_end_us"])

        frame_idx = 0
        used = 0
        in_frame = False

        def open_frame():
            fb.write(b"\x00" * pcbd_bytes)

        def close_frame(idx, u):
            if u < budget:
                fb.write(b"\x00" * (budget - u))
            fw.writerow([idx,
                         f"{idx*FRAME_US:.3f}",
                         f"{(idx+1)*FRAME_US:.3f}",
                         frame_total, pcbd_bytes, u])

        for i, g in enumerate(gems):
            tgt = int(starts[i] // FRAME_US)

         
            if in_frame and tgt > frame_idx:
                close_frame(frame_idx, used)
                in_frame = False
                used = 0

            if not in_frame:
                frame_idx = tgt
                open_frame()
                in_frame = True
                used = 0

         
            need = GEM_HDR if g.pli == 0 else GEM_HDR + 1
            while budget - used < need:
                close_frame(frame_idx, used)
                frame_idx += 1
                open_frame()
                used = 0

          
            t0 = frame_idx * FRAME_US + used * 8.0 / LINE_RATE * 1e6
            sf, so = frame_idx, used
            fb.write(g.header)
            used += GEM_HDR

       
            poff, n = 0, len(g.payload)
            while poff < n:
                room = budget - used
                if room <= 0:
                    close_frame(frame_idx, used)
                    frame_idx += 1
                    open_frame()
                    used = 0
                    room = budget
                take = min(n - poff, room)
                fb.write(g.payload[poff:poff + take])
                used += take
                poff += take

            t1 = frame_idx * FRAME_US + used * 8.0 / LINE_RATE * 1e6
            gw.writerow([g.gid, PORT_ID, g.pti, g.pli,
                         sf, so, frame_idx, used,
                         f"{t0:.3f}", f"{t1:.3f}"])

        if in_frame:
            close_frame(frame_idx, used)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcap", required=True)
    ap.add_argument("--out-gtc",    default="out_gtc.bin")
    ap.add_argument("--frames-csv", default="frames.csv")
    ap.add_argument("--gems-csv",   default="gems.csv")
    ap.add_argument("--pcbd-bytes", type=int, default=40)
    ap.add_argument("--aes-key", default=None, help="16바이트 hex 키 (실험용)")
    args = ap.parse_args()

    global ENC_KEY
    if args.aes_key:
        ENC_KEY = bytes.fromhex(args.aes_key)

    gems = build_gems(args.pcap)
    pack(gems, args.out_gtc, args.frames_csv, args.gems_csv, args.pcbd_bytes)
    print(f"done. gem={len(gems)} -> {args.gems_csv}")


if __name__ == "__main__":
    main()