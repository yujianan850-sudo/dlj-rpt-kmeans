import concurrent.futures
from database.mysql.query_status_regular import query_update_imeis
from calculate_model.test import test_by_kmeans
from calculate_model.threshold import test_by_threshold
from database.mongo.get_data import query_all_imeis_in_present_model,select_model_type
from database.mongo.save_model import update_present_model
# 日志
from log.log import logger

# 多线程测试，即定时任务（半小时执行一次的）
def mul_thread_test():
    # logger.info('[machineTime_test]定时任务，计算机时开始')
    # 获取更新的imei
    imei_list = query_update_imeis()
    # 获取当前模型表中的所有 IMEI 列表。
    imei_list_in_present_model = query_all_imeis_in_present_model()
    if imei_list != None:
        print(imei_list,'imei_list')
        # 使用集合操作符计算出在更新的 IMEI 列表中但不在当前模型表中的 IMEI 列表，并赋值给 imei_list_creat_model
        imei_list_creat_model = list(set(imei_list) - set(imei_list_in_present_model))
        # 新的仪器，模型表里没有的，设置默认模型为阈值模型
        if len(imei_list_creat_model) != 0:
            for imei in imei_list_creat_model:
                update_present_model(imei,1,0)
        mul_thread_methods(imei_list,test,50)
    # logger.info('[machineTime_test]定时任务，计算机时结束')

# 现有模型计算今日
def test(imei):
    # 查询使用的模型类型
    document = select_model_type(imei)
    # 使用kmeans模型 如果模型类型为 0，则调用 test_by_kmeans() 方法进行测试，否则调用 test_by_threshold() 方法进行测试。
    if document['type'] == 0:
        test_by_kmeans(imei)
    # 使用阈值模型
    else:
        test_by_threshold(imei)

# 多线程方法
def mul_thread_methods(imei_list,method_name,threads_count):
    # 使用 ThreadPoolExecutor 创建一个线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads_count) as executor:
        # 提交测试任务给线程池
        future_to_imei = {executor.submit(method_name, imei): imei for imei in imei_list}

        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_imei):
            imei = future_to_imei[future]
            try:
                future.result()  # 获取任务的结果
            except Exception as e:
                logger.error(f"[machineTime_test] Error testing IMEI {imei}: {e}")
                print(f"Error testing IMEI {imei}: {e}")
    print("所有IMEI处理完毕")




if __name__ == "__main__":
    mul_thread_test()









