from django.conf.urls import url
from . import views

urlpatterns = [
    # 结算
    url(r'^orders/settlement/$',views.OrderView.as_view()),
    # 保存订单
    url(r'^orders/commit/$',views.SaveOrderView.as_view()),
    # 提交成功
    url(r'^orders/success/$',views.SuccessOrderView.as_view()),
    # 全部订单
    url(r'^orders/info/(?P<page_num>\d+)/$',views.MyOrderView.as_view()),
    # 商品评价
    url(r'^orders/comment/$',views.CommentView.as_view()),
    # 详情显示评价
    url(r'^comment/(?P<sku_id>\d+)/$',views.DetailCommentView.as_view()),
]
