from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.core.cache import cache
from xiangmu_mall.utils.response_code import RETCODE
from .models import Area


class AreaView(View):
    def get(self,request):
        # 接受
        area_id = request.GET.get('area_id')
        # 验证
        # 处理
        if area_id is None:
            # 读缓存
            province_list = cache.get('province_list')
            if province_list is None:
                # 省份信息
                provinces = Area.objects.filter(parent__isnull=True)
                province_list = []
                for p in provinces:
                    province_list.append({
                        'id':p.id,
                        'name':p.name
                    })
                # 写缓存
                cache.set('province_list',province_list,3600)
            return JsonResponse({
                'code':RETCODE.OK,
                'errmsg':'OK',
                'province_list':province_list
            })
        else:
            chi_data = cache.get('area'+area_id)
            if chi_data is None:
                # 市区信息
                try:
                    # 获取父级，使用一对多的related_name
                    sub = Area.objects.get(id=area_id)
                    childs = sub.subs.all()
                    # 转格式
                    childs_list = []
                    for chi in childs:
                        childs_list.append({
                            'id':chi.id,
                            'name':chi.name
                        })
                    chi_data = {
                        'id':sub.id,
                        'name':sub.name,
                        'subs':childs_list
                    }
                    # 写缓存
                    cache.set('area'+area_id,chi_data,3600)
                except:
                    return JsonResponse({'code': RETCODE.DBERR, 'errmsg': '城市或区数据错误'})
            return JsonResponse({
                'code': RETCODE.OK,
                'errmsg': 'OK',
                'sub_data': chi_data
            })
        # 响应
