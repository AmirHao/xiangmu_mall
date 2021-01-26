from django.conf.urls import url
from .views import VerifyCodeView,SmsCodeView

urlpatterns = [
    url(r'^image_codes/(?P<uuid>[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/$',VerifyCodeView.as_view()),
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$',SmsCodeView.as_view()),
]
