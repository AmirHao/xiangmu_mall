from django.shortcuts import render
from django.views import View
from order.models import OrderInfo
from django import http
from xiangmu_mall.utils.response_code import RETCODE
from alipay import AliPay
from django.conf import settings
import os
from .models import Payment

# Create your views here.
# 生成支付地址
class AlipyUrlView(View):
    def get(self,request,order_id):
        # 查询订单对象
        try:
            order = OrderInfo.objects.get(pk=order_id)
        except:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'查询不到该订单'})
        # 创建支付宝对象
        alipay = AliPay(
            appid=settings.ALIPY_APP_ID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=open(os.path.join(settings.BASE_DIR,'apps/payments/alipy/app_private_key.pem')).read(),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=open(os.path.join(settings.BASE_DIR,'apps/payments/alipy/alipy_public_key.pem')).read(),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = settings.ALIPY_DEBUG  # 默认False
        )
        # 生成网站参数
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,    # 订单号
            total_amount=str(order.total_amount),  # 总金额
            subject='扣款环节',
            return_url=settings.ALIPAY_RETURN_URL,   # 回调地址
            # notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 拼接支付宝路径
        url = settings.ALIPAY_URL + order_string
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':"OK",'alipay_url':url})

# 处理订单
class AlipyStatusView(View):
    def get(self,request):
        # 提取参数
        param_dict = request.GET.dict()  # QueryDict转换成字典
        # 弹出sign
        sign = param_dict.pop('sign')
        alipay = AliPay(
            appid=settings.ALIPY_APP_ID,
            app_notify_url=None,  # 默认回调url
            app_private_key_string=open(
                os.path.join(settings.BASE_DIR, 'apps/payments/alipy/app_private_key.pem')).read(),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=open(
                os.path.join(settings.BASE_DIR, 'apps/payments/alipy/alipy_public_key.pem')).read(),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPY_DEBUG  # 默认False
        )
        res = alipay.verify(param_dict,sign,)
        order_id = param_dict.get('out_trade_no')
        trade_no = param_dict.get('trade_no')
        if res:
            # 支付成功
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_no
            )
            # 修改订单状态
            OrderInfo.objects.filter(pk=order_id).update(status=4)
            return render(request,'pay_success.html',{'order_id':order_id})
        else:
            # 支付失败
            return http.HttpResponse(res)
        pass

