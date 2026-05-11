from datetime import datetime
from fastapi import HTTPException

from calculate_model.get_time import get_timestamp_of_previous_n_days
from calculate_model.test import calculate_machine_time_kmeans_bydata
from calculate_model.threshold import threshold_inicial_calculate, calculate_machine_time_bydata
from calculate_model.train import train_one
from database.mongo.get_data import getDeviceCurrentData, get_train_data, get_value_org_data, load_model_file, \
    load_threshold_model, load_model_by_imei, select_model_type


# 模型修改
# kmeans模型训练并重算机时
def model_update_kmeans(imei, data, start, end, props):
    # 训练不存
    model_info = train_one(imei, start, end, props)
    # print(model_info)
    real_k = props['real_k']
    ignore_length = props['ignore_length']
    # 根据数据计算机时
    modified_list = calculate_machine_time_kmeans_bydata(data, model_info, real_k, ignore_length)
    print("kmeans模型结果")
    # print(modified_list)
    return modified_list

# 阈值模型重算机时
def model_update_threshold(imei, data, props, ignore_length, real_k):
    # 根据数据计算机时
    modified_list = calculate_machine_time_bydata(imei, data, props, ignore_length, real_k)
    print("阈值模型结果")
    # print(modified_list)
    # print("----------")
    return modified_list


# 根据时间获取电流数据
def get_data_from_time(imei, startTime, endTime):
    # 获取当前时间时间戳（Unix 时间戳，以秒为单位）
    current_time = int(datetime.now().timestamp()) * 1000

    # 获取前 2 天零点的时间戳
    twodayago_time = get_timestamp_of_previous_n_days(2)

    # 判断日期在哪个范围
    # 历史
    if endTime <= twodayago_time:
        print("历史电流")
        finalData = get_data_from_old(imei, startTime, endTime)
    # 未归档
    elif startTime >= twodayago_time:
        print("未归档电流")
        finalData = get_data_from_new(imei, startTime, endTime)
    else:
        print("all电流")
        finalData = get_data_from_oldandnew(imei, twodayago_time, startTime, endTime)
    return finalData




# 从历史表中获取电流数据
def get_data_from_old(imei, startTime, endTime):
    # dt = getDeviceCurrentData('device_current', imei, startTime, endTime)
    data = get_value_org_data(imei, startTime, endTime)
    # print(data,'data')
    # data = get_data_list(dt)
    # print(data)
    return data

# 从未归档表中获取电流数据
def get_data_from_new(imei, startTime, endTime):
    dt = getDeviceCurrentData('to_archived_current', imei, startTime, endTime)
    if dt:
        # dt = select_current_by_date(imei, startTime, endTime)
        data = get_data_list(dt)
        return data
    else:
        err = {
            'status':400,
            'message':'test data is null'
        }
        return err

# 从两个表中获取电流数据
def get_data_from_oldandnew(imei, twodayago_time, startTime, endTime):
    olddata = get_data_from_old(imei, startTime, twodayago_time)
    newdata = get_data_from_new(imei, twodayago_time, endTime)
    data = olddata + newdata
    # print(olddata)
    # print(newdata)
    # print(data)
    return data


# 得到需要的电流数据列表样式
def get_data_list(dt):

    print("整理后的list")
    values_and_times = []  # 用于存储提取的'value'和'time'部分的值

    for entry in dt:
        # 检查当前字典中是否包含'dataList'键
        if 'dataList' in entry:
            # 获取'dataList'键对应的值
            dataList = entry['dataList']
            # 检查'dataList'值是否为字典，并且是否包含'value'和'time'键
            if isinstance(dataList, dict) and 'value' in dataList and 'time' in dataList:
                # 创建包含'value'和'time'的字典，并将其添加到列表中
                value_time_dict = {'value': dataList['value'], 'time': dataList['time']}
                values_and_times.append(value_time_dict)
    return values_and_times

