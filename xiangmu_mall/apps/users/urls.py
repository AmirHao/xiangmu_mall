from django.conf.urls import url
from . import views

urlpatterns = [
    # 注册用户
    url(r'^register/$',views.RegisterView.as_view()),
    # 检查用户名是否重复
    url(r'^usernames/(?P<username>[0-9a-zA-Z]{5,20})/count/$',views.UserCheckView.as_view()),
    # 检查手机号是否重复
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$',views.PhoneCheckView.as_view()),
    # 登录
    url(r'^login/$',views.LoginView.as_view()),
    # 退出
    url(r'^logout/$',views.LogoutView.as_view()),
    # 用户中心
    url(r'^info/$',views.UserAuthView.as_view()),
    # 添加邮箱
    url(r'^emails/$',views.EmailView.as_view()),
    # 激活邮箱
    url(r'^emails/verification/$',views.EmailActiveView.as_view()),
    # 收货地址
    url(r'^addresses/$',views.AddressView.as_view()),
    # 增加地址
    url(r'^addresses/create/$',views.AddAddressView.as_view()),
    # 修改地址
    url(r'^addresses/(?P<address_id>\d+)/$',views.AddressUpdateView.as_view()),
    # 设置默认地址
    url(r'^addresses/(?P<address_id>\d+)/default/$',views.DefaultAddressView.as_view()),
    # 设置标题
    url(r'^addresses/(?P<address_id>\d+)/title/$',views.TitleView.as_view()),
    # 修改密码
    url(r'^password/$',views.ChangePwd.as_view()),
]
