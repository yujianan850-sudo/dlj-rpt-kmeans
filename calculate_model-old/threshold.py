from database.mongo.get_data import load_threshold_model
from database.mongo.save_model import save_threshold_model
from database.mongo.usage_table import select_current_by_time,add_machine_time
from log.log import logger
from calculate_model.process_data import compress_and_modify_states

# 计算并存储今日机时
def test_by_threshold(imei):
    # 加载前90分钟的电流数据
    data = select_current_by_time(imei,90)
    if not data:
        logger.info(f'[machineTime_test] {imei} test数据为空')
        return
    deviceType = data[0]['deviceType']
    currentData = data[0]['dataList']
    # 计算存储今日机时
    calculate_machine_time(imei, currentData,deviceType)


# 计算并存储今日机时
def calculate_machine_time(imei,data,deviceType):
    test_data = [float(item['value']) for item in data]
    # 从数据库中读取模型
    model = load_threshold_model(imei)
    # 如果数据库中没有
    if model == None:
        logger.info(f'[machineTime_test] {imei} threshold模型表里没有模型')
        # 默认的阈值
        props = {
            'U_close': 0.03,
            'U_standby': 0.04,
            'U_run': 0.5
        }
        ignore_length = 0
        real_k = 4
        # 存储阈值模型
        save_threshold_model(imei,props,ignore_length,real_k)
    props, ignore_length, real_k = model
    # 计算机时
    labels = threshold_inicial_calculate(test_data,props)
    # 机时标签合并
    result = compress_and_modify_states(labels,ignore_length,real_k)
    # 机时存储
    modified_list = [{'time': item['time'], 'label': result[i]} for i, item in enumerate(data)]
    add_machine_time(imei,modified_list,deviceType)

# 阈值法计算机时
def threshold_inicial_calculate(data,props):
    U_close = props['U_close']
    U_standby = props['U_standby']
    U_run = props['U_run']
    labels = []
    for current in data:
        if current == -1:
            labels.append(0)
        elif current <= U_close:
            labels.append(1)
        elif current >= U_standby and current <= U_run:
            labels.append(2)
        else:
            labels.append(3)
    return labels

# 根据数据计算机时
def calculate_machine_time_bydata(imei, data, props, ignore_length, real_k):
    test_data = [float(item['value']) for item in data]
    # 计算机时
    labels = threshold_inicial_calculate(test_data,props)
    # 机时标签合并
    result = compress_and_modify_states(labels,ignore_length,real_k)
    modified_list = [{'time': item['time'], 'label': result[i]} for i, item in enumerate(data)]
    return modified_list


if __name__ == '__main__':
   # test_by_threshold('864823041515230')
   test_by_threshold('866497066697849')
