import pymongo
import pandas as pd
import pickle
import time
# 日志
from log.log import logger

# 连接mongodb数据库
def connection():
    # host = '101.201.74.179'         # 省科技厅新大仪（外网）
    host = '172.22.22.120'         # 省科技厅新大仪（内网）
    # host = '172.17.0.1'           # 省科技厅新大仪/天津大仪 内网
    # host = '39.105.25.84'   # 天津大仪（外网）
    # host = '59.110.49.15'   #轨物
    port = 27017
    user_name = 'guiwu'
    user_pwd = '106ling106'
    authentication_db = 'admin'  # 认证数据库
    target_db = 'galv-center'  # 实际目标数据库
    uri = f"mongodb://{user_name}:{user_pwd}@{host}:{port}/{authentication_db}"

    try:
        # 尝试连接 MongoDB
        mongo_client = pymongo.MongoClient(uri, maxPoolSize=30)
        connect = mongo_client[target_db]
        return mongo_client,connect
    except pymongo.errors.ConnectionFailure as e:
        # 连接失败时的异常处理
        print(f"MongoDB Connection Error: {e}")
        return None,None

# 获取设备电流数据
def getDeviceCurrentData(table_name, imei, start, end):
    client, connect = connection()
    if client is not None and connect is not None:
        operations = [
            # 将字段拆分成多条
            {'$unwind': '$dataList'},
            # 数据过滤
            {'$match': {'$and': [{"imei": imei}, {"dataList.time": {'$gte': start, '$lt': end}}]}},
            # 筛选字段
            {'$project': {'_id': 0,'imei': 1, "dataList": 1,"date":1,"deviceType":1}}
        ]
        return list(connect[table_name].aggregate(operations))

# 获取设备电流数据
def getTodayCurrentData(table_name, imei):
    client, connect = connection()

    if client is not None and connect is not None:
        operations = [
            # 将字段拆分成多条
            {'$unwind': '$dataList'},
            # 数据过滤
            {'$match': {'$and': [{"imei": imei}]}},
            # 筛选字段
            {'$project': {'_id': 0,'imei': 1, "dataList": 1,'date':1,"deviceType":1}}
        ]
        if table_name == 'device_current':
            operations = [
                # 数据过滤
                {'$match': {'$and': [{"imei": imei}]}},
                # 筛选字段
                {'$project': {'_id': 0, 'imei': 1, "dataList": 1, 'date': 1,"deviceType":1}}
            ]
        return list(connect[table_name].aggregate(operations))


# 处理数据把压缩的电流展开
def processed_org_data(data_list):
    processed_data = []
    for entry in data_list:
        value = float(entry['value'])
        minutes = entry['minutes']
        if minutes < 0:
            return False
        processed_data.extend([value] * minutes)
    return processed_data


# 获取历史中的原始数据
def get_org_data(data_list):
    processed_data = []
    for entry in data_list:
        value = float(entry['value'])
        time = entry['time']  # 假设每个条目中都有'time'字段，表示毫秒时间戳
        minutes = entry['minutes']
        if minutes < 0:
            return False

        # 根据minutes扩展时间戳
        for _ in range(minutes):
            processed_data.append({'value': value, 'time': time})
            time += 60000  # 增加一分钟的毫秒数
    return processed_data


# 得到训练数据，返回的是数组
def get_train_data(imei,start,end):
    dt = getDeviceCurrentData('device_current',imei,start,end)
    df_4 = pd.DataFrame(dt)
    if df_4.empty:
        logger.info(f'[model_train] {imei} 空数据')
    else:
        data = df_4['dataList']
        processed_data = processed_org_data(data)
        if processed_data:
            return processed_data
        else:
            logger.info(f'[model_train] {imei} 异常数据')
            return False

# 根据给定的IMEI号、起始时间和结束时间获取历史数据，将数据展开后返回数组
def get_value_org_data(imei,start,end):
    print(start,end,'-----time')
    dt = getDeviceCurrentData('device_current',imei,start,end)
    df_4 = pd.DataFrame(dt)
    if df_4.empty:
        logger.info(f'[model_train] {imei} 空数据')
    else:
        data = df_4['dataList']
        deviceType = df_4['deviceType'][0]
        processed_data = get_org_data(data)
        if processed_data:
            return processed_data,deviceType
        else:
            logger.info(f'[model_train] {imei} 异常数据')
            return False

