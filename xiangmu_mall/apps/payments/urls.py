from django.conf.urls import url
from . import views

urlpatterns = [
    # 生成地址
    url(r'^payment/(?P<order_id>\d+)/$',views.AlipyUrlView.as_view()),
    # 处理订单
    url(r'^payment/status/$',views.AlipyStatusView.as_view()),
]
