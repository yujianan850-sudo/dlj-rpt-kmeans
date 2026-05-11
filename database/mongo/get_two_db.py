import pymongo
from datetime import datetime, timedelta

import pymysql
from dbutils.pooled_db import PooledDB


from pymysql.cursors import DictCursor

# 此部分代码用于将浙江旧算法的历史数据迁移到新算法的数据库中
# 只需要运行代代码，就能实现迁移

# 连接mysql数据库
def get_mysql_connection():
    # 创建数据库连接池
    pool = PooledDB(
        creator=pymysql,
        maxconnections=50,  # 最大连接数
        blocking=True,
        host='rm-2ze8kl2cepi7y986rco.mysql.rds.aliyuncs.com',   # 省科技厅大仪（外网）
        user='root',
        password='galv@Mysql',  # 省科技厅大仪、轨物
        database='galv_center'  # 数据库名
    )
    connection = pool.connection()
    return connection

# 根据imei获取设备表中的设备类型
def get_device_type_from_sql(imei):
    # 获取数据库连接
    connection = get_mysql_connection()
    try:
        # 创建游标对象
        with connection.cursor(DictCursor) as cursor:
            # 执行SQL查询
            cursor.execute("SELECT device_type FROM tb_device WHERE imei = %s", (imei,))
            # 获取查询结果
            result = cursor.fetchone()
            return result['device_type'] if result else None
    except pymysql.Error as e:
        print(f"Error: {e}")
        return None
    finally:
        # 确保连接被归还到连接池
        connection.close()

# 获取mysql数据表中的所有imei和device_type
def get_all_imeis_and_types():
    # 获取数据库连接
    connection = get_mysql_connection()
    try:
        # 创建游标对象
        with connection.cursor(DictCursor) as cursor:
            # 执行SQL查询
            cursor.execute("SELECT DISTINCT imei, device_type FROM tb_device")
            # 获取所有行
            result = cursor.fetchall()
            # 创建一个字典来存储IMEI及其对应的device_type
            imei_types = {row['imei']: row['device_type'] for row in result}
            return imei_types
    except pymysql.Error as e:
        print(f"Error: {e}")
        return {}
    finally:
        # 确保连接被归还到连接池
        connection.close()


# 获取mysql数据表中的所有imei
def get_all_imeis():
    # 获取数据库连接
    connection = get_mysql_connection()
    try:
        # 创建游标对象
        with connection.cursor(DictCursor) as cursor:
            # 执行SQL查询
            cursor.execute("SELECT imei FROM tb_device")
            # 获取所有行
            result = cursor.fetchall()
            # 提取IMEI列表
            imeis = [row['imei'] for row in result]
            return imeis
    except pymysql.Error as e:
        print(f"Error: {e}")
        return []
    finally:
        # 确保连接被归还到连接池
        connection.close()



# 连接MongoDB数据库
def connection(uri, target_db):
    try:
        # 尝试连接 MongoDB
        mongo_client = pymongo.MongoClient(uri, maxPoolSize=30)
        connect = mongo_client[target_db]
        return mongo_client, connect
    except pymongo.errors.ConnectionFailure as e:
        # 连接失败时的异常处理
        print(f"MongoDB Connection Error: {e}")
        return None, None

# 根据imei获取所有数据
def get_imei_data(mongo_client, target_db, collection, imei):
    try:
        # 根据IMEI查询数据
        data = list(mongo_client[target_db][collection].find({"imei": imei}).sort("date"))
        return data
    except pymongo.errors.ConnectionFailure as e:
        # 查询失败时的异常处理
        print(f"MongoDB Query Error: {e}")
        return None

# 根据imei和开始时间到结束时间获取时间段内的数据，根据data字段
def get_date_range_data(mongo_client, target_db, collection, imei, start_date, end_date):
    try:
        count = mongo_client[target_db][collection].count_documents({"date": {"$gte": start_date, "$lte": end_date}, "imei": imei})
        # 根据日期范围查询数据
        query = {"date": {"$gte": start_date, "$lte": end_date}, "imei": imei}
        # data = mongo_client[target_db][collection].find(query)
        data = list(mongo_client[target_db][collection].find(query))
        return data, count
    except pymongo.errors.ConnectionFailure as e:
        # 查询失败时的异常处理
        print(f"MongoDB Query Error: {e}")
        return None, None

