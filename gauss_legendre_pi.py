import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, getcontext

def sqrt_decimal(x, context):
    # 自己实现高精度sqrt以便并发
    getcontext().prec = context.prec
    s = x / 2
    last_s = None
    while last_s != s:
        last_s = s
        s = (s + x / s) / 2
    return +s  # 一元+触发decimal舍入

def gauss_legendre_pi(digits, n_threads, progress_callback=None):
    getcontext().prec = digits + 10
    a = Decimal(1)
    b = Decimal(1) / sqrt_decimal(Decimal(2), getcontext())
    t = Decimal('0.25')
    p = Decimal(1)

    total_iters = int(2.5 * (digits**0.5))  # 经验足够10~30轮，100万位约25轮
    total_iters = min(max(total_iters, 10), 40)

    start_time = time.time()
    for i in range(total_iters):
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = {}
            futures['a_next'] = executor.submit(lambda: (a + b) / 2)
            futures['b_next'] = executor.submit(sqrt_decimal, a * b, getcontext())

            results = {}
            for name, fut in futures.items():
                results[name] = fut.result()
            a_next = results['a_next']
            b_next = results['b_next']

        t -= p * (a - a_next) ** 2
        a = a_next
        b = b_next
        p *= 2

        if progress_callback:
            elapsed = time.time() - start_time
            est_digits = int((i + 1) / total_iters * digits)
            progress_callback(i + 1, total_iters, est_digits, elapsed)
    pi = ((a + b) ** 2) / (4 * t)
    return str(+pi)[:digits + 2]

def progress_bar(cur, total, width=30):
    f = cur / total
    left = int(f * width)
    bar = '=' * left + '>' + '.' * (width - left - 1)
    return f"[{bar}] {100*f:.2f}%"

def progress_thread_fn(state, total_digits, total_iters):
    while not state['done']:
        i = state['iter']
        est_digits = state['digits']
        elapsed = state['elapsed']
        print(
            f"\r迭代: {i}/{total_iters}  线程: {state['threads']}  "
            f"已计算位数: {est_digits}  用时: {elapsed:.2f}s  "
            f"{progress_bar(i, total_iters)}",
            end='', flush=True
        )
        time.sleep(0.2)
    print()  # 换行

def main():
    parser = argparse.ArgumentParser(description='多线程高斯-勒让德算法计算π')
    parser.add_argument('--digits', type=int, default=1000, help='计算π的精度（小数位数）')
    parser.add_argument('--threads', type=int, default=10, help='并行线程数')
    args = parser.parse_args()

    state = {
        'iter': 0,
        'digits': 0,
        'elapsed': 0,
        'threads': args.threads,
        'done': False
    }
    total_iters = int(2.5 * (args.digits**0.5))
    total_iters = min(max(total_iters, 10), 40)

    t = threading.Thread(
        target=progress_thread_fn,
        args=(state, args.digits, total_iters),
        daemon=True
    )
    t.start()

    def progress_callback(i, n, est_digits, elapsed):
        state['iter'] = i
        state['digits'] = est_digits
        state['elapsed'] = elapsed

    t1 = time.time()
    pi = gauss_legendre_pi(args.digits, args.threads, progress_callback)
    t2 = time.time()
    state['done'] = True
    time.sleep(0.3)

    print(f"计算完成，总用时 {t2-t1:.2f}s")
    print(f"π的前{args.digits}位：\n{pi}")

if __name__ == '__main__':
    main()
