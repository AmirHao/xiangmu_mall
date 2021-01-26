import json
from datetime import datetime
from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection

from xiangmu_mall.utils.category import get_categories, get_breadcrumb
from xiangmu_mall.utils.response_code import RETCODE
from .models import GoodsCategory, SKU, GoodsVisitCount


# 列表视图
class ListView(View):
    def get(self, request, category_id, page_num):
        # 拿到所有的商品数据
        try:
            categories3 = GoodsCategory.objects.get(id=category_id)
        except:
            return render(request, '404.html')
        # 导航栏
        categories = get_categories()
        # 面包屑
        breadcrumb = get_breadcrumb(categories3)
        # 排序、分页
        skus = SKU.objects.filter(is_launched=True, category_id=category_id)
        # 排序
        sort = request.GET.get('sort', 'default')
        if sort == 'hot':
            skus = skus.order_by("-sales")
        elif sort == 'price':
            skus = skus.order_by('price')
        else:
            skus = skus.order_by('-id')
        # 分页
        paginator = Paginator(skus, 5)  # 每页显示5条数据
        page_skus = paginator.page(page_num)  # 当前页码的数据
        total_page = paginator.num_pages
        context = {
            'category': categories3,  # 三级分类
            'categories': categories,  # 导航栏
            'breadcrumb': breadcrumb,  # 面包屑
            'sort': sort,  # 排序方式
            'page_skus': page_skus,  # 当前页面的sku数据
            'total_page': total_page,  # 总页数
            "page_num": page_num
        }
        return render(request, 'list.html', context)


# 热销视图
class HotView(View):
    def get(self, request, category_id):
        hots = SKU.objects.filter(is_launched=True, category_id=category_id).order_by('-sales')[0:2]
        hot_sku_list = []
        for hot in hots:
            hot_sku_list.append({
                'id': hot.id,
                'default_image_url': hot.default_image.url,
                'name': hot.name,
                'price': hot.price
            })
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'OK',
            'hot_sku_list': hot_sku_list
        })


# 详情页视图
class DetailView(View):
    def get(self, request, sku_id):
        try:
            sku = SKU.objects.get(pk=sku_id)
        except:
            return render(request, '404.html')
        # 导航栏
        categories = get_categories()
        # 面包屑
        breadcrumb = get_breadcrumb(sku.category)
        # 商品对象
        spu = sku.spu
        """
            print(sku_id,sku.category.id,spu.id)
            指定手机的id，
            产品所属三级分类的id，
            商品所属spu的id即为手机牌子id 
        """
        # 商品规格
        # 拿到标准商品下的所有库存商品
        skus = spu.sku_set.filter(is_launched=True)
        # 构建商品规格对应库存商品的字典
        sku_option_dict = {}
        for s in skus:
            # 构造字典的键
            key_temp = []
            option_list = s.specs.order_by('spec_id')
            for option in option_list:
                key_temp.append(option.option_id)
            sku_option_dict[tuple(key_temp)] = s.id
        # 拿到当前商品的具体规格
        current_sku = [info.option_id for info in sku.specs.order_by('spec_id')]
        # 获得所有规格对象
        specs = spu.specs.all()
        specs_list = []
        # enumerate生成带下标
        for index, spec in enumerate(specs):
            spec_dict = {
                'name': spec.name,
                'options': []
            }
            # 获得所有规格选项
            options = spec.options.all()
            for option in options:
                # 深拷贝一个商品规格选项
                current_sku_temp = current_sku[:]
                # 修改为下一个库存的规格
                current_sku_temp[index] = option.id
                spec_dict['options'].append({
                    # 通过构建的规格库存键值对找到要下一个库存的id
                    'sku_id': sku_option_dict[tuple(current_sku_temp)],
                    'name': option.value,
                    'selected': option.id in current_sku
                })
            specs_list.append(spec_dict)
        # 热销排行
        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'spu': spu,
            'specs_list': specs_list
        }
        return render(request, 'detail.html', context)


# 商品访问量
class VisitVirew(View):
    def post(self, request, category_id):
        # 获取当前日期
        t = datetime.now()
        today_str = '%d-%02d-%02d' % (t.year, t.month, t.day)
        # 查询该商品当天的访问量
        try:
            visit = GoodsVisitCount.objects.get(category_id=category_id, date=today_str)
        except:
            # 不存在，新建
            GoodsVisitCount.objects.create(category_id=category_id, count=1)
        else:
            visit.count += 1
            visit.save()
        # 返回信息
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


# 浏览历史
class VisitHistoryView(LoginRequiredMixin, View):
    def post(self, request):
        sku_id = json.loads(request.body.decode()).get('sku_id')
        if not sku_id:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品id不能为空'})
        if not SKU.objects.get(id=sku_id):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品id不存在'})
        # 处理
        user = request.user
        key = 'history%d' % user.id
        # 连接缓存
        redis_cli = get_redis_connection('history')
        redis_pl = redis_cli.pipeline()
        # 去重
        redis_pl.lrem(key, 0, sku_id)
        # 新增
        redis_pl.lpush(key, sku_id)
        # 截取
        redis_pl.ltrim(key, 0, 4)
        redis_pl.execute()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

    def get(self, request):
        redis_cli = get_redis_connection('history')
        user = request.user
        key = 'history%d' % user.id
        skus = redis_cli.lrange(key, 0, -1)
        sku_list = []
        for sku in skus:
            sku_temp = SKU.objects.get(id=sku)
            sku_list.append({
                'id': sku_temp.id,
                'name': sku_temp.name,
                'default_image_url': sku_temp.default_image.url,
                'price': sku_temp.price
            })
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'OK',
            'skus': sku_list
        })
