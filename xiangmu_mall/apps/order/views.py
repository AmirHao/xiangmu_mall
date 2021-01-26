import time
from django.core.paginator import Paginator
from django import http
from django.shortcuts import render
from django.views import View
from users.models import Address
from goods.models import SKU
from django.contrib.auth.mixins import LoginRequiredMixin
from django_redis import get_redis_connection
import json
from xiangmu_mall.utils.response_code import RETCODE
from datetime import datetime
from .models import OrderInfo,OrderGoods
from django.db import transaction


# 展示订单
class OrderView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        # 展示收货地址
        address_list = Address.objects.filter(is_deleted=False,user_id=user.id)
        default_address_id = user.default_address_id
        # 查询购物车
        reids_cli = get_redis_connection('carts')
        cart_str = reids_cli.hgetall('user%s' %user.id)
        cart_dict = {int(sku_id):int(count) for sku_id,count in cart_str.items()}
        selected_str = reids_cli.smembers('selected%s' %user.id)
        selected_list = [int(sku_id) for sku_id in selected_str]
        # 查询库存商品
        skus = SKU.objects.filter(is_launched=True,pk__in=selected_list)
        sku_list = []
        total_count = 0 # 总数量
        total_price = 0 # 总金额
        freight = 10 # 运费
        sn = 0
        for sku in skus:
            total_amount = sku.price * cart_dict[sku.id] # 小计
            total_count += cart_dict[sku.id]
            total_price += total_amount
            sn += 1
            sku_list.append({
                'id':sn,
                'default_image':sku.default_image.url,
                'name':sku.name,
                'price':sku.price,
                'count':cart_dict[sku.id],
                'total_amount':total_amount
            })
        pay_price = total_price + freight # 实际付款
        context = {
            'address_list':address_list,
            'default_address_id':default_address_id,
            'sku_list':sku_list,
            'total_count':total_count,
            'total_price':total_price,
            'freight':freight,
            'pay_price':pay_price
        }
        return render(request,'place_order.html',context)