# 根据imei获取模型数据
def get_model_info_by_imei(imei):
    model_type_res = select_model_type(imei)
    modelId = model_type_res['type']
    print(modelId)
    model_info = get_model_by_imei_and_modeltype(modelId,imei)
    model_info['modelId'] = modelId
    return model_info

# 根据imei和模型类型获取模型数据
def get_model_by_imei_and_modeltype(modelId, imei):
    if modelId == 0:
        document = load_model_by_imei("device_model",imei)
        if document:
            props = {
                'U_close': document['U_close'],
                'ignore_length': document['ignore_length'],
                'real_k': document['real_k']
            }
            data = {
                'imei': imei,
                'start': document['start'],
                'end': document['end'],
                'props': props
            }

        else:
            print("没有模型")
            raise HTTPException(status_code=400, detail="没有模型")
    elif modelId == 1:
        document = load_model_by_imei("threshold_model", imei)
        if document:
            props = document['model']
            data = {
                'imei': imei,
                'ignore_length': document['ignore_length'],
                'real_k': document['real_k'],
                'props': props
            }

        else:
            print("没有模型")
            raise HTTPException(status_code=400, detail="没有模型")
    else:
        raise HTTPException(status_code=400, detail="Invalid modelId. Supported values are 0 or 1.")
    print(data)
    return data

# imei = "866497066697849"
imei="866497066682841"
start=1708531200000
end=1708706560000
props={
    "U": 0.04,
    "length": 300,
    "ignore_length":30,
    "real_k":4,
    "pen_list": [20, 10, 5, 1, 0.1, 0.01, 0.001],
    "feature_list": ["mean", "max_value", "min_value"]
}
data = [{'value': '0.02', 'time': 1709096040000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096100000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096160000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096220000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096280000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096340000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096400000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096460000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096520000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096580000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096640000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096700000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096760000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096820000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096880000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709096940000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097000000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097060000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'},
        {'value': '0.02', 'time': 1709097120000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097180000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097240000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097300000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097360000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097420000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097480000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097540000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097600000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097660000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097720000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097780000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097840000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097900000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709097960000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.88', 'time': 1709098020000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.88', 'time': 1709098080000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.88', 'time': 1709098140000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'},
        {'value': '4.01', 'time': 1709098200000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098260000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098320000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.26', 'time': 1709098380000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.29', 'time': 1709098440000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.26', 'time': 1709098500000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.31', 'time': 1709098560000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.26', 'time': 1709098620000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.26', 'time': 1709098680000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098740000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098800000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098860000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098920000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709098980000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.87', 'time': 1709099040000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.86', 'time': 1709099100000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.87', 'time': 1709099160000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.86', 'time': 1709099220000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'},
        {'value': '3.86', 'time': 1709099280000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.86', 'time': 1709099340000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.87', 'time': 1709099400000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.88', 'time': 1709099460000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '3.89', 'time': 1709099520000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}, {'value': '0.02', 'time': 1709099580000, '_class': 'org.springblade.thingcom.data.entity.ToArchivedCurrent$Current'}]
imei1 = "866497066697849"
props1 = {
            'U_close': 0.03,
            'U_standby': 0.04,
            'U_run': 0.5
        }
ignore_length = 30
real_k = 4
if __name__ == "__main__":
    # model_update_threshold(imei1, data, props1, ignore_length, real_k)
    # model_update_kmeans(imei, data, start, end, props)
    #get_data_from_time(imei, 1707963200000, 1708963200000) # 历史
    #get_data_from_time(imei, 1708963200000, 1709188391000) # 未归档
    # final = get_data_from_time(imei1, 1707963200000, 1709188391000)  # all
    # model_update_threshold(imei1, final, props1, ignore_length, real_k)
    # model_update_kmeans(imei, final, start, end, props)

    # print(get_data_from_old('866497066682841', 1708566840000, 1708576200000))
    # get_model_by_imei(1, '866497066682841')
    get_model_info_by_imei('869858032088347')

