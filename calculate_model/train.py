import numpy as np
import pickle
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from database.mongo.save_model import save_batch_models, update_present_model, save_kmeans_model
from database.mongo.get_data import get_train_data,select_model_type
from calculate_model.process_data import sequence_processing,label_reset
from calculate_model.rpt import generate_seglist
from calculate_model.get_time import get_previous_seven_days_timestamps,get_now
from calculate_model.draw import draw

# 日志
from log.log import logger

# 判断训练数据的波动
def judge_wave(data,U_wave):
    # 提取第一列数据
    arr = data[:, 0]
    # 计算最大值和最小值
    max_value = np.max(arr)
    min_value = np.min(arr)

    # 计算差值并保留两位小数
    diff = round(max_value - min_value, 2)
    # print(diff,'----diff')

    # 波动差值小于波动阈值
    if diff < U_wave:
        return False


# 聚类
def cluster(X_train,k):
    kmeans = KMeans(n_clusters=k,n_init=10)
    labels = kmeans.fit_predict(X_train)
    cluster_centers_indices = []
    # 找到每个聚类中心在原始数据中的索引
    for i in range(k):
        indices = np.where(labels == i)[0][:1]
        cluster_centers_indices = np.concatenate((cluster_centers_indices, indices)).astype(int)
    return labels,cluster_centers_indices,kmeans


# 生成最佳k值模型，根据轮廓系数
def creat_model(seg_data,feature_list,U_close,U_wave):
    # 生成训练数据
    train_data,labels_neg,seq_pos = sequence_processing(seg_data,feature_list,U_close)
    # 样本数量太少，全都是-1、关机
    if len(train_data) <= 3:
        return False
    # 判断波动
    flag = judge_wave(train_data,U_wave)
    # 聚类聚不出来
    if flag == False:
        return False
    # 聚类
    labels,center_indices,model = cluster(train_data,2)
    # 聚类中心的均值
    mean_seg = [np.mean(seg_data[seq_pos[item]]) for item in center_indices]
    # 标签生成
    labels_seq = label_reset(labels,seg_data,seq_pos,labels_neg,2,mean_seg,U_close)
    ss_score = silhouette_score(train_data,labels)
    result = [2,ss_score,labels_seq,model,mean_seg]
    return result


# 生成不同pen的原始数据
def product_pen(data, length, pen_list):
    seg_data_list = []
    for pen in pen_list:
        # 生成不等长子序列
        seg_data = generate_seglist(data, length, pen)
        seg_data_list.append((pen,seg_data))
    return seg_data_list


def train(imei,start,end,props):
    U_close = props['U_close']  # 关机阈值
    U_wave = props['U_wave'] # 波动阈值
    # length = props['length']
    # pen_list = props['pen_list']
    # feature_list = props['feature_list']
    # 模型数值
    length = 300
    pen_list = [20, 10, 5, 1, 0.1, 0.01, 0.001]
    feature_list = ["mean", "max_value", "min_value"]

    best_score = -np.Inf
    best_result = []
    best_pen = ''
    # 获取训练数据
    or_data = get_train_data(imei, start, end)
    if or_data == False:
        return False
    # 分割
    try:
        seg_data_list = product_pen(or_data, length, pen_list)
    except:
        return False
    for seg_data in seg_data_list:
        pen = seg_data[0]
        model_result = creat_model(seg_data[1],feature_list,U_close,U_wave)
        if model_result == False:
            continue
        score = model_result[1]
        if score > best_score:
            best_score = score
            best_result = model_result
            best_pen = pen
    if len(best_result) == 0:
        return False
    # labels_seq = best_result[2]
    # print('最佳结果',best_result[0],best_score,best_pen)
    # labels_com = compress_and_modify_states(labels_seq,30,4)
    # draw(or_data,labels_com)
    # 创建包含模型和相关信息的字典
    model_info = {
        'k':2, # kmeans聚类类别数
        'kmeans_model': best_result[3], # kmeans模型
        'mean_seg':best_result[4], # 聚类中心均值
        'pen': best_pen, # 最佳分割精度
        'features': feature_list, # 选用的特征值
        'U_close':U_close,  # 关机阈值
        'U_wave':U_wave,  # 波动阈值
        'length':length, # 分割单位长度
    }
    return model_info

