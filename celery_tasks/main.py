import os
from celery import Celery

# 加载项目配置
os.environ["DJANGO_SETTINGS_MODULE"] = "xiangmu_mall.settings.dev"
# 实例化selery对象
celery_app = Celery()
# 加载消息队列的配置
celery_app.config_from_object('celery_tasks.config')

# 自动识别任务
celery_app.autodiscover_tasks([
    'celery_tasks.sms',
    'celery_tasks.email',
    'celery_tasks.detail',
    ])

