import json
from django_redis import get_redis_connection
from goods.models import SKU
from xiangmu_mall.utils.response_code import RETCODE
from django import http
from django.shortcuts import render
from django.views import View
from xiangmu_mall.utils import mall_json
from .constants import CAR_COOKIE_EXPIRE

# 购物车
class CartView(View):
    # 新增购物车
    def post(self,request):
        # 接受
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')
        count = param_dict.get('count')
        # 验证
        if not all([sku_id,count]):
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'参数不完整'})
        try:
            sku = SKU.objects.get(id=sku_id)
        except:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'库存商品不存在'})
        try:
            count = int(count)
        except:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'数量格式不正确'})
        if count < 0 | count > sku.stock:
            return http.JsonResponse({'code':RETCODE.PARAMERR,'errmsg':'数量小于0 或者 超过库存数量'})
        # 处理
        # 设置响应对象
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        user = request.user
        if user.is_authenticated:
            # 登陆，写入redis
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            redis_pl.hset('user%s' %user.id,sku_id,count)
            redis_pl.sadd('selected%s' %user.id,sku_id)
            redis_pl.execute()
        else:
            # 未登录，写入cookie
            # 读取cookie
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                cart_dict = {}
            else:
                cart_dict = mall_json.loads(cart_str)
            # 构建字典
            cart_dict[sku_id]={'count':count,'selected':True}
            # 写入cookie
            response.set_cookie('cart',mall_json.dumps(cart_dict),max_age=CAR_COOKIE_EXPIRE)
        # 响应
        return response

    # 查询购物车
    def get(self,request):
        user = request.user
        new_dict = {}
        if user.is_authenticated:
            # 已登陆，查redis
            redis_cli = get_redis_connection('carts')
            # 查sku
            sku_byt = redis_cli.hgetall('user%s' %user.id)
            # 查选中状态
            selected_byt = redis_cli.smembers('selected%s' %user.id)
            # 数据转化 byte ---->
            for sku_id,count in sku_byt.items():
                new_dict[int(sku_id)] = {
                    'count':int(count),
                    'selected':sku_id in selected_byt
                }
                """
                {
                sku_id1:{
                count:1,
                selected:True
                },
                sku_id2:{
                count:1,
                selected:True
                },...
                }
                """
        else:
            # 未登录，查cookie
            cart_str = request.COOKIES.get('cart')
            if cart_str is not None:
                new_dict = mall_json.loads(cart_str)
        # 查询库存对象
        skus = SKU.objects.filter(pk__in=new_dict.keys(),is_launched=True)
        # 构建前端格式
        sku_list = []
        for sku in skus:
            sku_list.append({
                'id':sku.id,
                'name':sku.name,
                'count':new_dict[sku.id]['count'],
                # 将True转‘True’，方便json解析
                'selected':str(new_dict[sku.id]['selected']),
                'default_image_url': sku.default_image.url,
                # 从Decimal('10.2')中取出'10.2'，方便json解析
                'price': str(sku.price),
                'amount': str(sku.price * new_dict[sku.id]['count']),
            })
        context = {
            'cart_skus':sku_list
        }
        return render(request,'cart.html',context)

    # 修改购物车
    def put(self,request):
        # 接受
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')
        count = param_dict.get('count')
        selected = param_dict.get('selected',True)
        # 验证 bool值不作为非空验证
        if not all([sku_id, count]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '参数不完整'})
        # sku_id是否存在
        try:
            sku = SKU.objects.get(pk=sku_id)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})
        # 整数验证
        try:
            count = int(count)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量格式不对'})
        # 是否为负数
        if count < 0:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量不能小于0'})
        # 是否超过库存上限
        if count > sku.stock:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '超过库存上限'})
        # 验证selected是否为bool
        if not isinstance(selected, bool):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '选中状态无效'})
        # 处理
        user = request.user
        # 响应

        response =  http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok',
                                       'cart_sku': {
                                                    'id': sku_id,
                                                    'count': count,
                                                    'selected': str(selected),
                                                    'name': sku.name,
                                                    'default_image_url': sku.default_image.url,
                                                    'price': str(sku.price),
                                                    'amount': str(sku.price * count),
                                                }})
        if user.is_authenticated():
            # 已登陆，修改redis
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            # 修改哈希中的数量
            redis_pl.hset('user%s' %user.id,sku_id,count)
            if selected:
                # 选中，添加进去
                redis_pl.sadd('selected%s' %user.id,sku_id)
            else:
                # 未选中，移除sku_id
                redis_pl.srem('selected%s' %user.id,sku_id)
            redis_pl.execute()
        else:
            # 未登录，修改cookie
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '购物车信息无效'})
            cart_dict = mall_json.loads(cart_str)
            cart_dict[sku_id] = {'count':count,'selected':selected}
            response.set_cookie('cart',mall_json.dumps(cart_dict),max_age=CAR_COOKIE_EXPIRE)
        return response

    # 删除购物车
    def delete(self,request):
        # 接受
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')
        # 验证
        if not all([sku_id]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '参数不完整'})
        # sku_id是否存在
        try:
            sku = SKU.objects.get(pk=sku_id)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})
        # 处理
        user = request.user
        response = http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok'})
        if user.is_authenticated:
            # 登陆，从redis删
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            redis_pl.hdel('user%s' %user.id,sku_id)
            redis_pl.srem('selected%s' %user.id,sku_id)
            redis_pl.execute()
        else:
            # 未登录，从cookie删
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '购物车是空的'})
            cart_dict = mall_json.loads(cart_str)
            # 判断要删除的是否存在，可以删除
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            response.set_cookie('cart',mall_json.dumps(cart_dict),max_age=CAR_COOKIE_EXPIRE)
        # 响应
        return response