# 批量训练并存储
def train_and_save_batch(imei_list,start,end,props):
    models_infos = []
    reselect_data_imei_list = []
    for imei in imei_list:
        model_file = train(imei, start, end, props)
        if model_file == False:
            # logger.info(f'[model_train] {imei} 当前数据无法训练出聚类模型')
            print(imei,'重新选择训练数据')
            reselect_data_imei_list.append(imei)
            continue
        else:
            model_file['kmeans_model'] = pickle.dumps(model_file['kmeans_model'])
            print(imei,model_file)
        model_info = {
            'imei': imei,
            'start': start,
            'end': end,
            'update_time': get_now()
        }
        # 合并模型信息
        model_info.update(model_file)
        models_infos.append(model_info)
        document = select_model_type(imei)
        if document == None or (document['human_adjuge'] == 0 and document['type'] == 1):
            update_present_model(imei,0,0)
    if models_infos:
        save_batch_models(models_infos)
    return reselect_data_imei_list

# 单台训练并存储
def train_and_save_one(imei, start, end, props):
    print('start')
    model_info = train(imei, start, end, props)
    if model_info == False:
        logger.info(f'[request_model_train] {imei} 当前数据无法训练出聚类模型')
        print('重新选择训练数据')
        return False
    else:
        model_info['kmeans_model'] = pickle.dumps(model_info['kmeans_model'])
        print('model_info')
    update_time = get_now()
    save_kmeans_model(imei, model_info, start, end,0,4,update_time)
    print('over')
    return model_info

# 单台训练但不存储
def train_one(imei, start, end, props):
    print('start')
    # print(props,'-----props')
    model_info = train(imei, start, end, props)
    if model_info == False:
        logger.info(f'[request_model_train] {imei} 当前数据无法训练出聚类模型')
        print('重新选择训练数据')
        return False
    else:
        print('model_info')
    print('over')
    return model_info

# kmeams训练并保存
def train_one_adjust_save(imei, start, end, props):
    print('start')
    model_info = train(imei, start, end, props)
    if model_info == False:
        logger.info(f'[request_model_train] {imei} 当前数据无法训练出聚类模型')
        print('重新选择训练数据')
        return False
    else:
        model_info['kmeans_model'] = pickle.dumps(model_info['kmeans_model'])
        print('model_info')
    update_time = get_now()
    ignore_length = props['ignore_length']
    real_k = props['real_k']
    save_kmeans_model(imei, model_info, start, end, ignore_length, real_k, update_time)
    print('over')
    return model_info

# 批量按imeilist训练
'''
用于全部仪器模型训练和没有模型的仪器模型训练
imeiList 所有要训练的仪器的imei
batchSize 批量存储的batch
'''
def batch_train_by_imeilist(imeiList,batchSize=10):
    props = {
        'U_close': 0.05,  # 关机阈值
        'U_wave':0.1,  # 波动阈值
        'length': 300,
        'pen_list': [20, 10, 5, 1, 0.1, 0.01, 0.001],
        'feature_list': ['mean', 'max_value', 'min_value']
    }
    # 14天的数据作为训练数据
    start,end = get_previous_seven_days_timestamps(14)
    imei_batch = []
    re_train_list = []
    for imei in imeiList:
        # 10个批量训练并存储
        if len(imei_batch) == batchSize:
            re_train_batch_list = train_and_save_batch(imei_batch, start, end, props)
            re_train_list += re_train_batch_list
            re_train_batch_list = []
            imei_batch = []
        else:
            imei_batch.append(imei)
    if len(imei_batch) != 0:
        re_train_batch_list = train_and_save_batch(imei_batch, start, end, props)
        re_train_list += re_train_batch_list
        re_train_batch_list = []


#imei="864823041521733"
# start=1701360000000
# end=1702137600000
imei="869858033744179"
start=1708531200000
end=1708706560000
props={
    "U": 0.04,
    "length": 300,
    "ignore_length": 30,
    "real_k": 4,
    "pen_list": [20, 10, 5, 1, 0.1, 0.01, 0.001],
    "feature_list": ["mean", "max_value", "min_value"]
}

if __name__ == '__main__':
    # model_info = train_and_save_one(imei, start, end, props)
    model_info = train_one_adjust_save(imei, start, end, props)
    print(model_info)











