import concurrent

from database.mongo.get_data import select_model_type,load_model_file,load_threshold_model,get_all_current_data_new,get_current_by_time
from database.mongo.save_model import update_present_model,save_threshold_model
from database.mongo.usage_table import add_machine_time,add_machine_time_to_old
from calculate_model.test import calculate_machine_time_kmeans_bydata
from calculate_model.threshold import calculate_machine_time_bydata
from calculate_model.get_time import get_timestamp_of_previous_n_days
from calculate_model.model_modification import get_data_list
from calculate_model.process_data import compress_data
from database.mysql.query_status_regular import query_all_imeis
from calculate_model.multithreaded_processing import mul_thread_methods
# 日志
from log.log import logger

# 批量计算仪器机时并保存
def batch_machine_time_retest():
    imeiList = query_all_imeis()
    mul_thread_methods(imeiList,machine_time_retest,50)

# 批量计算仪器机时并保存
def batch_machine_time_retest(start,end):
    imeiList = query_all_imeis()
    mul_thread_methods_retest(imeiList,start,end,machine_time_retest,50)

# 多线程方法
def mul_thread_methods_retest(imei_list,start,end,method_name,threads_count):
    # 使用 ThreadPoolExecutor 创建一个线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
        # 提交测试任务给线程池
        future_to_imei = {executor.submit(method_name, imei,start,end): imei for imei in imei_list}

        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_imei):
            imei = future_to_imei[future]
            try:
                future.result()  # 获取任务的结果
            except Exception as e:
                logger.error(f"[machineTime_test] Error testing IMEI {imei}: {e}")
                print(f"Error testing IMEI {imei}: {e}")
    print("所有IMEI处理完毕")

# 重新计算机时并保存
def machine_time_retest(imei,startTime = 1711296000000, endTime = 1711728000000):
    # 获取前 2 天零点的时间戳
    twodayago_time = get_timestamp_of_previous_n_days(2)
    # 判断日期在哪个范围
    # 历史
    if endTime <= twodayago_time:
        print("历史电流")
        machine_time_retest_old(imei,startTime, endTime)
    # 未归档
    elif startTime >= twodayago_time:
        print("未归档电流")
        machine_time_retest_new(imei)
    else:
        print("all电流")
        machine_time_retest_old(imei,startTime, twodayago_time)
        machine_time_retest_new(imei)


# 重新计算机时并保存（历史表）
def machine_time_retest_old(imei,startTime, endTime):
    # 获取电流并解压缩
    dataList = get_current_by_time(imei, startTime, endTime)
    modified_list = []
    if dataList:
        for dt in dataList:
            data,date,deviceType = dt
            # 根据数据计算机时
            modified_data = calculate_machine_time_by_data(imei,data)
            modified_list.append((modified_data,date,deviceType))
        print(modified_list)
        # 存储到历史机时库
        add_machine_time_old(imei,modified_list)


# 重新计算机时并保存（暂存表）
def machine_time_retest_new(imei):
    # 根据imei获取所有电流（暂存表）
    dt = get_all_current_data_new(imei)
    if dt:
        data,deviceType = get_data_list(dt)
        # 根据数据计算机时
        modified_list = calculate_machine_time_by_data(imei, data)
        print(modified_list)
        # 存储机时到未归档库
        add_machine_time_new(imei,modified_list,deviceType)
    else:
        logger.info(f'[machineTime_test] {imei} 空数据')


# 根据数据计算机时
def calculate_machine_time_by_data(imei,valueData):
    # 查询使用的模型类型
    document = select_model_type(imei)
    # 使用kmeans模型 如果模型类型为 0，则调用 test_by_kmeans() 方法进行测试，否则调用 test_by_threshold() 方法进行测试。
    modified_list = []
    if document['type'] == 0:
        # 加载kmeans模型
        loaded_file = load_model_file(imei)
        # 没有模型就跳过
        if loaded_file == None:
            logger.info(f'[machineTime_test] {imei} kmeans模型表里没有模型')
            update_present_model(imei, 1, 0)
            return
        loaded_model, ignore_length, real_k = loaded_file
        modified_list = calculate_machine_time_kmeans_bydata(valueData,loaded_model,real_k,ignore_length)
    # 使用阈值模型
    else:
        # 从数据库中读取模型
        model = load_threshold_model(imei)
        # 如果数据库中没有
        if model == None:
            logger.info(f'[machineTime_test] {imei} threshold模型表里没有模型')
            # 默认的阈值
            props = {
                'U_close': 0.03,
                'U_standby': 0.04,
                'U_run': 0.5
            }
            ignore_length = 0
            real_k = 4
            # 存储阈值模型
            save_threshold_model(imei, props, ignore_length, real_k)
        props, ignore_length, real_k = model
        modified_list = calculate_machine_time_bydata(imei, valueData, props, ignore_length, real_k)
    return modified_list


# 存储机时到历史库
def add_machine_time_old(imei,modified_list):
    res_list = []
    for dt in modified_list:
        data,date,deviceType = dt
        compressed_list = compress_data(data)
        doc = {
            'dataList': compressed_list,
            'date': int(date),
            'deviceType': deviceType
        }
        res_list.append(doc)
    add_machine_time_to_old(imei,res_list)


# 存储机时到未归档库
def add_machine_time_new(imei,modified_list,deviceType):
    add_machine_time(imei,modified_list,deviceType,1)



imei = '866497066698789'
# start = 1711555200000
# end = 1711641600000

start = 1711468800000
end = 1711728000000

if __name__ == '__main__':
    batch_machine_time_retest()