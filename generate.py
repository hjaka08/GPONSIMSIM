# GPON GEM 헤더 만들기 연습
# ITU-T G.984.3 8.3.1 : PLI(12) + Port-ID(12) + PTI(3) + HEC(13) = 40bit = 5byte


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
    par = bin(code39).count("1") & 1     # 40bit 안의 1 개수를 짝수로
    hec13 = (bch << 1) | par
    return ((data27 << 13) | hec13).to_bytes(5, "big")


if __name__ == "__main__":
    print(gem_header(1500, 0x101, 1).hex())
