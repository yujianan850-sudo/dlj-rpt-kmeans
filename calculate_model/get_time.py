from datetime import datetime, timedelta, timezone

# 某个时间戳加分钟数,返回时间戳
def add_minutes_to_timestamp(timestamp, minutes):
    # 将毫秒转换为秒
    timestamp_seconds = timestamp / 1000.0
    # 将时间戳转换为 datetime 对象（时区设为UTC）
    dt_obj_utc = datetime.utcfromtimestamp(timestamp_seconds).replace(tzinfo=timezone.utc)
    # 将 UTC 时间转换为本地时间
    dt_obj_local = dt_obj_utc.astimezone(timezone(timedelta(hours=8)))
    # 添加指定分钟数
    new_dt_obj_local = dt_obj_local + timedelta(minutes=minutes)
    # 将新的本地 datetime 对象转换为时间戳
    new_timestamp = int(new_dt_obj_local.timestamp() * 1000)
    return new_timestamp

# 获取当前时间
def get_now():
    # 获取当前日期和时间
    current_datetime = datetime.now()
    # 清除微秒部分，将其精确到秒级别
    current_datetime = current_datetime - timedelta(microseconds=current_datetime.microsecond)
    # 将 datetime.datetime 对象转换为字符串
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    # 打印当前日期和时间
    # print("Current Date and Time:", formatted_datetime)
    return formatted_datetime

# 获取前n天的时间戳范围，不包括今天
def get_previous_seven_days_timestamps(n):
    # 获取当前日期和时间
    current_datetime = datetime.now()

    # 计算昨天的23:59:59时间
    yesterday_end_datetime = datetime.combine(current_datetime.date() - timedelta(days=1), datetime.max.time())

    # 计算前n的日期
    seven_days_ago_datetime = current_datetime - timedelta(days=n)

    # 构建七天前的0点时间
    seven_days_ago_start_datetime = datetime.combine(seven_days_ago_datetime.date(), datetime.min.time())

    # 获取今天之前的前七天0点时间戳和昨天的23:59:59时间戳（以毫秒为单位）
    seven_days_ago_start_timestamp = int(seven_days_ago_start_datetime.timestamp() ) * 1000
    yesterday_end_timestamp = int(yesterday_end_datetime.timestamp() ) * 1000

    return seven_days_ago_start_timestamp, yesterday_end_timestamp


# 获取前n分钟和当前时间的时间戳
def get_previous_n_minutes_timestamps(n):
    # 获取当前时间
    current_time = datetime.now()

    # 计算前n分钟的时间
    previous_n_minutes_time = current_time - timedelta(minutes=n)

    # 将时间转换为时间戳（Unix时间戳，以秒为单位）
    current_timestamp = int(current_time.timestamp()) * 1000
    previous_n_minutes_timestamp = int(previous_n_minutes_time.timestamp()) * 1000

    return previous_n_minutes_timestamp,current_timestamp


# 获取前n天零点的时间戳
def get_timestamp_of_previous_n_days(n):
    # 获取当前时间
    current_time = datetime.now()

    # 计算前 n 天的日期
    previous_n_days = current_time - timedelta(days=n)

    # 设置时间为零点
    previous_n_days_zero_time = datetime(previous_n_days.year, previous_n_days.month, previous_n_days.day, 0, 0, 0)

    # 将时间转换为时间戳（Unix 时间戳，以秒为单位）
    timestamp = int(previous_n_days_zero_time.timestamp()) * 1000

    return timestamp












