import numpy as np
from database.mongo.get_data import load_imeis_have_model
from database.mysql.query_status_regular import query_all_imeis
from calculate_model.train import batch_train_by_imeilist
import multiprocessing
# 日志
from log.log import logger

# 得到没有模型的设备imei
def compared_no_model_imeis():
    have_model_imeis = load_imeis_have_model()
    all_imeis = query_all_imeis()
    # 得到在all_imeis  ，但不在have_model_imeis中的所有元素
    no_model_imeis = np.setdiff1d(all_imeis,have_model_imeis)
    return no_model_imeis

# 重新训练模型
# def no_model_imeis_retrain():
#     logger.info('[model_train]定时任务，模型计算开始')
#     imeis_list = compared_no_model_imeis()[:100]
#     batch_train_by_imeilist(imeis_list,10)
#     logger.info('[model_train]定时任务，模型计算结束')

# 重新训练模型,多进程
def no_model_imeis_retrain():
    logger.info('[model_train]定时任务，模型计算开始')
    imeis_list = compared_no_model_imeis()
    # 要使用的进程数量
    num_processes = 2

    # 将数据分成用于每个进程的小块
    chunk_size = len(imeis_list) // num_processes
    if chunk_size == 0:
        data_chunks = [imeis_list]
    else:
        data_chunks = split_data(imeis_list, chunk_size)
    # 创建一个进程池
    with multiprocessing.Pool(processes=num_processes) as pool:
        # 将 compute_task 函数映射到每个数据块，以并行方式执行
        pool.map(batch_train_by_imeilist, data_chunks)
    logger.info('[model_train]定时任务，模型计算结束')


def split_data(data, chunk_size):
    # 将数据分成小块
    return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

if __name__ == "__main__":
    # import cProfile
    # 保存结果到文件
    # cProfile.run('no_model_imeis_retrain()', filename='profile_result.txt')
    no_model_imeis_retrain()


