import schedule
from calculate_model.no_model_imeis_retrain import no_model_imeis_retrain
from calculate_model.multithreaded_processing import mul_thread_test
import time
from calculate_model.get_time import get_timestamp_of_previous_n_days
from database.mongo.usage_table import delete_documents_matching_condition

def delete_machine_table_by_time():
    # 例如，获取前 2 天零点的时间戳
    n_days_ago_timestamp = get_timestamp_of_previous_n_days(2)
    delete_documents_matching_condition(n_days_ago_timestamp)

# 定时计算机时
def timer_task_test():
    # 一直执行查询计算，中间不间隔
    while True:
        mul_thread_test()
    # scheduler = schedule.Scheduler()
    # scheduler.every(1).seconds.do(mul_thread_test)
    # # 循环执行定时任务
    # while True:
    #     scheduler.run_pending()
    #     time.sleep(1)  # 休眠1秒

# 定时训练模型
def timer_task_train():
    # 定义一个任务，安排在每天的00:00执行
    scheduler1 = schedule.Scheduler()
    scheduler1.every().day.at("00:00").do(no_model_imeis_retrain)
    # 循环执行定时任务
    while True:
        scheduler1.run_pending()
        time.sleep(1)  # 休眠1秒

# 定时清理机时数据库
def clear_machine_table():
    scheduler2 = schedule.Scheduler()
    scheduler2.every().day.at("03:00").do(delete_machine_table_by_time)
    # 循环执行定时任务
    while True:
        scheduler2.run_pending()
        time.sleep(1)  # 休眠1秒

if __name__ == "__main__":
    timer_task_test()