# 将数据进行补齐,处理
def add_data(data_list):

    for item in data_list:

        dataList = item['dataList']
        date_end_time = item['date'] + 24 * 60 * 60 * 1000  # 当天的最后一毫秒
        # 检查第一个数据元素的time是否与date相等
        if dataList and dataList[0]['time'] != item['date']:
            first_time_diff = (dataList[0]['time'] - item['date']) // (60 * 1000)
            dataList.insert(0, {
                'value': -1,
                'minutes': first_time_diff,
                'time': item['date']
            })

        # 检查最后一个数据元素是否需要补全
        if dataList:
            last_time = dataList[-1]['time'] + dataList[-1]['minutes'] * 60 * 1000
            if last_time < date_end_time:
                last_time_diff = (date_end_time - last_time) // (60 * 1000)
                dataList.append({
                    'value': -1,
                    'minutes': last_time_diff,
                    'time': last_time
                })

        # 处理中间的缺失数据
        i = 0
        while i < len(dataList) - 1:
            current = dataList[i]
            next = dataList[i + 1]
            newtime = current['time'] + current['minutes'] * 60 * 1000
            if newtime != next['time']:
                missing_minutes = (next['time'] - newtime) // (60 * 1000)
                dataList.insert(i + 1, {
                    'value': -1,
                    'minutes': missing_minutes,
                    'time': newtime
                })
            else:
                i += 1
        # 移除 _class 和 _id 字段
        item.pop('_class', None)
        item.pop('_id', None)
    return data_list

def fill_missing_days(data_list):
    # 初始化日期和IMEI
    prev_date = None
    prev_imei = None

    # 创建一个新列表来存储补全后的数据
    filled_data_list = []

    for item in data_list:
        # 将时间戳转换为日期对象
        current_date = datetime.fromtimestamp(item['date'] / 1000)

        # 如果IMEI或日期发生变化，检查是否需要补全缺失的天数
        if (prev_imei != item['imei'] or prev_date != current_date) and prev_date is not None:
            # 计算缺失的天数
            missing_days = (current_date - prev_date).days

            # 添加缺失的天数
            for missing_day in range(missing_days):
                new_date = prev_date + timedelta(days=missing_day + 1)
                filled_data_list.append({
                    'imei': item['imei'],
                    'date': int(new_date.timestamp() * 1000),
                    'deviceType': item['deviceType'],
                    'dataList': [{'value': -1, 'minutes': 1440, 'time': int(new_date.timestamp() * 1000)}]
                })

        # 更新日期和IMEI
        prev_date = current_date
        prev_imei = item['imei']

    # 返回补全后的数据列表
    return filled_data_list


# 将机时数据进行补齐,处理
def add_usage_data(data_list, imei_types):
    for item in data_list:
        dataList = item['dataList']
        date_end_time = item['date'] + 24 * 60 * 60 * 1000  # 当天的最后一毫秒

        # 检查第一个数据元素的time是否与date相等
        if dataList and dataList[0]['timestamp'] != item['date']:
            first_time_diff = (dataList[0]['timestamp'] - item['date']) // (60 * 1000)
            dataList.insert(0, {
                'label': -1,
                'minute': first_time_diff,
                'timestamp': item['date']
            })

        # 检查最后一个数据元素是否需要补全
        if dataList:
            last_time = dataList[-1]['timestamp'] + dataList[-1]['minute'] * 60 * 1000
            if last_time < date_end_time:
                last_time_diff = (date_end_time - last_time) // (60 * 1000)
                dataList.append({
                    'label': -1,
                    'minute': last_time_diff,
                    'timestamp': last_time
                })

        # 处理中间的缺失数据
        i = 0
        while i < len(dataList) - 1:
            current = dataList[i]
            next = dataList[i + 1]
            newtime = current['timestamp'] + current['minute'] * 60 * 1000
            if newtime != next['timestamp']:
                missing_minutes = (next['timestamp'] - newtime) // (60 * 1000)
                dataList.insert(i + 1, {
                    'label': -1,
                    'minute': missing_minutes,
                    'timestamp': newtime
                })
            else:
                i += 1
        # 移除 _class 和 _id 字段
        item.pop('_class', None)
        item.pop('_id', None)
        # 检查deviceType是否为-1，如果是，则查询数据库获取device_type
        if 'deviceType' in item and item['deviceType'] == -1 and 'imei' in item:
            device_type = imei_types.get(item['imei'])
            # device_type = get_device_type_from_sql(item['imei'])
            if device_type is not None:
                item['deviceType'] = device_type
        if isinstance(item['dataList'], list):
            for data in item['dataList']:
                # 将'minute'字段改名为'minutes'
                if 'minute' in data:
                    data['minutes'] = data.pop('minute')
                # 将'timestamp'字段改名为'time'
                if 'timestamp' in data:
                    data['time'] = data.pop('timestamp')
                # 确保'label'键存在且其值为整数，然后将其增加1
                if 'label' in data and isinstance(data['label'], int):
                    data['label'] += 1
    return data_list


