# 만든 GEM 헤더가 진짜 규격대로 나오는지 확인하는 스크립트
# G.984.3 8.3.1 : 앞 39비트를 생성다항식으로 나눈 나머지가 0이어야 하고,
#                 헤더 40비트 안의 1의 개수는 짝수여야 한다.

import random

from generate import BCH_POLY, bch_rem, gem_header


def syndrome(code39):
    reg = code39
    for b in range(38, 11, -1):
        if (reg >> b) & 1:
            reg ^= BCH_POLY << (b - 12)
    return reg & 0xFFF


bad = 0
for _ in range(10000):
    pli = random.randrange(0, 4096)
    port = random.randrange(0, 4096)
    pti = random.choice([0b000, 0b001])

    h = gem_header(pli, port, pti)
    v = int.from_bytes(h, "big")

    if len(h) != 5:
        bad += 1
    if syndrome(v >> 1) != 0:
        bad += 1
    if bin(v).count("1") % 2 != 0:
        bad += 1

print("bad =", bad)
