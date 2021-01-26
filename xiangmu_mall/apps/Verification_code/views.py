import random
from venv import logger
from celery_tasks.sms.tasks import send_sms_code
from xiangmu_mall.libs.yuntongxun.sms import CCP
from django import http
from django.shortcuts import render
from django_redis import get_redis_connection
from django.views import View
from .constants import IMG_CODE_EXPIRY,SMS_CODE_EXPIRY,SMS_FLAG_EXPIRY
from xiangmu_mall.libs.captcha.captcha import captcha
from xiangmu_mall.utils.response_code import RETCODE

# 图片验证码接口
class VerifyCodeView(View):
    def get(self,request,uuid):
        # 接收
        # 验证
        # 处理
        text,code,img = captcha.generate_captcha()
        redis_con = get_redis_connection('verify_code')
        redis_con.setex(uuid,IMG_CODE_EXPIRY,code)
        # temp_code = redis_con.get(uuid).decode()
        # 响应
        return http.HttpResponse(img,content_type='image/png')

# 短信验证码接口
class SmsCodeView(View):
    def get(self,request,mobile):
        # 接收
        image_code_req = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')
        # 验证
        if not all([image_code_req,uuid]):
            return http.JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必传参数'})
        redis_con = get_redis_connection('verify_code')
        image_code_redis = redis_con.get(uuid)
        if image_code_redis is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码失效'})
        if image_code_req.upper() != image_code_redis.decode():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码不一致'})
        # 删除缓存的验证码
        # try:
        redis_con.delete(uuid)
        # except Exception as e:
        #     logger.error(e)
        # 短信验证码
        sms_code = '%06d' % random.randint(0,999999)
        if redis_con.get('sms_flag_'+mobile):
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '获取验证码太频繁了'})

        # 保存到redis中
        # redis_con.setex('sms_'+mobile,SMS_CODE_EXPIRY,sms_code)
        # redis_con.setex('sms_flag_'+mobile,SMS_FLAG_EXPIRY,1)
        # 管道传输
        redis_pipeline = redis_con.pipeline()
        redis_pipeline.setex('sms_'+mobile,SMS_CODE_EXPIRY,sms_code)
        redis_pipeline.setex('sms_flag_'+mobile,SMS_FLAG_EXPIRY,1)
        redis_pipeline.execute()
        # 处理
        # cpp = CCP()
        # cpp.send_template_sms(mobile,[sms_code,5],1)
        print(sms_code)
        # 使用celery异步处理
        datas = [sms_code,5]
        send_sms_code.delay(mobile,datas,1)
        # 响应
        return http.JsonResponse({
            'code':RETCODE.OK,
            'errmsg':'Pass'
        })
