from venv import logger

from xiangmu_mall.libs.yuntongxun.sms import CCP
from celery_tasks.main import celery_app

# 1.需要加selef参数，代表本函数。2.路径的代替名字。3.重新尝试之间的时间间隔
# @celery_app.task(bind=True, name='ccp_send_sms_code', retry_backoff=3)
@celery_app.task()
def send_sms_code(to,datas,tempid):
    try:
        cpp = CCP()
        # cpp.send_template_sms(to,datas,tempid)
    except Exception as e:
        logger.error(e)
    #     raise self.retry(exc=e,max_retries=3)
    # if send_ret != 0:
    #     raise self.retry(exc=Exception('发送短信失败'),max_retries=3)
    print(datas[0])