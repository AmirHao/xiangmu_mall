from django.conf.urls import url
from . import views

urlpatterns = [
    # QQ登陆网址
    url(r'^qq/login/$',views.QQUrlView.as_view()),
    # 获取openid
    url(r'^oauth_callback/$',views.QQAuthUserView.as_view()),
]
