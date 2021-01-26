import re
from Verification_code.constants import USER_COOKIE_EXPIRY
from users.models import User
from django import http
from django.contrib.auth import login
from django.shortcuts import render,redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from xiangmu_mall.utils.merge_cart import cart_cookie_to_redis
from xiangmu_mall.utils.response_code import RETCODE
from .models import OauthQQUser
from xiangmu_mall.utils import mall_signature


# 获取qq授权地址
class QQUrlView(View):
    def get(self,request):
        # 获取QQ登陆授权地址
        next_url = request.GET.get('next','/')
        # 1.创建对象
        oauth = OAuthQQ(
            settings.QQ_CLIENT_ID,
            settings.QQ_CLIENT_SECRET,
            settings.QQ_REDIRECT_URI,
            next_url,
        )
        # 2.生成授权地址
        QQ_login_url = oauth.get_qq_url()
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg':'OK',
            'login_url':QQ_login_url
        })

# qq用户登录
class QQAuthUserView(View):
    def get(self,request):
        # 获取openid
        code = request.GET.get('code')
        next = request.GET.get('state')
        if not code:
            return http.HttpResponseForbidden('缺少code')
            # 1.创建对象
        oauth = OAuthQQ(
            settings.QQ_CLIENT_ID,
            settings.QQ_CLIENT_SECRET,
            settings.QQ_REDIRECT_URI,
        )
        try:
            # 获得openid
            token = oauth.get_access_token(code)
            openid = oauth.get_open_id(token)
            # 查询openid是否存在
            try:
                qq_user = OauthQQUser.objects.get(openid=openid)
            # 不存在，绑定
            except:
                openid = mall_signature.dumps(openid,300)
                content = {'token':openid}
                response = render(request,'oauth_callback.html',content)

                response = cart_cookie_to_redis(request, response)
                return response

            # 存在，状态保持，重定向
            else:
                login(request,qq_user.user)
                response = redirect(next,'/')
                response.set_cookie('username',qq_user.user.username,max_age=USER_COOKIE_EXPIRY)

                response = cart_cookie_to_redis(request, response)
                return response
        except:
            openid = 0

        return http.HttpResponse(openid)
    # 1144A4D00A7DB278D2CD4AD0E15309EA

    def post(self,request):
        # 接受
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('pwd')
        sms_code = request.POST.get('sms_code')
        token = request.POST.get('access_token')
        next = request.POST.get('next')
        # 验证
        if not all([mobile,pwd,sms_code,token]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return http.HttpResponseForbidden('请输入正确格式的手机号')
        if not re.match(r'^[0-9a-zA-Z]{8,20}$',pwd):
            return http.HttpResponseForbidden('请输入8-20个字符的密码')
        openid = mall_signature.loads(token,300)
        # print(token_dic)
        # openid = token_dic.get('openid',None)
        # 处理
        try:
            # 1.判断用户是否存在手机号
            user = User.objects.get(mobile=mobile)
            # 2.用户不存在
        except:
            # 2.1注册用户
            user = User.objects.create_user(username=mobile,mobile=mobile,password=pwd)
        else:
            print(user.check_password(pwd))
            # 3.有，判断密码是否正确 True/False
            if not user.check_password(pwd):
                content = {'token': token,'account_errmsg': '用户名或密码错误'}
                # 3.1密码错误，返回错误响应
                return render(request, 'oauth_callback.html',
                              content)
        # 3.2密码正确，绑定
        OauthQQUser.objects.create(openid=openid, user=user)
        # 状态保持，重定向
        login(request,user)
        response = redirect(next,'/')
        response.set_cookie('username', mobile, max_age=USER_COOKIE_EXPIRY)
        # 响应
        response = cart_cookie_to_redis(request,response)

        return response