# 更新电流到新的数据库
def move_current_data(data):
    # 连接到MongoDB
    client = pymongo.MongoClient("mongodb://guiwu:106ling106@101.201.74.179:27017/admin")
    db = client["galv-center"]
    # 需更新的集合表
    # collection = db["device_current_copy1"]
    collection = db["device_current"]  # 电流
    # 遍历处理后的数据，并使用 update_many() 方法来覆盖集合中的文档
    for item in data:
        # 构建查询和更新操作
        query = {"imei": item["imei"], "date": item["date"]}
        update = {"$set": item}
        # 执行更新操作,如果不存在则插入
        collection.update_many(query, update, upsert=True)


# 更新机时到新的数据库
def move_usage_data(data):
    # 连接到MongoDB
    client = pymongo.MongoClient("mongodb://guiwu:106ling106@101.201.74.179:27017/admin")
    db = client["galv-center"]
    # 需更新的集合表
    collection = db["device_usage"]  # 机时
    # collection = db["device_usage_copy1"]
    # 遍历处理后的数据，并使用 update_many() 方法来覆盖集合中的文档
    for item in data:
        if "imei" in item and "date" in item:
            # 构建查询和更新操作
            query = {"imei": item["imei"], "date": item["date"]}
            update = {"$set": item}
            # 执行更新操作,如果不存在则插入
            collection.update_many(query, update, upsert=True)
        else:
            print(f"Skipping item due to missing 'imei' or 'date': {item}")

# 获取所有imei列表
def get_imei(mongo_client, target_db, collection):
    try:
        # 查询数据库2中的所有IMEI
        imeis = mongo_client[target_db][collection].distinct("imei")
        return imeis
    except pymongo.errors.ConnectionFailure as e:
        # 查询失败时的异常处理
        print(f"MongoDB Query Error: {e}")
        return None

# 检测第一个元素与data是否一致
def check_first_element_time(data):
    mismatched_items = []
    for item in data:
        dataList = item['dataList']
        # if dataList and dataList[0]['time'] < item['date']:
        if dataList and dataList[0]['timestamp'] < item['date']:
            mismatched_items.append(item)
    return mismatched_items

# 检测最后一个元素与data是否一致
def check_end_element_time(data):
    mismatched_items = []
    for item in data:
        date_end_time = item['date'] + 24 * 60 * 60 * 1000  # 当天的最后一毫秒
        dataList = item['dataList']
        # last_time = dataList[-1]['time'] + dataList[-1]['minutes'] * 60 * 1000
        last_time = dataList[-1]['timestamp'] + dataList[-1]['minute'] * 60 * 1000 # 机时
        if last_time > date_end_time:
            mismatched_items.append(item)
    return mismatched_items

# 传输所有电流数据
def move_all_current_imei():
    imeis = get_imei(mongo_client2, target_db2, 'processedData')
    # count = 0  # 初始化计数器
    for item in imeis:
        # if count >= 2:  # 如果已经处理了3个IMEI，退出循环
        #     break
        data = get_imei_data(mongo_client2, target_db2, 'processedData', item)
        # 补全缺失天的数据
        move_current_data(fill_missing_days(data))
        # 补全离线数据
        move_current_data(add_data(data))
        # print("电流数据传输成功")
        # count += 1  # 处理完一个IMEI后，计数器加1
        if item is not None:
            print(f"处理IMEI: {item}")
    print("所有电流数据传输成功")

# 传输所有机时数据
def move_all_usage_imei():
    imeis = get_imei(mongo_client2, target_db2, 'deviceUsage')
    # 获取imei和对应类型
    imei_types = get_all_imeis_and_types()
    # count = 0  # 初始化计数器
    for item in imeis:
        # if count >= 3:  # 如果已经处理了3个IMEI，退出循环
        #     break
        data = get_imei_data(mongo_client2, target_db2, 'deviceUsage', item)
        move_usage_data(add_usage_data(data, imei_types))
        # count += 1  # 处理完一个IMEI后，计数器加1
        if item is not None:
            print(f"处理IMEI: {item}")
    print("所有机时数据传输成功")

