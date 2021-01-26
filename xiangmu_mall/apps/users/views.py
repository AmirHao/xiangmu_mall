import re
from django import http
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,redirect
from django.views import View
from django_redis import get_redis_connection
import json
from Verification_code.constants import USER_COOKIE_EXPIRY
from celery_tasks.email.tasks import send_verify_email
from xiangmu_mall.apps.Verification_code.views import VerifyCodeView
from users.models import User
from xiangmu_mall.utils.response_code import RETCODE
from xiangmu_mall.utils import mall_signature
from .models import Address
from xiangmu_mall.utils.merge_cart import cart_cookie_to_redis


# 注册用户
class RegisterView(View):
    def get(self,request):
        return render(request,'register.html')

    def post(self,request):
        # 接受
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        phone = request.POST.get('phone')
        allow = request.POST.get('allow')
        msg_code = request.POST.get('msg_code')
        # 验证
        if not all([user_name,pwd,cpwd,phone,allow,msg_code]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',user_name):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        if not re.match(r'^[0-9a-zA-Z]{8,20}$',pwd):
            return http.HttpResponseForbidden('请输入8-20个字符的密码')
        if cpwd != pwd:
            return http.HttpResponseForbidden('两次输入的密码不一样')
        if not re.match(r'^1[3-9]\d{9}$',phone):
            return http.HttpResponseForbidden('请输入正确格式的手机号')
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选协议')
        # 验证是否已经存在
        if User.objects.filter(username=user_name).count() > 0:
            return http.HttpResponseForbidden('用户名已存在')
        if User.objects.filter(mobile=phone).count() > 0:
            return http.HttpResponseForbidden('手机号已存在')
        # 手机验证码判断
        redis_con = get_redis_connection('verify_code')
        sms_code_redis = redis_con.get('sms_'+phone)
        if sms_code_redis is None:
            return http.HttpResponseForbidden('无效的短信验证码')
        if msg_code != sms_code_redis.decode():
            return http.HttpResponseForbidden('输入的短信验证码不一致')
        redis_con.delete('sms_'+phone)
        # 处理
        # try:
            # 使用create_user直接将密码加密
        user = User.objects.create_user(username=user_name,password=pwd,mobile=phone)
            # 保持状态
            # request.session['user_id'] = user.id
        login(request,user)
        response = redirect('/')
        response.set_cookie('username',user.username,max_age=USER_COOKIE_EXPIRY)
        # 购物车迁移
        response = cart_cookie_to_redis(request,response)

        # except:
        #     return render(request,'register.html',{'register_errmsg':'注册失败'})
        # 响应
        return response
# 检查用户名是否重复
class UserCheckView(View):
    # 检查用户名是否重复
    def get(self,request,username):
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({"count" : count})
# 检查手机号是否重复
class PhoneCheckView(View):
    # 检查手机号是否重复
    def get(self,request,mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'count': count})
# 登录
class LoginView(View):
    # 提供登录界面
    def get(self,request):
        return render(request,'login.html')
    # 登录请求，表单
    def post(self,request):
        # 接受参数
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        remembered = request.POST.get('remembered')
        # 登录成功后要跳转的网址
        next_url = request.GET.get('next','/')
        # 验证
        if not all([username,pwd]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[0-9a-zA-Z]{5,20}$',username):
            return http.HttpResponseForbidden('请输入正确的用户名或者手机号')
        if not re.match(r'^[0-9a-zA-Z]{8,20}$',pwd):
            return http.HttpResponseForbidden('请输入正确格式的密码')
        # 处理
        user = authenticate(request,username = username,password = pwd)
        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})
        # 保持状态
        login(request,user)
        # 在cookie中写入登录的用户名
        response = redirect(next_url)
        response.set_cookie('username',user.username,max_age=USER_COOKIE_EXPIRY)
        # 保持状态周期
        if remembered == 'on':
            # None过期时间为两周
            request.session.set_expiry(None)
        else:
            # 会话退出过期
            request.session.set_expiry(0)
        # 响应
        response = cart_cookie_to_redis(request,response)
        return response
# 退出
class LogoutView(View):
    def get(self,request):
        logout(request)
        response = redirect('/')
        response.delete_cookie('username')
        return response
# 用户中心 继承了LoginRequiredMixin不用校验是否登陆
class UserAuthView(LoginRequiredMixin,View):
    def get(self,request):
        # 校验用户是否登录
        # if not request.user.is_authenticated():
        #     return redirect('/login/')
        content = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active,
        }
        return render(request,'user_center_info.html',content)
# 添加邮箱
class EmailView(LoginRequiredMixin,View):
    def put(self,request):
        # 接受
        email_dic = json.loads(request.body.decode())
        email = email_dic.get('email')
        # 验证
        if not email:
            return http.HttpResponseForbidden('缺少email参数')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')
        # 处理
        try:
            user = request.user
            user.email = email
            user.save()
            # 发送邮件分支
            token = mall_signature.dumps(user.id,300)
            EMAIL_VERIFY_url = settings.EMAIL_VERIFY_URL+'?token=%s' % token
            send_verify_email.delay(email,EMAIL_VERIFY_url)
        except:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
# 激活邮箱
class EmailActiveView(View):
    def get(self,request):
        # 接受
        id = request.GET.get('token')
        # 验证
        if not id :
            return http.HttpResponseForbidden('缺少必传参数')
        id = mall_signature.loads(id,300)
        if id is None:
            return http.HttpResponseForbidden('参数无效')
        # 处理
        try:
            user = User.objects.get(pk=id)
            user.email_active = True
            user.save()
        except:
            return http.HttpResponseForbidden('邮箱激活失败')
        # 响应
        return redirect('/info/')
