from django.db import models


class BaseMOdels(models.Model):

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        # 设置此对象模型，可用于集成，在生成数据库迁移的时候不会生成表
        abstract = True