# 购物车全选
class SelectAllView(View):
    def put(self,request):
        # 接受
        param_dict = json.loads(request.body.decode())
        selected = param_dict.get('selected', True)
        # 验证
        if not isinstance(selected, bool):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '选中状态无效'})
        # 处理
        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        if user.is_authenticated:
            # 已登陆，操作redis
            redis_cli = get_redis_connection('carts')
            if selected:
                # 如果为true则代表为全选 即将hash中的所有sku_id加入到set
                # hkeys 取属性 hvals 取属性值 得到的是列表
                skus = redis_cli.hkeys('user%s' %user.id)
                redis_cli.sadd('selected%s' %user.id,*skus)
            else:
                # 全部不选，移除
                redis_cli.delete('selected%s' %user.id)
                pass
        else:
            # 未登录，操作cookie
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '购物车不能为空'})
            cart_dict = mall_json.loads(cart_str)
            for sku_id,dict in cart_dict.items():
                dict['selected'] = selected
            response.set_cookie('cart',mall_json.dumps(cart_dict),max_age=CAR_COOKIE_EXPIRE)
        # 响应
        return response
# 购物车simple
class SimpleCartView(View):
    def get(self,request):
        user = request.user
        cart_dict = {}
        if user.is_authenticated:
            # 已登陆，从redis查
            redis_cli = get_redis_connection('carts')
            cart_bytes = redis_cli.hgetall('user%s' %user.id)
            cart_dict = {int(sku_id):int(count) for sku_id,count in cart_bytes.items()}
            '''{sku_id:count}'''
        else:
            # 未登录，从cookie查
            cart_str = request.COOKIES.get('cart')
            if cart_str is not None:
                cart_dict = mall_json.loads(cart_str)
                '''{sku_id:{count:1,selected:True}}'''
                cart_dict = {sku_id:dict['count'] for sku_id,dict in cart_dict.items()}

        skus = SKU.objects.filter(pk__in=cart_dict.keys(),is_launched=True)
        sku_list = []
        for sku in skus:
            sku_list.append({
                'id':sku.id,
                'name':sku.name,
                'count':cart_dict[sku.id],
                'default_image_url':sku.default_image.url,
            })
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'OK','cart_skus':sku_list})

