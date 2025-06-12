import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, getcontext

def sqrt_decimal(x, context):
    """
    高精度开方，使用牛顿迭代法实现，以支持 decimal 多线程环境下的高精度 sqrt。
    参数:
        x: 要开方的 Decimal 数
        context: decimal.Context 对象，决定精度
    返回:
        Decimal: x 的平方根
    """
    getcontext().prec = context.prec    # 设置当前线程 decimal 精度
    s = x / 2                           # 初始猜测
    last_s = None
    while last_s != s:                  # 牛顿迭代
        last_s = s
        s = (s + x / s) / 2
    return +s                           # 一元+触发 decimal 的舍入

def gauss_legendre_pi(digits, n_threads, progress_callback=None):
    """
    使用高斯-勒让德算法并行计算高精度π。
    参数:
        digits: 小数精度（位数）
        n_threads: 并行线程数
        progress_callback: 进度回调函数，每次迭代时调用，用于展示进度
    返回:
        str: 计算得出的π，字符串形式，保留 digits 位
    """
    # 设置 decimal 精度
    getcontext().prec = digits + 10

    # 初始化算法变量
    a = Decimal(1)
    b = Decimal(1) / sqrt_decimal(Decimal(2), getcontext())
    t = Decimal('0.25')
    p = Decimal(1)

    # 预估迭代轮数（经验公式）
    total_iters = int(2.5 * (digits**0.5))      # 经验公式，100万位约25轮
    total_iters = min(max(total_iters, 10), 40) # 迭代次数限制在10~40之间

    start_time = time.time()
    for i in range(total_iters):
        # 用线程池并发计算 a_next 和 b_next
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = {}
            futures['a_next'] = executor.submit(lambda: (a + b) / 2)
            futures['b_next'] = executor.submit(sqrt_decimal, a * b, getcontext())

            results = {}
            for name, fut in futures.items():
                results[name] = fut.result()
            a_next = results['a_next']
            b_next = results['b_next']

        # 按算法更新变量
        t -= p * (a - a_next) ** 2
        a = a_next
        b = b_next
        p *= 2

        # 进度回调
        if progress_callback:
            elapsed = time.time() - start_time
            est_digits = int((i + 1) / total_iters * digits)
            progress_callback(i + 1, total_iters, est_digits, elapsed)

    # 最终π计算
    pi = ((a + b) ** 2) / (4 * t)
    return str(+pi)[:digits + 2]   # 字符串截取，保留 digits 位（含"3."）

def progress_bar(cur, total, width=30):
    """
    格式化进度条字符串
    参数:
        cur: 当前进度
        total: 总进度
        width: 进度条宽度（字符数）
    返回:
        str: 格式化后的进度条
    """
    f = cur / total
    left = int(f * width)
    bar = '=' * left + '>' + '.' * (width - left - 1)
    return f"[{bar}] {100*f:.2f}%"

def progress_thread_fn(state, total_digits, total_iters):
    """
    进度条显示线程函数，实时打印迭代进度
    参数:
        state: dict, 包含当前迭代数、估算位数、用时等信息
        total_digits: 总精度
        total_iters: 总迭代次数
    """
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
    """
    主程序入口：
    1. 解析命令行参数
    2. 启动进度显示线程
    3. 调用高斯-勒让德算法计算π
    4. 输出结果
    """
    parser = argparse.ArgumentParser(description='多线程高斯-勒让德算法计算π')
    parser.add_argument('--digits', type=int, default=1000, help='计算π的精度（小数位数）')
    parser.add_argument('--threads', type=int, default=10, help='并行线程数')
    args = parser.parse_args()

    # 用 state 记录进度信息
    state = {
        'iter': 0,
        'digits': 0,
        'elapsed': 0,
        'threads': args.threads,
        'done': False
    }
    total_iters = int(2.5 * (args.digits**0.5))
    total_iters = min(max(total_iters, 10), 40)

    # 启动进度条线程
    t = threading.Thread(
        target=progress_thread_fn,
        args=(state, args.digits, total_iters),
        daemon=True
    )
    t.start()

    # 进度回调函数，更新 state
    def progress_callback(i, n, est_digits, elapsed):
        state['iter'] = i
        state['digits'] = est_digits
        state['elapsed'] = elapsed

    # 开始计算π
    t1 = time.time()
    pi = gauss_legendre_pi(args.digits, args.threads, progress_callback)
    t2 = time.time()
    state['done'] = True
    time.sleep(0.3)  # 确保进度线程最后一次刷新

    print(f"计算完成，总用时 {t2-t1:.2f}s")
    print(f"π的前{args.digits}位：\n{pi}")

if __name__ == '__main__':
    main()