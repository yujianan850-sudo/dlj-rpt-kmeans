import time
import pymongo
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError, AutoReconnect

from calculate_model.draw import drawbytime
from database.mongo.get_data import connection
from calculate_model.process_data import convert_numpy_int
from database.mysql.query_status_regular import set_status

# 按照时间查询电流
from log.log import logger


def select_current_by_time(imei,n):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["to_archived_current"]
            operations = [
                {'$match': {'imei': imei}},  # 匹配指定的 imei
                {
                    '$project': {
                        '_id':0,
                        'dataList': {'$slice': ['$dataList', -n]},
                        'deviceType': 1
                    }
                } # 使用 $slice 获取最后60条数据，并保留 deviceType 字段
            ]
            cursor = list(collection.aggregate(operations))
            if len(cursor) == 0 or len(cursor[0]['dataList']) == 0:
                print('电流数据为空')
                return False
            return cursor
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")
            time.sleep(5)
            collection = connect["to_archived_current"]


# 按照日期选择查询电流
def select_current_by_date(imei, start_date, end_date):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["to_archived_current"]
            operations = [
                {'$match': {'imei': imei, 'date': {'$gte': start_date, '$lte': end_date}}},
                {
                    '$project': {
                        '_id': 0,
                        'dataList': 1,
                        'deviceType': 1
                    }
                }
            ]
            cursor = list(collection.aggregate(operations))
            if len(cursor) == 0 or len(cursor[0]['dataList']) == 0:
                print('电流数据为空')
                return False
            return cursor
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")
            time.sleep(5)
            collection = connect["to_archived_current"]

# 新增机时(暂存表)
def add_machine_time(imei,dataList,deviceType):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["to_archived_usage"]
            # 构造插入和更新的操作列表
            bulk_operations = []
            for data in dataList:
                filter_condition = {"imei": imei}
                # 新增
                add_operation = {
                    "$addToSet": {
                        "dataList": {
                            "label": data['label'],
                            "time": data['time']
                        }
                    },
                    "$set":{
                        "deviceType": deviceType
                    }
                }

                add_operation = convert_numpy_int(add_operation)
                # 删除
                delete_operation = {
                    "$pull": {
                        "dataList": {"time": {"$eq": data['time']}}
                    }
                }
                # 删除
                bulk_operations.append(pymongo.UpdateOne(filter=filter_condition, update=delete_operation, upsert=True))
                # 新增
                bulk_operations.append(pymongo.UpdateOne(filter=filter_condition, update=add_operation, upsert=True))
            try:
                result = collection.bulk_write(bulk_operations) #可能存在重复？ 可以优化
                # print(f"Inserted {result.upserted_count} documents and updated {result.modified_count} documents.")
                # 是否是后续重新计算机时，默认0 ，要置位
                set_status(imei)
            except pymongo.errors.BulkWriteError as bwe:
                print(f"Bulk write error: {bwe.details}")
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")
            time.sleep(5)
            collection = connect["to_archived_usage"]

# 更新机时(暂存表)
# 由于未归档数据是全部重算，因此直接对其进行全部更新
def add_machine_time_update(imei,dataList,deviceType,type = 0):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["to_archived_usage"]
            # collection = connect["to_archived_usage_copy1"]
            query = {"imei": imei}
            item = {"imei": imei, "dataList": dataList, "deviceType": deviceType}
            update = {"$set": item}
            # 执行更新操作,如果不存在则插入
            collection.update_many(query, update, upsert=True)
            print(imei+"Updated")
            # set_status(imei)
            # 构造插入和更新的操作列表
            bulk_operations = []
            # for data in dataList:
            #     # 构建查询和更新操作
            #     query = {"imei": data["imei"]}
            #     update = {"$set": item}
            #     # 执行更新操作,如果不存在则插入
            #     collection.update_many(query, update, upsert=True)
            #     filter_condition = {"imei": imei}
            #     # 新增
            #     add_operation = {
            #         "$addToSet": {
            #             "dataList": {
            #                 "label": data['label'],
            #                 "time": data['time']
            #             }
            #         },
            #         "$set":{
            #             "deviceType": deviceType
            #         }
            #     }
            #
            #     add_operation = convert_numpy_int(add_operation)
            #     # 删除
            #     delete_operation = {
            #         "$pull": {
            #             "dataList": {"time": {"$eq": data['time']}}
            #         }
            #     }
            #     # 删除
            #     bulk_operations.append(pymongo.UpdateOne(filter=filter_condition, update=delete_operation, upsert=True))
            #     # 新增
            #     bulk_operations.append(pymongo.UpdateOne(filter=filter_condition, update=add_operation, upsert=True))
            # try:
            #     result = collection.bulk_write(bulk_operations)
            #     # print(f"Inserted {result.upserted_count} documents and updated {result.modified_count} documents.")
            #     # 是否是后续重新计算机时，默认0 ，要置位
            #     if type == 0:
            #         # 置位
            #         set_status(imei)
            # except pymongo.errors.BulkWriteError as bwe:
            #     print(f"Bulk write error: {bwe.details}")
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")
            time.sleep(5)
            # collection = connect["to_archived_usage_copy1"]
            collection = connect["to_archived_usage"]

# 清理数据库数据
def delete_documents_matching_condition(timeTemp):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["to_archived_usage"]
            collection.update_many({}, {'$pull': {'dataList': {'time': {'$lt': timeTemp}}}})
        except Exception as e:
            print(f"Error deleting documents matching condition: {e}")


# 新增机时（历史库）
def add_machine_time_to_old(imei,dataList):
    client, connect = connection()
    if client is not None and connect is not None:
        try:
            collection = connect["device_usage"]
            # 构造插入和更新的操作列表
            # 遍历文档列表，准备用于 update_many 的操作
            bulk_operations = []
            for doc in dataList:
                doc['imei'] = imei
                filter_criteria = {"imei": imei,"date":doc['date']}
                update_operation = {"$set": doc}
                add_operation = convert_numpy_int(update_operation)
                bulk_operations.append(pymongo.UpdateOne(filter_criteria, add_operation, upsert=True))
            # 执行 update_many 操作
            result = collection.bulk_write(bulk_operations)
            # 打印插入或更新操作的结果
            print(f"插入了 {result.upserted_count} 条新文档，更新了 {result.modified_count} 条已存在文档。")
        except pymongo.errors.AutoReconnect as e:
            print(f"Connection lost, error: {e}")
            time.sleep(5)
            collection = connect["device_usage"]


if __name__ == '__main__':
    data_list = [
        {"value": 2, "time": 1706180280006},
        {"value": 3, "time": 1706180280007},
        {"value": 3, "time": 1706180280008},
        {"value": 3, "time": 1706180280009},
        {"value": 3, "time": 1706180280010},
        {"value": 3, "time": 1706180280011},
        {"value": 3, "time": 1706180280012},
    ]
    a = select_current_by_time("866497066682718", 60)
    #a = select_current_by_time("864823041521261",60)
    print(a)
    # add_machine_time("864823041515214",data_list)