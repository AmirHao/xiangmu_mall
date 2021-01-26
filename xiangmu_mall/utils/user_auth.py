import re

from django.contrib.auth.backends import ModelBackend

from users.models import User


class UsernameMobileAuth(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # 手机号登录
            if re.match(r'^1[3-9]\d{9}$', username):
                user = User.objects.get(mobile=username)
            else:
                user = User.objects.get(username=username)
        except:
            return None
        else:
            # 检查密文密码
            if user.check_password(password):
                return user
