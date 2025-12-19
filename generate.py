# GPON GEM 헤더 만들기 연습
# ITU-T G.984.3 8.3.1 : HEC = BCH(39,12,2) + parity 1bit
# 생성 다항식 x^12 + x^10 + x^8 + x^5 + x^4 + x^3 + 1


BCH_POLY = (1 << 12) | (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 3) | 1


def bch_rem(data27):
    reg = data27 << 12
    for b in range(38, 11, -1):
        if (reg >> b) & 1:
            reg ^= BCH_POLY << (b - 12)
    return reg & 0xFFF


if __name__ == "__main__":
    print(hex(bch_rem(0x1234567)))