# 创建订单
class SaveOrderView(LoginRequiredMixin,View):
    def post(self,request):
        # 接受
        user = request.user
        order_dict = json.loads(request.body.decode())
        address_id = order_dict.get('address_id')
        pay_method = order_dict.get('pay_method')
        # 验证
        if not all([address_id,pay_method]):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数不完整'})
        try:
            address = Address.objects.filter(is_deleted=False,pk=address_id,user_id=user.id)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '收货地址不存在'})
        # 判断付款方式
        if not isinstance(pay_method,int):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'无效的支付方式'})
        if pay_method not in [1,2]:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'无效的支付方式'})
        # 处理 创建订单
        # 获得购物车信息
        redis_cli = get_redis_connection('carts')
        cart_dict = redis_cli.hgetall('user%s' %user.id)
        cart_dict = {int(sku_id):int(count) for sku_id,count in cart_dict.items()}
        cart_list = redis_cli.smembers('selected%s' %user.id)
        cart_list = [int(sku_id) for sku_id in cart_list]
        if not cart_list:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '未选中商品'})

        # 创建订单对对象
        # 使用事物
        with transaction.atomic():

            total_count = 0  # 总数量
            total_amount = 0  # 总金额
            freight = 10  # 运费
            status = 1
            # if pay_method == 1:
            #     status = 1
            # elif pay_method == 2:
            #     status = 1
            now = datetime.now()
            order_id = now.strftime('%Y%m%d%H%M%S') + '%09d' %user.id

            # 开启事物
            sid = transaction.savepoint()
            order = OrderInfo.objects.create(
                order_id = order_id,
                user_id = user.id,
                address_id = address_id,
                total_count = total_count,
                total_amount = total_amount,
                freight = freight,
                pay_method = pay_method,
                status = status,
            )
            # 查询库存商品
            skus = SKU.objects.filter(is_launched=True,pk__in=cart_list)
            for sku in skus:
                if sku.stock < cart_dict[sku.id]:

                    # 回滚事物
                    transaction.savepoint_rollback(sid)
                    return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存数量不足'})
                # sku.stock -= cart_dict[sku.id]
                # sku.sales += cart_dict[sku.id]
                # sku.save()

                # 乐观锁
                old_count = sku.stock   #旧库存
                new_count = old_count - cart_dict[sku.id]   #新库存
                new_sales = sku.sales + cart_dict[sku.id]
                time.sleep(5)
                # res返回受影响行数
                res = SKU.objects.filter(pk=sku.id,stock=old_count).update(stock=new_count,sales=new_sales)
                if res == 0:
                    transaction.savepoint_rollback(sid)
                    return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': "服务器忙"})

                total_count += cart_dict[sku.id]
                total_amount += sku.price * cart_dict[sku.id]
                # 创建订单商品对象
                order_goods = OrderGoods.objects.create(
                    order_id = order_id,
                    sku_id = sku.id,
                    count = cart_dict[sku.id],
                    price = sku.price
                )
            # 修改订单的信息
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()

            # 提交事物
            transaction.savepoint_commit(sid)
        # 删除购物车的数据
        redis_cli.hdel('user%s' %user.id,*cart_list)
        redis_cli.delete('selected%s' %user.id)
        # 响应
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','order_id':order_id})
# 提交成功
class SuccessOrderView(LoginRequiredMixin,View):
    def get(self,request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')
        context = {
            'order_id':order_id,
            'payment_amount':payment_amount,
            'pay_method':pay_method,
        }
        return render(request,'order_success.html',context)
# 我的订单
class MyOrderView(LoginRequiredMixin,View):
    def get(self,request,page_num):
        user = request.user
        # 查询订单对象
        orders = OrderInfo.objects.filter(user_id=user.id).order_by('-update_time')
        # 分页
        pages = Paginator(orders,2)
        page = pages.page(page_num)
        # 订单列表
        order_list = []
        for order in page:
            # 订单下的商品
            sku_list = []
            for order_sku in order.skus.all():
                sku_list.append({
                    'default_image':order_sku.sku.default_image.url,
                    'name':order_sku.sku.name,
                    'price':order_sku.price,
                    'count':order_sku.count,
                    'total':order.total_amount,
                })
            order_list.append({
                'create_time':order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'order_id':order.order_id,
                'sku_list':sku_list,
                'total_amount':order.total_amount + order.freight,
                'freight':order.freight,
                'pay_method':order.pay_method,
                'status':order.status
            })
        context = {
            'order_list':order_list,
            'surrent_page':page_num,    #当前页数
            'total_page':pages.num_pages,   # 总页数
        }
        return render(request,'user_center_order.html',context)
# 评价页面
class CommentView(LoginRequiredMixin,View):
    # 展示评价界面
    def get(self,request):
        # 接受
        order_id = request.GET.get('order_id')
        # 验证
        try:
            order_info = OrderInfo.objects.get(pk=order_id)
        except:
            return render(request,'404.html')
        # 处理
        sku_list = []
        skus = order_info.skus.filter(is_commented=False)
        for sku in skus:
            sku_list.append({
                'default_image_url':sku.sku.default_image.url,
                'price':str(sku.price),
                'name':sku.sku.name,
                'sku_id':sku.sku_id,
                'order_id':order_id
            })
        # 响应
        return render(request,'goods_judge.html',{'skus':sku_list})
    # 保存评价
    def post(self,request):
        # 接受
        param_dict = json.loads(request.body.decode())
        order_id = param_dict.get('order_id')
        sku_id = param_dict.get('sku_id')
        comment = param_dict.get('comment')
        score = param_dict.get('score')
        is_anonymous = param_dict.get('is_anonymous',False)   # 标记True，不标记无值
        # 验证
        if not all([order_id,sku_id,comment,score]):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'缺少参数'})
        try:
            # 订单商品
            order_info = OrderGoods.objects.get(order_id=order_id,sku_id=sku_id)
        except:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'订单不存在'})
        # 处理
        # 保存评论信息
        order_info.comment = comment
        order_info.score = score
        order_info.is_anonymous = is_anonymous
        order_info.is_commented = True
        order_info.save()
        # 修改订单状态
        if OrderGoods.objects.filter(order_id = order_id,is_commented=False).count() == 0:
            order = order_info.order
            order.status = 5
            order.save()
        # 响应
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK'})
# 详情页显示评价
class DetailCommentView(View):
    def get(self,request,sku_id):
        # 接受
        # 验证
        # 处理
        skus = OrderGoods.objects.filter(sku_id=sku_id,is_commented=True).order_by('-create_time')
        goods_comment_list = []
        for sku in skus:
            goods_comment_list.append({
                'username':'******' if sku.is_anonymous else sku.order.user.username,
                'comment':sku.comment,
                'score':sku.score
            })
        # 响应
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','goods_comment_list':goods_comment_list})

