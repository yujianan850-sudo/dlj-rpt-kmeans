from datetime import datetime, timedelta

import pymongo

from database.mongo.get_data import connection


'''
  该部分代码用于从aep平台获取的历史数据，进行数据处理
'''

# 输入imei，beginTime，endTime
def getHistoryData(imei):
    # 连接目标数据库
    mongo_client, connect = connection()
    # 获取指定数据库中表的内容
    data = get_imei_data(connect, 'to_archived_current_old', imei)
    return data

# 根据imei获取所有数据
def get_imei_data(connect, collection, imei):
    try:
        # 根据IMEI查询数据
        data = list(connect[collection].find({"imei": imei}).sort("date"))
        return data
    except pymongo.errors.ConnectionFailure as e:
        # 查询失败时的异常处理
        print(f"MongoDB Query Error: {e}")
        return None

# # 补全数据到测试数据库
# def move_current_data(data):
#     # 连接到MongoDB
#     client = pymongo.MongoClient("mongodb://guiwu:106ling106@39.105.25.84:27017/admin")
#     db = client["galv-center"]
#     # 需更新的集合表
#     # collection = db["device_current_copy1"]
#     collection = db["to_archived_current_test"]  # 电流
#     # 遍历处理后的数据，并使用 update_many() 方法来覆盖集合中的文档
#     for item in data:
#         # 构建查询和更新操作
#         query = {"imei": item["imei"]}
#         update = {"$set": item}
#         # 执行更新操作,如果不存在则插入
#         collection.update_many(query, update, upsert=True)

# 补全数据到测试数据库
def move_current_data(data):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            # 需更新的集合表
            collection = connect["to_archived_current_test"]
            # 遍历处理后的数据，并使用 update_many() 方法来覆盖集合中的文档
            for item in data:
                # 构建查询和更新操作
                query = {"imei": item["imei"]}
                update = {"$set": item}
                # 执行更新操作,如果不存在则插入
                collection.update_many(query, update, upsert=True)
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")

# # 压缩数据到测试数据库
# def save_current_data(data):
#     # 连接到MongoDB
#     client = pymongo.MongoClient("mongodb://guiwu:106ling106@39.105.25.84:27017/admin")
#     db = client["galv-center"]
#     # 需更新的集合表
#     collection = db["device_current_test"]  # 电流
#     # 遍历处理后的数据，并使用 update_many() 方法来覆盖集合中的文档
#     for item in data:
#         # 构建查询和更新操作
#         query = {"imei": item["imei"],"date": item["date"]}
#         update = {"$set": item}
#         # 执行更新操作,如果不存在则插入
#         collection.update_many(query, update, upsert=True)

# 压缩数据到测试数据库
def save_current_data(data):
    # 连接到MongoDB
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["device_current_test"]
            # 构造插入和更新的操作列表
            for item in data:
                # 构建查询和更新操作
                query = {"imei": item["imei"], "date": item["date"]}
                update = {"$set": item}
                # 执行更新操作,如果不存在则插入
                collection.update_many(query, update, upsert=True)
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")

# 补齐缺失数据
def fill_missing_data(data_list, begin_time, end_time):
    processed_list = []

    for item in data_list:
        imei = item['imei']
        device_type = item['deviceType']
        original_data_list = item['dataList']

        # 将开始时间和结束时间转换为datetime对象
        begin_dt = datetime.fromtimestamp(begin_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)

        # 创建一个从开始时间到结束时间的完整时间戳列表（每分钟一个）
        full_timestamps = []
        current_time = begin_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_time <= end_dt:
            full_timestamps.append(int(current_time.timestamp() * 1000))
            current_time += timedelta(minutes=1)

        # 读取原始数据并填充缺失的数据点
        filled_data = []
        for ts in full_timestamps:
            found = False
            for data in original_data_list:
                if data['time'] == ts:
                    filled_data.append(data)
                    found = True
                    break
            if not found:
                filled_data.append({'value': -1, 'time': ts})

        # 包含imei和deviceType的最终数据列表
        complete_data_list = {
            'imei': imei,
            'deviceType': device_type,
            'dataList': filled_data
        }

        processed_list.append(complete_data_list)

    return processed_list



def get_one_data(data, beginTime, endTime):
    # 转换为日期
    begin_date_time = datetime.fromtimestamp(beginTime / 1000)
    # 获取日期部分
    begin_date = begin_date_time.date()
    # 转换为日期
    end_date_time = datetime.fromtimestamp(endTime / 1000)
    # 获取日期部分
    end_date = end_date_time.date()
    # 计算日期差并转换为整数
    gap_days = (end_date - begin_date).days
    # 初始化结果列表
    result = []
    # 遍历每一天
    current_date = begin_date_time
    for _ in range(gap_days + 1):  # 包含开始和结束日期
        # 获取当前日期的毫秒时间戳
        current_date_timestamp = int(current_date.timestamp() * 1000)
        # 查找并收集属于当前日期的数据
        daily_data = {'imei': data[0]['imei'], 'deviceType': data[0]['deviceType'], 'date': current_date_timestamp,
                      'dataList': []}

        for entry in data:
            for item in entry['dataList']:
                item_date = datetime.fromtimestamp(item['time'] / 1000).date()
                if item_date == current_date.date():
                    daily_data['dataList'].append({'value': item['value'], 'time': item['time']})

        # 如果daily_data的dataList不为空，则添加到结果列表
        if daily_data['dataList']:
            result.append(daily_data)

        # 进入下一天
        current_date += timedelta(days=1)

    return result

# 压缩数据
def compress_consecutive_data(data_entry):
    compress_data = []
    for entry in data_entry:
        compress_one_data = {'imei': entry['imei'], 'deviceType': entry['deviceType'], 'date': entry['date'],
                         'dataList': []}
        compressed_data = []
        current_value = None
        current_minutes = 0
        start_time = None

        for item in entry['dataList']:
            time = item['time']
            value = item['value']

            if current_value is None:
                # 初始化第一个条目
                current_value = value
                start_time = time
                current_minutes += 1
            elif current_value == value:
                # 当前值与前一个值相同，累加分钟数
                current_minutes += 1
            else:
                # 值发生变化，将累积的信息添加到结果列表
                compressed_data.append({
                    'value': current_value,
                    'minutes': current_minutes,
                    'time': start_time,
                })
                # 重置为当前值和时间
                current_value = value
                start_time = time
                current_minutes = 1

        # 处理最后一个序列
        if current_value is not None:
            compressed_data.append({
                'value': current_value,
                'minutes': current_minutes,
                'time': start_time,
                # 注意：最后一个序列的end_time可能需要特殊处理，这里假设数据列表是连续的，最后一个时间就是结束
            })

        # 更新或创建新的dataEntry
        compress_one_data['dataList'] = compressed_data
        compress_data.append(compress_one_data)

    return compress_data

def processing_data(imei, beginTime, endTime):
    # 获取原始历史数据
    data_list = getHistoryData(imei)
    # 补齐数据
    getlist = fill_missing_data(data_list, beginTime, endTime)
    # 暂存补齐数据到表中
    move_current_data(getlist)
    # 按天划分
    one_day_result = get_one_data(getlist, beginTime, endTime)
    # 压缩数据
    compressed_data = compress_consecutive_data(one_day_result)
    print(compressed_data)
    # 保存数据到表中
    save_current_data(compressed_data)

if __name__ == '__main__':

    imei = "863455069117267"
    beginTime = 1719504000000
    endTime = 1719590340000
    processing_data(imei, beginTime, endTime)


