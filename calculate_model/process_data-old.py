import numpy as np
# import pywt
from scipy.stats import entropy,skew,kurtosis,mode
from calculate_model.get_time import add_minutes_to_timestamp

# 特征值计算------------------------------------------------------------------
def rms(arr):
    rms = np.sqrt(np.mean(np.square(arr)))
    return rms

# def xiaobo(arr):
#     coeffs, _ = pywt.cwt(arr, scales=np.arange(1, 128), wavelet='cmor')
#     xiaobo_features = np.abs(coeffs).mean(axis=1)  # Use mean of coefficients as features
#     return xiaobo_features

def ar_coefficients(arr):
    ar_coefficients = np.polyfit(range(len(arr)), arr, 2)
    return ar_coefficients

def fourier_descriptors(arr):
    fourier_descriptors = np.fft.fft(arr).real
    return fourier_descriptors

def short_term_zero_crossing_rate(arr):
    return np.sum(np.abs(np.diff(np.sign(arr)))) / 2

def short_term_energy(arr):
    arr = np.array(arr)
    return np.sum(arr ** 2)

# 众数
def arr_mode(arr):
    res =  mode(arr)
    return res.mode

# 获取序列特征值数组，根据选取的feature_list
def get_features(arr,feature_list):
    feature_functions = {
        'mean': np.mean,
        'var': np.var,
        'skew': skew,
        'kurtosis':kurtosis,
        'max_value':np.max,
        'min_value':np.min,
        'peak_to_peak':np.ptp,
        'median_value':np.median,
        'rms':rms,
        # 'xiaobo':xiaobo,
        'ar':ar_coefficients,
        'fourier':fourier_descriptors,
        'entropy':entropy,
        'short_term_zero_crossing_rate':short_term_zero_crossing_rate,
        'short_term_energy':short_term_energy,
        'mode':arr_mode
    }

    features = []
    for f in feature_list:
        result = feature_functions[f](arr)
        # 如果特征是数组，就把值加进来
        if isinstance(result, np.ndarray):
            features.extend(result)
        # 特征返回的是值，直接加进来
        else:
            features.append(result)
    return np.array(features)

# 预处理，生成训练数据----------------------------------------------------------------
def sequence_processing(data,feature_list,U_close):
    # seq_length = [len(seq) for seq in data]  # 计算每个子序列的长度
    # max_length = max(seq_length)  # 计算最大长度

    # 除去-1的序列
    padded_seqs = []
    # padded_train = []
    # -1序列的位置
    labels_neg_and_closed = []
    # 存放除去-1的序列位置和均值
    pos =[]

    # 计算每个序列的均值并填充序列
    for i,seq in enumerate(data):
        mean_val = ''
        if len(seq) != 0:
            mean_val = np.mean(seq)  # 计算序的均值
        # 均值小于0的
        if mean_val < 0:
            labels_neg_and_closed.append((i,0))
        elif mean_val < U_close:
            labels_neg_and_closed.append((i,1))
        else:
            # 特征值
            features = get_features(seq,feature_list)
            padded_seqs.append(features)
            pos.append(i)
    # 转换为 np.array([[],[],[]]) 格式
    result = np.array(padded_seqs)
    return result,labels_neg_and_closed,pos

