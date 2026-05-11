import multiprocessing
from api.request import run_fastapi_app
from calculate_model.timer_tasks import timer_task_train,timer_task_test,clear_machine_table

import psutil
import os

# windows
def set_cpu_limit():
    try:
        # 获取系统的逻辑 CPU 数量
        num_cpus = psutil.cpu_count(logical=True)

        # 设置每个进程的 CPU 限制为总逻辑 CPU 数量的一部分，例如限制为总数的 50%
        cpu_limit_percent = 30
        cpu_limit = int(num_cpus * (cpu_limit_percent / 100.0))

        # 获取当前进程的 PID
        pid = os.getpid()

        # 创建 psutil.Process 对象
        process = psutil.Process(pid)

        # 设置每个进程的 CPU 限制
        process.cpu_affinity(list(range(cpu_limit)))

        print(f"CPU affinity set successfully for process {pid}.")
    except Exception as e:
        print(f"Error setting CPU affinity: {e}")

# 主线程
def main():
    # 设置 CPU 限制
    set_cpu_limit()

    multiprocessing.log_to_stderr()
    # 创建三个进程，分别运行 FastAPI 应用和两个定时任务
    app_process = multiprocessing.Process(target=run_fastapi_app)
    app_process.start()

    schedule_process_1 = multiprocessing.Process(target=timer_task_test)
    schedule_process_1.start()

    schedule_process_2 = multiprocessing.Process(target=timer_task_train)
    schedule_process_2.start()

    schedule_process_3 = multiprocessing.Process(target=clear_machine_table)
    schedule_process_3.start()

    app_process.join()
    schedule_process_1.join()
    schedule_process_2.join()
    schedule_process_3.join()


if __name__ == "__main__":
    main()