'''
{
    imei = "866497066682536"
    # 转换日期字符串为时间戳
    start_date_str = "2024-6-28"
    end_date_str = "2024-6-30"
}
'''
# 传输指定imei的时间段电流数据
def move_some_current_imei(imei, start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").timestamp() * 1000
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").timestamp() * 1000
    data, count = get_date_range_data(mongo_client2, target_db2, 'processedData', imei, start_date, end_date)
    # 补全缺失天的数据
    move_current_data(fill_missing_days(data))
    # 补全离线数据
    move_current_data(add_data(data))

    print("所有电流数据传输成功")
if __name__ == '__main__':
    # imei = "869858033726341"
    # #
    # # imei = "869858033737108"
    # # imei = "869858033735433"
    # # imei = "869858033728529"
    # # 转换日期字符串为时间戳
    # start_date_str = "2021-3-01"
    # end_date_str = "2024-6-3"
    # start_date = datetime.strptime(start_date_str, "%Y-%m-%d").timestamp()*1000
    # end_date = datetime.strptime(end_date_str, "%Y-%m-%d").timestamp()*1000
    #
    # 第一个数据库连接 浙江新算法
    uri1 = f"mongodb://guiwu:106ling106@101.201.74.179:27017/admin"
    target_db1 = 'galv-center'
    mongo_client1, connect1 = connection(uri1, target_db1)

    # 第二个数据库连接 浙江旧算法
    uri2 = f"mongodb://root:106ling106@121.40.154.189:27017/admin"
    target_db2 = 'galv'
    mongo_client2, connect2 = connection(uri2, target_db2)

    # 获取时间范围内的列表进行处理
    # data, count = get_date_range_data(mongo_client2, target_db2, 'processedData', imei, start_date, end_date)

    # print(f"查询到 {count} 条数据：")
    # print(add_data(data))
    # move_data(add_data(data))
    # imeis = get_imei(mongo_client2, target_db2, 'processedData')
    # if imeis:
    #     print(f"数据库2中的所有IMEI：{imeis}")
    # else:
    #     print("无法获取数据库2中的IMEI。")

    # 根据imei判断数据是否有异常
    # data = get_imei_data(mongo_client2, target_db2, 'processedData', '869858033726341')
    # # print(data)
    # move_current_data(fill_missing_days(data))
    # move_current_data(add_data(data))
    # print("数据传输成功")
    # print("缺失开始数据")
    # miss_list = check_first_element_time(data)
    # print(miss_list)
    # print("结尾数据超标")
    # over_list = check_end_element_time(data)
    # print(over_list)

    # # 遍历所有imei进行处理
    # imeis = get_imei(mongo_client2, target_db2, 'deviceUsage')
    # for item in imeis:
    #     data = get_imei_data(mongo_client2, target_db2, 'deviceUsage', item)
    #     # move_data(add_data(data))
    #     print("缺失开始数据")
    #     miss_list = check_first_element_time(data)
    #     print(miss_list)
    #     print("结尾数据超标")
    #     over_list = check_end_element_time(data)
    #     print(over_list)

    #
    # # 机时数据传输
    # data = get_imei_data(mongo_client2, target_db2, 'deviceUsage', '869858033726341')
    # imei_types = get_all_imeis_and_types()
    # move_usage_data(add_usage_data(data, imei_types))
    # print("数据传输成功")

    # # 使用示例
    # imei_types = get_all_imeis_and_types()
    # print(imei_types)

    # 调用函数
    # move_all_current_imei()
    # print("电流已结束")
    # move_all_usage_imei()
    # print("机时已结束")

    # # 调用函数并打印IMEI列表
    # imeis = get_all_imeis()
    # print(imeis)
    # type = get_device_type_from_sql(869858033726341)
    # print(type)

    imei = "863455069120915"
    # 转换日期字符串为时间戳
    start_date_str = "2024-6-17"
    end_date_str = "2024-6-29"
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").timestamp()*1000
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").timestamp()*1000
    data, count = get_date_range_data(mongo_client2, target_db2, 'processedData', imei, start_date, end_date)
    print(data)
    # 补全缺失天的数据
    move_current_data(fill_missing_days(data))
    # 补全离线数据
    move_current_data(add_data(data))


