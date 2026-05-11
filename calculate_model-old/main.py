from database.mysql.query_status_regular import query_all_imeis
from calculate_model.train import batch_train_by_imeilist
from calculate_model.get_time import get_now
from database.mysql.query_status_regular import query_all_imeis
from database.mongo.save_model import update_present_model_batch
from database.mongo.get_data import load_imeis_have_model,select_model_type


import time

if __name__ == '__main__':
    imeiList = query_all_imeis()
    print(imeiList)
    # imeiList = get_imeis_by_time_temp()
    # update_present_model_batch(imeiList)






