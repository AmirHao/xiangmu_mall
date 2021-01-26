from django.conf.urls import url
from . import views

urlpatterns = [
    # 用户认证
    url(r'^areas/$', views.AreaView.as_view()),
]