# 后处理-----------------------------------------------------------------------------------------
# 重新标签，生成离线0，关机1，运行2，工作3
def label_reset(labels,seg_data,seq_pos,labels_neg,k,mean_seg,threshold_u):
    labels = np.array(labels)
    mean_indices = np.argsort(mean_seg)
    new_labels = labels.copy()
    # 分成2类
    if k == 2:
        # 最小的均值  小于 关机阈值，标签设为 0
        if mean_seg[mean_indices[0]] <= threshold_u:
            new_labels[labels == mean_indices[0]] = 1           # 关机
            new_labels[labels == mean_indices[1]] = 3           # 工作
        else:
            new_labels[labels == mean_indices[0]] = 2           # 待机
            new_labels[labels == mean_indices[1]] = 3           # 工作
    elif k == 3:
        # 最小的均值  小于 关机阈值，标签设为 0
        if mean_seg[mean_indices[0]] <= threshold_u:
            new_labels[labels == mean_indices[0]] = 1           # 关机
            new_labels[labels == mean_indices[1]] = 2           # 待机
            new_labels[labels == mean_indices[2]] = 3           # 工作
        else:
            new_labels[labels == mean_indices[0]] = 2           # 待机
            new_labels[labels == mean_indices[1]] = 3           # 工作
            new_labels[labels == mean_indices[2]] = 3           # 工作
    # 带位置的标签
    labels_with_pos = list(zip(seq_pos,new_labels))
    # 所有的子序列标签（包括-1）
    all_labels = labels_neg + labels_with_pos
    sorted_all_labels = sorted(all_labels, key=lambda x: x[0])
    # 生成标签序列
    labels_seq = generate_label_list(seg_data,sorted_all_labels)
    return labels_seq


# 按照时间窗合并机时
def compress_and_modify_states(input_list, ignore_length, k):
    compressed_list = []
    current_state = None
    count = 0

    for value in input_list:
        if current_state is None:
            current_state = value
            count = 1
        elif current_state == value:
            count += 1
        else:
            # 滤除离线的0状态
            if count < 30:
                if compressed_list and compressed_list[-1][0] in [1,2,3] and current_state == 0:
                    current_state = compressed_list[-1][0]
            # 人工要求合并状态
            if count < ignore_length:
                if compressed_list and compressed_list[-1][0] in [2,3] and current_state == 1:
                    current_state = compressed_list[-1][0]
                elif compressed_list and compressed_list[-1][0] == 3 and current_state == 2:
                    current_state = compressed_list[-1][0]
            if (k == 2 and current_state != 0) or (k == 3 and current_state in [2, 3]):
                current_state = 3
            compressed_list.append((current_state, count))
            current_state = value
            count = 1

    if count < 30:
        if compressed_list and compressed_list[-1][0] in [1,2,3] and current_state == 0:
            current_state = compressed_list[-1][0]
    # 处理最后一个数据
    if count < ignore_length:
        if compressed_list and compressed_list[-1][0] in [2, 3] and current_state == 1:
            current_state = compressed_list[-1][0]
        elif compressed_list and compressed_list[-1][0] == 3 and current_state == 2:
            current_state = compressed_list[-1][0]
    if (k == 2 and current_state != 0) or (k == 3 and current_state in [2, 3]):
        current_state = 3

    compressed_list.append((current_state, count))
    result_list = [item[0] for item in compressed_list for _ in range(item[1])]
    return result_list


# 后处理生成标签序列  和原序列等长
def generate_label_list(seg_data,labels):
    # 标签 list
    label_list = []
    n = 0
    for i, sequence in enumerate(seg_data):
        label_list.extend([labels[i][1]] * len(sequence))
        n += len(sequence)
    return label_list

# int类型转换
def convert_numpy_int(obj):
    """递归将 numpy.int32 或 numpy.int64 转换为 Python 内置整数类型"""
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_int(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_int(value) for key, value in obj.items()}
    else:
        return obj


def compress_data(data_list):
    if not data_list:
        return []

    # 初始化压缩后的列表
    compressed_list = []

    # 遍历数据列表
    for i in range(len(data_list)):
        # 如果是第一个元素或者当前元素的标签与前一个元素的标签不同
        if i == 0 or data_list[i]['label'] != data_list[i - 1]['label']:
            # 将当前元素添加到压缩列表中
            compressed_list.append({
                'time': data_list[i]['time'],
                'label': data_list[i]['label'],
                'minutes': 1  # 初始时间跨度为1
            })
        else:
            # 如果当前元素与前一个元素标签相同，更新压缩列表中最后一个元素的时间跨度
            compressed_list[-1]['minutes'] += 1

    # 返回压缩后的列表
    return compressed_list


if __name__ == "__main__":
    arr = [2,2,2,2,2,2,2,2,2,2,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,2,2,2,2,2,2,2,2,2,2]
    res = compress_and_modify_states(arr,0,4)
    print(res)


