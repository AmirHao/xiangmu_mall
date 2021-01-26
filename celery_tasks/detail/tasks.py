from django.shortcuts import render
from xiangmu_mall.utils.category import get_categories,get_breadcrumb
from goods.models import SKU
import os
from django.conf import settings
from celery_tasks.main import celery_app


@celery_app.task(name='generate_static_detail_html')
def generate_static_detail_html(sku_id):
    try:
        sku = SKU.objects.get(pk=sku_id)
    except:
        return render(None, '404.html')
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
                # 'sku_id': sku_option_dict[tuple(current_sku_temp)],
                'sku_id': sku_option_dict.get(tuple(current_sku_temp),0),
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
    response = render(None, 'detail.html', context)
    html_str = response.content.decode()


    # 写文件
    html_path = os.path.join(settings.BASE_DIR,'static/details/%s.html' %sku_id)
    with open(html_path,'w') as f:
        f.write(html_str)
