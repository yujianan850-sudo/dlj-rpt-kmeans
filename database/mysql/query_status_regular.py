import pymysql
from calculate_model.get_time import get_now
from dbutils.pooled_db import PooledDB

# 连接mysql数据库
def get_db_connection():
    # 创建数据库连接池
    pool = PooledDB(
        creator=pymysql,
        maxconnections=50,  # 最大连接数
        blocking=True,
        # host='rm-2ze8kl2cepi7y986rco.mysql.rds.aliyuncs.com',   # 省科技厅大仪（外网）
        host='rm-2ze8kl2cepi7y986r.mysql.rds.aliyuncs.com',   # 省科技厅大仪（内网）/ 轨物内网
        # host = 'rm-2ze55er111a0m91fe5o.mysql.rds.aliyuncs.com',  # 天津大仪 (外网)
        # host = 'rm-2ze55er111a0m91fe.mysql.rds.aliyuncs.com',  # 天津大仪 (内网)
        # host = 'rm-2ze8kl2cepi7y986rco.mysql.rds.aliyuncs.com',  # 轨物
        user='root',
        password='galv@Mysql',  # 省科技厅大仪、轨物
        # password = 'tianjin@Mysql',  # 天津大仪
        database='galv_center'  # 数据库名
        # database = 'guiwu_galv_center'  # 轨物数据库
    )
    connection = pool.connection()
    return connection

# 查询有电流更新的imei
def query_update_imeis():
    connection = None
    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            # 具体SQL语句可根据自己实际需求编写
            sql = "SELECT imei FROM tb_update_record WHERE current_update_flag = 1"
            cursor.execute(sql)
            # 获取查询结果
            results = cursor.fetchall()

            # 打印拼接后的imei值
            if results:
                # 将结果放入数组
                imei_array = [result[0] for result in results]
                return imei_array
    except Exception as e:
        print(f"Error query_update_imeis: {e}")


# 查询所有仪器的imei
def query_all_imeis():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 具体SQL语句可根据自己实际需求编写
            sql = "SELECT imei FROM tb_update_record"
            cursor.execute(sql)
            # 获取查询结果
            results = cursor.fetchall()
            # 打印拼接后的imei值
            if results:
                # 将结果放入数组
                imei_array = [result[0] for result in results]
                return imei_array
    except Exception as e:
        print(f"Error inserting data: {e}")


# 对计算过机时的imei进行置位
def set_status(imei):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            now_time = get_now()
            sql = "UPDATE tb_update_record SET current_update_flag = 0,usage_update_flag = 1,current_customer_flag = 1 , usage_update_time = %s WHERE imei = %s"
            cursor.execute(sql, (now_time, imei))
        connection.commit()  # 确保提交事务
        print(imei,'修改成功')
    except Exception as e:
        print(f"Error updating data for {imei}: {type(e).__name__} - {e}")


if __name__ == "__main__":
    get_db_connection()