# 收货地址
class AddressView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        address = Address.objects.filter(user=user,is_deleted=False)
        address_list = []
        for ads in address:
            # address_dic = {
            # 'id': ads.id,
            # 'receiver': ads.receiver,
            # 'province': ads.province.name,
            # 'province_id': ads.province_id,
            # 'city': ads.city.name,
            # 'city_id': ads.city_id,
            # 'district': ads.district.name,
            # 'district_id': ads.district_id,
            # 'place': ads.place,
            # 'mobile': ads.mobile,
            # 'tel': ads.tel,
            # 'email': ads.email
            # }
            address_list.append(Address.to_dict(ads,ads.mobile,ads.tel,ads.email))
        context = {
            'default_address_id' : user.default_address_id,
            'addresses' : address_list
        }
        return render(request,'user_center_site.html',context)
# 新增地址
class AddAddressView(LoginRequiredMixin,View):
    def post(self,request):
        '''实现新增地址逻辑'''
        if request.user.addresses.count() > 20:
            return http.JsonResponse({
                'code':RETCODE.THROTTLINGERR,
                'errmsg':'超过地址个数上限'
            })
        # 接受
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 响应
        if not all([receiver,province_id,city_id,district_id,place,mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        # 处理，保存信息
        try:
            address = Address.objects.create(
                user = request.user,
                title = receiver,
                receiver = receiver,
                province_id = province_id,
                city_id = city_id,
                district_id = district_id,
                place = place,
                mobile = mobile,
                tel = tel,
                email = email
            )
            if not request.user.default_address:
                request.user.default_address = address
                request.user.save()
        except:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})
        # 响应
        # address_dic = {
        #     'id': address.id,
        #     'receiver': address.receiver,
        #     'province': address.province.name,
        #     'province_id': address.province_id,
        #     'city': address.city.name,
        #     'city_id': address.city_id,
        #     'district': address.district.name,
        #     'district_id': address.district_id,
        #     'place': address.place,
        #     'mobile': mobile,
        #     'tel': tel,
        #     'email': email
        # }
        return http.JsonResponse({
            'code':RETCODE.OK,
            'errmsg':'OK',
            'address':Address.to_dict(address,mobile,tel,email)
        })
# 修改地址
class AddressUpdateView(LoginRequiredMixin,View):
    def put(self,request,address_id):
        user = request.user
        """修改地址"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')
        # 校验参数
        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
                # 判断地址是否存在,并更新地址信息
        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新地址失败'})
        # 构造响应数据
        address = Address.objects.get(id=address_id)
        # address_dict = {
        #     "id": address.id,
        #     "title": address.title,
        #     "receiver": address.receiver,
        #     "province": address.province.name,
        #     "province_id": address.province.id,
        #     "city": address.city.name,
        #     "city_id": address.city.id,
        #     "district": address.district.name,
        #     "district_id": address.district.id,
        #     "place": address.place,
        #     "mobile": address.mobile,
        #     "tel": address.tel,
        #     "email": address.email
        # }
        # 响应更新地址结果
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': '更新地址成功',
            'address': Address.to_dict(address,mobile,tel,email)
        })
    def delete(self,request,address_id):
        try:
            ads = Address.objects.get(id=address_id)
        except:
            return http.JsonResponse({
            'code':RETCODE.PARAMERR,
            'errmsg':'删除地址失败'
        })
        ads.is_deleted = True
        ads.save()
        return http.JsonResponse({
            'code':RETCODE.OK,
            'errmsg':'删除地址成功'
        })
# 设置默认地址
class DefaultAddressView(LoginRequiredMixin,View):
    def put(self,request,address_id):
        # 接受
        user = request.user
        # 验证
        if not address_id:
            return http.HttpResponseForbidden('参数无效')
        # 处理
        user.default_address_id = address_id
        user.save()
        # 响应
        return http.JsonResponse({
            'code':RETCODE.OK,
            'errmsg':'默认地址设置成功'
        })
# 设置标题
class TitleView(LoginRequiredMixin,View):
    def put(self,request,address_id):
        # 接受
        user = request.user
        new_title = json.loads(request.body.decode()).get('title')
        # 验证
        if not address_id:
            return http.HttpResponseForbidden('参数无效')
        # 处理
        try:
            address = Address.objects.get(pk=address_id,user=user,is_deleted=False)
            address.title = new_title
            address.save()
        except:
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})
        # 响应
        return http.JsonResponse({
            'code':RETCODE.OK,
            'errmsg':'设置标题成功'
        })
# 修改密码
class ChangePwd(LoginRequiredMixin,View):
    def get(self,request):
        return render(request,'user_center_pass.html')
    def post(self,request):
        # 接受
        user = request.user
        old_pwd = request.POST.get('old_pwd')
        new_pwd = request.POST.get('new_pwd')
        new_cpwd = request.POST.get('new_cpwd')
        # 验证
        if not all([old_pwd,new_cpwd,new_pwd]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not request.user.check_password(old_pwd):
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_pwd):
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '新密码格式错误'})
        if new_pwd != new_cpwd:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '两次密码不一致'})
        # 处理
        user.set_password(new_pwd)
        user.save()
        # 重新登陆
        logout(request)
        response = render(request,'login.html')
        response.delete_cookie('username')
        # 响应
        return response



