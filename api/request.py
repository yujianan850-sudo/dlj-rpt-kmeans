from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from calculate_model.model_modification import model_update_kmeans, model_update_threshold, get_data_from_time,get_model_info_by_imei
from calculate_model.machine_time_retest import calculate_machine_time_by_data, machine_time_retest, \
    batch_machine_time_retest, mul_thread_methods_retest
from calculate_model.train import train_and_save_one, train_one_adjust_save
from calculate_model.train_history import processing_data
from database.mongo.save_model import update_present_model, save_threshold_model
from database.mysql.query_status_regular import query_all_imeis
from log.log import logger
import json

from pydantic import BaseModel

class Item(BaseModel):
    s:dict

# 服务端配置
app = FastAPI(raise_server_exceptions=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中根据需要进行调整
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# 重新训练的接口（单个）
'''
训练rpt-kmeans模型并重新计算机时

传参为json格式的
{
    "imei":"864823041515297",
    "start":1701619200000,
    "end":1702224000000,
    "props":{
        "U":0.04,
        "length":300,
        "pen_list":[20,10,5,1,0.1,0.01,0.001],
        "feature_list":["mean","max_value","min_value"]
    }
}
'''
@app.post("/rpt_kmeans_model")
def rpt_kmeans_model(data: dict):
    try:
        imei = data.get('imei')
        start = data.get('start')
        end = data.get('end')
        props = data.get('props')

        # 调用 train_and_save_one 函数
        logger.info(f'[request_model_train]{imei}调用接口重新训练模型')
        model_info = train_and_save_one(imei, start, end, props)
        features = {
            'k':model_info['k'],
            'mean_seg':model_info['mean_seg'],
            'pen':model_info['pen'],
        }
        # 更新仪器模型表，imei，0为kmeans模型，1为人为调整
        update_present_model(imei,0,1)
        # 返回成功
        # return JSONResponse(content={'status': 'success', 'features': features})
        raise HTTPException(status_code=200, detail={'status':'success','features':features})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=200, detail={'status':'failed','realError':e})

'''
模型改成阈值法并重新计算所有机时
{
    "imei":"864823041515297",
    "props":{
        "U_close":0.03,
        "U_standby":0.07,
        "U_run":0.5
    }
}
'''

@app.post("/retest_all_data_by_threshold/")
def run_function(s:Item):
    try:
        # imei = data.get('imei')
        # props = data.get('props')

        # 更新仪器模型表，imei，1为阈值模型，1为人为调整
        # update_present_model(imei,1,1)
        # 返回成功
        return {'status': 'success','imei':s}
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=500, detail={'status':'failed','realError':str(e)})


'''
传参为json格式的
{   "modelId":0,
    "imei":"866497066682841",
    "startTime":1707963200000,
    "endTime": 1709188391000,
    "start":1708531200000,
    "end":1708706560000,
    "props":{
        "U": 0.04,
        "length": 300,
        "ignore_length":30,
        "real_k":4,
        "pen_list": [20, 10, 5, 1, 0.1, 0.01, 0.001],
        "feature_list": ["mean", "max_value", "min_value"]
    }
}

{
    "modelId":1,
    "imei":"866497066697849",
    "startTime":1707963200000,
    "endTime": 1709188391000,
    "ignore_length": 30,
    "real_k": 4,
    "props":{
                "U_close": 0.03,
                "U_standby": 0.04,
                "U_run": 0.5
            }
}
'''
# 修改模型后根据日期重新计算机时
@app.post("/python/update_machine_time")
def update_machine_time(params):
    try:
        # 解析JSON数据
        data = json.loads(params)
        print(data)
        modelId = data['modelId']
        imei = data['imei']
        props = data['props']
        startTime = data['startTime']
        endTime = data['endTime']
        valueData = get_data_from_time(imei, startTime, endTime)

        if type(valueData) != list:
            raise HTTPException(status_code=500, detail={'status':'failed','realError':'test data is null'})
        if modelId == 0:
            # 使用 model_update_kmeans 函数
            start = data["start"]
            end = data["end"]
            modified_list = model_update_kmeans(imei, valueData, start, end, props)
            # modified_list = json.loads(json.dumps(modified_list))
        elif modelId == 1:
            # 使用 model_update_threshold 函数
            ignore_length = data["ignore_length"]
            real_k = data["real_k"]
            modified_list = model_update_threshold(imei, valueData, props, ignore_length, real_k)
        else:
            raise HTTPException(status_code=400, detail="Invalid modelId. Supported values are 0 or 1.")
        # print(len(valueData))
        # print(len(modified_list))
        # 提取 valueData 中的值
        values = [float(item['value']) for item in valueData]
        times = [datetime.utcfromtimestamp(item['time'] / 1000) for item in valueData]
        # 提取 modified_list 中的标签
        labels = [item['label'] for item in modified_list]
        # 画图
        # drawbytime(times, values, labels)

        # 返回成功
        return {'label_list': modified_list, 'value_list': valueData}
    except HTTPException as http_exception:
        # 如果已经是HTTPException，则直接重新抛出
        raise http_exception
    except Exception as e:
        print(e)
        # 记录错误并返回 HTTP 500 错误
        raise HTTPException(status_code=500, detail={'msg':str(e)})

'''
传参为json格式的
{
    "modelId":0,
    "imei":"866497066682841",
    "start":1708531200000,
    "end":1708706560000,
    "props":{
        "U": 0.04,
        "length": 300,
        "ignore_length":30,
        "real_k":4,
        "pen_list": [20, 10, 5, 1, 0.1, 0.01, 0.001],
        "feature_list": ["mean", "max_value", "min_value"]
    }
 }
 {
    "modelId":1,
    "imei":"866497066697849",
    "ignore_length": 30,
    "real_k": 4,
    "props":{
                "U_close": 0.03,
                "U_standby": 0.04,
                "U_run": 0.5
            }
}
'''