# 根据imei获取所有电流
def get_all_current_data(imei):
    dt = getTodayCurrentData('device_current',imei)
    df_4 = pd.DataFrame(dt)
    if len(df_4) == 0:
        print(imei, '空数据')
        return False
    processed_data_list = []
    for i in range(len(df_4)):
        data = df_4['dataList'][i]
        date = df_4['date'][i]
        deviceType = df_4['deviceType'][i]
        processed_data = processed_org_data(data)
        processed_data_list.append((processed_data,date,deviceType))
    if processed_data_list:
        return processed_data_list
    else:
        print(imei, '异常数据')
        return False

# 根据imei获取所有电流（暂存表）
def get_all_current_data_new(imei):
    client, connect = connection()
    if client is not None and connect is not None:
        operations = [
            # 将字段拆分成多条
            {'$unwind': '$dataList'},
            # 数据过滤
            {'$match': {'$and': [{"imei": imei}]}},
            # 筛选字段
            {'$project': {'_id': 0,'imei': 1, "dataList": 1,"deviceType":1}}
        ]
        return list(connect['to_archived_current'].aggregate(operations))

# 根据imei获取时间区间内的电流（历史表）
def get_current_by_time(imei,startTime,endTime):
        client, connect = connection()
        if client is not None and connect is not None:
            operations = [
                # 数据过滤
                {'$match': {'$and': [{"imei": imei}, {"dataList.time": {'$gte': startTime, '$lt': endTime}}]}},
                # 筛选字段
                {'$project': {'_id': 0, 'imei': 1, "dataList": 1, "date": 1, "deviceType": 1}}
            ]
            dt = connect['device_current'].aggregate(operations)
            df_4 = pd.DataFrame(dt)
            processed_data_list = []
            if df_4.empty:
                logger.info(f'[model_train] {imei} 空数据')
                return False
            for i in range(len(df_4)):
                data = df_4['dataList'][i]
                date = df_4['date'][i]
                deviceType = df_4['deviceType'][i]
                processed_data = get_org_data(data)
                processed_data_list.append((processed_data, date, deviceType))
            if processed_data_list:
                return processed_data_list
            else:
                print(imei, '异常数据')
                return False



def load_model_by_imei(tableName,imei):
    client, connect = connection()
    if client is not None and connect is not None:
        query = {"imei": imei}
        return connect[tableName].find_one(query)


# 模型加载并解析
def load_model_file(imei):
    document = load_model_by_imei("device_model",imei)
    if document:
        props = {
            'U_close':document['U_close'],
            'U_wave': document['U_wave'],
            'kmeans_model':pickle.loads(document['kmeans_model']),
            'k':document['k'],
            'pen':document['pen'],
            'mean_seg':document['mean_seg'],
            'features':document['features'],
            'length':document['length']
        }
        ignore_length = document.get("ignore_length")
        real_k = document.get("real_k")
        return props, ignore_length, real_k
    else:
        print("没有模型")

# 加载阈值模型
def load_threshold_model(imei):
    document = load_model_by_imei("threshold_model",imei)
    if document:
        model = document.get("model")
        ignore_length = document.get("ignore_length")
        real_k = document.get("real_k")
        return model, ignore_length, real_k
    else:
        print("没有阈值模型")

def load_imeis_have_model():
    return query_imeis("device_model")

def query_imeis(tableName):
    client, connect = connection()
    if client is not None and connect is not None:
        operations = [
            # 筛选字段
            {'$project': {'_id': 0, 'imei': 1}}
        ]
        dt = connect[tableName].aggregate(operations)
        if dt:
            df_4 = pd.DataFrame(list(dt))
            if df_4.empty:
                return []
            else:
                return df_4['imei'].to_numpy()

# 获取仪器模型表中所有imei
def query_all_imeis_in_present_model():
    return query_imeis('present_model')

# 查询仪器的模型类型
def select_model_type(imei):
    document = load_model_by_imei("present_model",imei)
    if document:
        return document
    else:
        print("没有模型")

if __name__ == '__main__':
    # print(get_all_current_data('866497066689705'))
    # load_model_file('866497066697849')
    # get_train_data('866497066682841',1707963200000, 1708963200000)
    # print(get_value_org_data('864823041568056', 1709049600000, 1709135999000))
    # select_model_type(864823041516105)
    connection()








