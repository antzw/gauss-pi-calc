from decimal import Decimal, getcontext

def gauss_legendre_pi(digits):
    getcontext().prec = digits + 5  # 多保留几位精度，防止尾数误差
    a = Decimal(1)
    b = Decimal(1) / Decimal(2).sqrt()
    t = Decimal('0.25')
    p = Decimal(1)
    for _ in range(10):  # 10次迭代足够算出100位
        a_next = (a + b) / 2
        b = (a * b).sqrt()
        t -= p * (a - a_next) ** 2
        a = a_next
        p *= 2
    pi = ((a + b) ** 2) / (4 * t)
    return str(pi)[:digits + 2]  # 包含 "3."

if __name__ == "__main__":
    digits = 1000000
    pi = gauss_legendre_pi(digits)
    print(f"π的前{digits}位（高斯-勒让德算法）：\n{pi}")