# 保存模型接口
@app.post("/python/save_model")
def save_model(params):
    try:
        # 解析JSON数据
        data = json.loads(params)
        modelId = data['modelId']
        imei = data['imei']
        props = data['props']
        print(data)
        if imei == "":
            raise HTTPException(status_code=400, detail={'msg':"Imei Error."})
        if modelId == 0 :
            start = data["start"]
            end = data["end"]
            # 调用 train_and_save_one 函数
            logger.info(f'[request_model_train]{imei}调用接口重新训练模型')
            train_one_adjust_save(imei, start, end, props)
            update_present_model(imei, 0, 1)
        elif modelId == 1:
            ignore_length = data["ignore_length"]
            real_k = data["real_k"]
            # 保存阈值模型
            save_threshold_model(imei, props, ignore_length, real_k)
            # 更新仪器模型表，imei，1为阈值模型，1为人为调整
            update_present_model(imei, 1, 1)
        else:
            raise HTTPException(status_code=400, detail="Invalid modelId. Supported values are 0 or 1.")
        # 返回成功
        return HTTPException(status_code=200, detail={'status':'success'})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 400 错误
        raise HTTPException(status_code=400, detail={'msg':str(e)})


'''
{
    "imei":"866497066696833"
}
'''
# 查询模型信息
@app.post("/python/query_model_info")
def query_model_information(params):
    try:
        # 解析JSON数据
        data = json.loads(params)
        imei = data["imei"]
        # 在当前模型表里查找当前模型类型
        modelinfo = get_model_info_by_imei(imei)
        return {'modelInfo': modelinfo}
        # return JSONResponse(content={'status':'success','data':{'modelInfo': modelinfo}})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=400, detail={'msg':str(e)})

# 通过电流计算机时接口
'''
{
    "imei":"866497066696833",
    "current_data":[
        {"time":1711728000000,"value":-1},
        {"time":1711728001000,"value":0},
        {"time":1711728002000,"value":0},
        {"time":1711728003000,"value":0},
        {"time":1711728004000,"value":0},
        {"time":1711728005000,"value":2.3},
        {"time":1711728006000,"value":2}
    ]
}
'''

@app.post("/calculate_machine_time_by_current")
def calculate_machine_time_by_current(data: dict):
    try:
        print(data)
        imei = data['imei']
        current_data = data['current_data']
        # 通过电流计算机时
        modified_list = calculate_machine_time_by_data(imei, current_data)
        # return JSONResponse(content={'status':'success','data':{'label_list': modified_list}})
        raise HTTPException(status_code=200, detail={'status': 'success', 'data':{'label_list': modified_list}})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=200, detail={'status':'failed','realError':str(e)})

# 单台仪器机时重算并存储到数据库接口
'''
{
    "imei":"866497066696833",
    "start":1711728000000,
    "end":1711728006000
}
'''
@app.post("/python/retest_data_by_imei")
def retest_data_by_imei(params):
    try:
        # 解析JSON数据
        data = json.loads(params)
        imei = data['imei']
        start = data['start']
        end = data['end']
        print(data,'single')
        # 通过电流计算机时
        machine_time_retest(imei,start,end)
        # return JSONResponse(content={'status':'success'})
        return HTTPException(status_code=200, detail={'status': 'success'})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=400, detail={'msg':str(e)})

# 所有仪器机时重算并存储到数据库接口
'''
{
    "start":1711728000000,
    "end":1711728006000
}
'''
@app.post("/python/retest_all_data")
def retest_all_data(params):
    try:
        # 解析JSON数据
        data = json.loads(params)
        start = data['start']
        end = data['end']
        print(data,'all')
        batch_machine_time_retest(start,end)
        # return JSONResponse(content={'status':'success'})
        return HTTPException(status_code=200, detail={'status': 'success'})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=400, detail={'msg':str(e)})

'''
{   
    "imei":"863455069117515",
    "beginTime":1719504000000,
    "endTime": 1719590340000
}
'''
# 用于将aep拉取历史电流数据进行处理
@app.post("/process_data")
def process_data_api(request: dict):
    try:
        # 从请求中获取IMEI和时间段
        imei = request['imei']
        beginTime = request['beginTime']
        endTime = request['endTime']
        processing_data(imei, beginTime, endTime)
        return JSONResponse(content={'status': 'success', 'data': "数据处理完毕"})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=500, detail=str(e))


'''
{   
    "beginTime":1719504000000,
    "endTime": 1719590340000
}
'''
# 用于将全部aep拉取历史电流数据进行处理
@app.post("/process_all_data")
def process_all_data_api(request: dict):
    try:
        # 从请求中获取IMEI和时间段
        imeiList = query_all_imeis()
        beginTime = request['beginTime']
        endTime = request['endTime']
        mul_thread_methods_retest(imeiList, beginTime, endTime, processing_data, 50)
        # processing_data(imei, beginTime, endTime)
        return JSONResponse(content={'status': 'success', 'data': "数据处理完毕"})
    except Exception as e:
        logger.error(str(e))
        # 捕获异常并返回 HTTP 500 错误
        raise HTTPException(status_code=500, detail=str(e))

async def run_fastapi_app_async():
    uvicorn.run("api.request:app", host="0.0.0.0", port=5000, reload=True)

def run_fastapi_app():
    # 启动 FastAPI 应用
    asyncio.run(run_fastapi_app_async())


if __name__ == "__main__":
    run_fastapi_app()