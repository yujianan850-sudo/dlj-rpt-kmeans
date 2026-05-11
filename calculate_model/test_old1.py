from datetime import datetime

import numpy as np
# 日志
from matplotlib import pyplot as plt

from log.log import logger
from calculate_model.process_data import sequence_processing, label_reset, compress_and_modify_states, \
    sequence_processing_new, label_reset_new
from calculate_model.rpt import generate_seglist
from database.mongo.get_data import load_model_file
from database.mongo.usage_table import add_machine_time,select_current_by_time
from database.mongo.save_model import update_present_model
from calculate_model.draw import draw, drawlabelsbytime


# kmeans测试模型(wyy更新版)
def kmeans_test_new(data,loaded_file):
    length = loaded_file['length']
    # 赋值
    model = loaded_file['kmeans_model']
    U_close = loaded_file['U_close']
    pen = loaded_file['pen']
    features = loaded_file['features']
    k = loaded_file['k']
    mean_seg = loaded_file['mean_seg']
    # 预处理----分割
    # 尝试对数据进行分割，如果失败则将整个数据作为一个分割
    try:
        seg_data = generate_seglist(data, length, pen)
    except:
        seg_data = np.array([data])
    # 生成训练数据
    # 处理分割后的数据，提取特征，生成测试数据集和负标签序列
    # test_data,labels_neg,seq_pos = sequence_processing(seg_data,features,U_close)
    test_data,labels_neg,seq_pos,big_data,wave_data = sequence_processing_new(seg_data,features,U_close,0.04)

    # 如果测试数据为空且所有分割都被标记为负标签，则直接返回负标签
    if len(test_data) == 0:
        print('都是-1')
        labels = test_data
    else:
        # 使用K均值模型预测测试数据的标签
        labels = model.predict(test_data)
    # 标签生成
    # 根据预测标签和分割数据，重置标签以匹配原始数据结构
    predict_labels = label_reset_new(labels, seg_data, seq_pos, labels_neg, k, mean_seg, U_close,big_data,wave_data)
    return predict_labels


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
    # 尝试对数据进行分割，如果失败则将整个数据作为一个分割
    try:
        seg_data = generate_seglist(data, length, pen)
    except:
        seg_data = np.array([data])
    # 生成训练数据
    # 处理分割后的数据，提取特征，生成测试数据集和负标签序列
    test_data,labels_neg,seq_pos = sequence_processing(seg_data,features,U_close)
    # 如果测试数据为空且所有分割都被标记为负标签，则直接返回负标签
    if len(test_data) == 0 and len(labels_neg) == len(seg_data):
        print('都是-1')
        labels = test_data
    else:
        # 使用K均值模型预测测试数据的标签
        labels = model.predict(test_data)
    # 标签生成
    # 根据预测标签和分割数据，重置标签以匹配原始数据结构
    predict_labels = label_reset(labels, seg_data, seq_pos, labels_neg, k, mean_seg, U_close)
    return predict_labels

# 每分钟定时任务计算实时机时
def test_by_kmeans(imei):
    # 加载前90分钟的电流数据
    data = select_current_by_time(imei,120)
    if not data:
        logger.info(f'[machineTime_test] {imei} test数据为空')
        return
    # 从数据中获取设备类型和电流数据
    deviceType = data[0]['deviceType']
    currentData = data[0]['dataList']
    # # 计算存储今日机时
    calculate_machine_time(imei,currentData,deviceType)


# 机时计算并存储（实时计算）
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
    labels = kmeans_test_new(test_data,loaded_model)
    if ignore_length == 0:
        # 机时标签合并
        result = compress_and_modify_states(labels, 60, real_k)
    else:
        # 机时标签合并
        result = compress_and_modify_states(labels,ignore_length,real_k)
    # draw(test_data,result)
    # # 机时存储 将修改后的机时结果和原始数据的时间信息一起存储起来。
    modified_list = [{'time': item['time'], 'label': result[i]} for i, item in enumerate(data)]
    # 使用切片操作获取后90分钟的数据
    modified_list_90_minutes = modified_list[-90:]
    # show(modified_list_90_minutes)
    add_machine_time(imei,modified_list_90_minutes,deviceType)

# 根据数据计算计时（接口计算）
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

def show(modified_list_90_minutes):
    times = [item['time'] for item in modified_list_90_minutes]
    labels = [item['label'] for item in modified_list_90_minutes]
    draw(times, labels)

if __name__ == '__main__':
    test_by_kmeans('863455069119107')

