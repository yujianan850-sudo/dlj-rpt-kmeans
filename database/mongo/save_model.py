from joblib import dump

from database.mongo.get_data import connection
import time
import pymongo
from calculate_model.process_data import convert_numpy_int
from calculate_model.get_time import get_now

def save_human_adjuge_info(imei,ignore_length,real_k):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["device_model"]
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect["device_model"]
        update_time = get_now()
        # 要插入的多个字段
        data_to_insert = {
            "ignore_length": ignore_length,     # 合并的长度
            "real_k": real_k,        # 真实类别
            "update_time": update_time
        }

        data_to_insert = convert_numpy_int(data_to_insert)
        # 查找是否已经存在相同imei的文档
        # 存储，没有插入，有就覆盖
        collection.update_one({"imei": imei}, {'$set': data_to_insert}, upsert=True)
        print('存储了kmeans模型')
    else:
        print('数据库连接错误')

# 存储训练出来的kmeans模型
def save_kmeans_model(imei,model_file,start,end, ignore_length,real_k, update_time):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["device_model"]
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect["device_model"]
        # 要插入的多个字段
        data_to_insert = {
            "imei": imei,
            "start": start,
            "end": end,
            "ignore_length": ignore_length,  # 合并的长度
            "real_k": real_k,  # 真实类别
            "update_time": update_time
        }

        # 合并模型信息
        # data_to_insert = convert_numpy_int(data_to_insert)
        data_to_insert.update(model_file)
        # 查找是否已经存在相同imei的文档
        # 存储，没有插入，有就覆盖
        collection.update_one({"imei": imei}, {"$set": data_to_insert}, upsert=True)
        print('存储了kmeans模型')
    else:
        print('数据库连接错误')


# 模型批量存储
def save_batch_models(documents):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["device_model"]
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect["device_model"]
        # 遍历文档列表，准备用于 update_many 的操作
        bulk_operations = []
        for doc in documents:
            doc['ignore_length'] = 0
            doc['real_k'] = 4
            filter_criteria = {"imei": doc["imei"]}
            update_operation = {"$set": doc}
            bulk_operations.append(pymongo.UpdateOne(filter_criteria, update_operation, upsert=True))
        # 执行 update_many 操作
        result = collection.bulk_write(bulk_operations)
        # 打印插入或更新操作的结果
        print(f"插入了 {result.upserted_count} 条新文档，更新了 {result.modified_count} 条已存在文档。")
    else:
        print('数据库连接错误')


# 存储阈值模型到数据库
def save_threshold_model(imei,props,ignore_length,real_k):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect['threshold_model']
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect['threshold_model']

        update_time = get_now()
        # 要插入的多个字段
        data_to_insert = {
            "imei": imei,
            "model": props,
            'ignore_length':ignore_length,
            'real_k':real_k,
            "update_time": update_time
        }

        data_to_insert = convert_numpy_int(data_to_insert)

        # 存储，没有插入，有就覆盖
        collection.update_one({"imei": imei}, {"$set": data_to_insert}, upsert=True)
        print('存储了阈值模型')
    else:
        print('数据库连接错误')

# 仪器当前使用的模型表更新
def update_present_model(imei,type,human_adjuge):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect['present_model']
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect['present_model']
        update_time = get_now()
        # 要插入的多个字段
        data_to_insert = {
            "imei": imei,
            "type": type,
            "human_adjuge":human_adjuge,
            "update_time": update_time
        }

        data_to_insert = convert_numpy_int(data_to_insert)

        # 存储，没有插入，有就覆盖
        collection.update_one({"imei": imei}, {"$set": data_to_insert}, upsert=True)
        print('更新了仪器模型表')
    else:
        print('数据库连接错误')


def update_present_model_batch(imeiList):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect['device_model']
        except pymongo.errors.AutoReconnect as e:
            print(f"连接断开，错误信息: {e}")
            time.sleep(5)  # 等待一段时间
            # 重新尝试数据库操作
            collection = connect['device_model']
        update_time = get_now()
        # 遍历文档列表，准备用于 update_many 的操作
        bulk_operations = []
        for imei in imeiList:
            # 要插入的多个字段
            doc = {
                "ignore_length": 0,  # 合并的长度
                "real_k": 4,  # 真实类别
                "update_time": update_time
            }
            filter_criteria = {"imei": imei}
            update_operation = {"$set": doc}
            bulk_operations.append(pymongo.UpdateOne(filter_criteria, update_operation, upsert=True))
        # 执行 update_many 操作
        result = collection.bulk_write(bulk_operations)
        # 打印插入或更新操作的结果
        print(f"插入了 {result.upserted_count} 条新文档，更新了 {result.modified_count} 条已存在文档。")
    else:
        print('数据库连接错误')


if __name__ == '__main__':
    save_human_adjuge_info("864823041516154",30,3)

