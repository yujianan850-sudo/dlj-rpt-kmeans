import numpy as np
# 日志
from log.log import logger
from calculate_model.process_data import sequence_processing,label_reset,compress_and_modify_states
from calculate_model.rpt import generate_seglist
from database.mongo.get_data import load_model_file
from database.mongo.usage_table import select_current_by_time,add_machine_time,select_current_by_time
from database.mongo.save_model import update_present_model
from calculate_model.draw import draw

# kmeans测试模型
def kmeans_test(data,loaded_file):
    length = loaded_file['length']
    # 赋值
    model = loaded_file['kmeans_model']
    U_close = loaded_file['U_close']
    pen = loaded_file['pen']
    features = loaded_file['features']
    k = loaded_file['k']
    mean_seg = loaded_file['mean_seg']
    # 预处理----分割
    try:
        seg_data = generate_seglist(data, length, pen)
    except:
        seg_data = np.array([data])
    # 生成训练数据
    test_data,labels_neg,seq_pos = sequence_processing(seg_data,features,U_close)
    if len(test_data) == 0 and len(labels_neg) == len(seg_data):
        print('都是-1')
        labels = test_data
    else:
        labels = model.predict(test_data)
    # 标签生成
    predict_labels = label_reset(labels, seg_data, seq_pos, labels_neg, k, mean_seg, U_close)
    return predict_labels


# 每分钟定时任务计算实时机时
def test_by_kmeans(imei):
    # 加载前90分钟的电流数据
    data = select_current_by_time(imei,90)
    if not data:
        logger.info(f'[machineTime_test] {imei} test数据为空')
        return
    # 从数据中获取设备类型和电流数据
    deviceType = data[0]['deviceType']
    currentData = data[0]['dataList']
    # # 计算存储今日机时
    calculate_machine_time(imei,currentData,deviceType)


# 机时计算并存储
def calculate_machine_time(imei,data,deviceType):
    # 从数据中提取出需要进行计算的数值，并存储在test_data列表
    test_data = [float(item['value']) for item in data]
    # print(test_data)
    # 加载kmeans模型
    loaded_file = load_model_file(imei)
    # 没有模型就跳过
    if loaded_file == None:
        logger.info(f'[machineTime_test] {imei} kmeans模型表里没有模型')
        update_present_model(imei,1,0)
        return
    loaded_model, ignore_length, real_k = loaded_file
    # 对test_data进行测试，得到每个数据点的标签
    labels = kmeans_test(test_data,loaded_model)
    # 机时标签合并
    result = compress_and_modify_states(labels,ignore_length,real_k)
    # draw(test_data,result)
    # # 机时存储 将修改后的机时结果和原始数据的时间信息一起存储起来。
    modified_list = [{'time': item['time'], 'label': result[i]} for i, item in enumerate(data)]
    add_machine_time(imei,modified_list,deviceType)

# 根据数据计算计时
def calculate_machine_time_kmeans_bydata(data, model_info, real_k, ignore_length):
    # 从数据中提取出需要进行计算的数值，并存储在test_data列表
    test_data = [float(item['value']) for item in data]
    loaded_model = model_info
    # 对test_data进行测试，得到每个数据点的标签
    labels = kmeans_test(test_data, loaded_model)
    # 机时标签合并
    result = compress_and_modify_states(labels, ignore_length, real_k)
    # 机时存储 将修改后的机时结果和原始数据的时间信息一起存储起来。
    modified_list = [{'time': item['time'], 'label': int(result[i])} for i, item in enumerate(data)]
    return modified_list



if __name__ == '__main__':
    test_by_kmeans('869858033744179')

