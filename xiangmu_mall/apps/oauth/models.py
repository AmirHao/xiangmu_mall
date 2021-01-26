from django.db import models
from xiangmu_mall.utils.models import BaseMOdels
from users.models import User

# Create your models here.

class OauthQQUser(BaseMOdels):

    user = models.ForeignKey(User)
    openid = models.CharField(max_length=50)

    class Meta:
        db_table = 'tb_qq_user'

