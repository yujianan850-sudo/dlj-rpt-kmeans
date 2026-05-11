import numpy as np
import ruptures as rpt
import matplotlib.pyplot as plt

# 以-1为界分割数组
def divide_by_negative(data,base_idx):
    result = []
    child_arr = []
    negative_arr = []
    # 遍历数据
    for i,e in enumerate(data):
        # 如果不为-1
        if e != -1:
            # 元素加入子序列
            child_arr.append(e)
            # -1子序列不为空，加入结果数组
            if len(negative_arr) != 0:
                result.append((negative_arr,base_idx+i))
                negative_arr = []
        else:
            negative_arr.append(e)
            if len(child_arr) != 0:
                result.append((child_arr,base_idx+i))
                child_arr = []
    if len(child_arr) != 0:
        result.append((child_arr, base_idx+len(child_arr)+i))
    if len(negative_arr) != 0:
        result.append((negative_arr, base_idx+len(negative_arr)+i))
    return result

# 按length分割序列
def split_sequence(seq, length):
    result = []
    for i in range(0, len(seq), length):
        sub_seq = seq[i:i+length]
        result.append((sub_seq, i//length))  # 标记子序列便于重组
    return result

# 拐点检测
def detect_change_point(seg_seq,pen):
    algo = rpt.Binseg(model="rbf").fit(seg_seq)
    result = algo.predict(pen=pen)
    # 打印拐点测结果
    # print("Detected change points:", result)
    return result

# 分割组成子序列

def draw(X,point):
    print(X,point)
    # 绘制时间序列数据和拐点
    plt.plot(X, color='blue', label='Time Series')
    for cp in point:
        plt.axvline(x=cp, color='red', linestyle='--')
    # plt.title(position)
    plt.legend()
    plt.show()

# 根据分割点生成子序列
def generate_subsequences(arr,point_list):
    seg_arr = []
    start = 0
    for point in point_list:
        if start == point:
            continue
        seg = arr[start:point]
        start = point
        seg_arr.append(seg)
    return seg_arr

# 生成分割后的子序列数组
def generate_seglist(data,length,pen):
    # 分割成1440长度的
    sequence_list = split_sequence(data, length)
    # 存储突变点
    point_list = []
    # 遍历找突变点
    for seg in sequence_list:
        # 以-1分割数据
        first_seq_data = divide_by_negative(seg[0],seg[1]*length)
        for i,e in enumerate(first_seq_data):
            # 按照-1分割，子序列只有1个元素，直接把位置加入，跳过本次循环
            if len(e[0]) == 1:
                point_list.append(e[1])
                continue
            # 寻找突变点
            change_point = detect_change_point(np.array(e[0]),pen)
            # print(change_point,e[0])
            # draw(e[0],change_point)
            base_point =  seg[1]*length if (i == 0) else first_seq_data[i-1][1]
            for i in range(len(change_point)):
                real_change_point = change_point[i] + base_point
                # 突变点存入point_list
                point_list.append(real_change_point)
    # 生成子序列（不等长）
    seg_list = generate_subsequences(data,point_list)
    # draw(data, point_list)
    return seg_list





