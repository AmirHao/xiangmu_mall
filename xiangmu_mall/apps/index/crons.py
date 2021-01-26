import os
from django.shortcuts import render
from .models import Content,ContentCategory
from xiangmu_mall.utils.category import get_categories
from django.conf import settings


# 首页静态化
def generate_static_index_html():
    # 生成首页html字符串
    categories = get_categories()
    # 获得首页广告内容
    contents = {}
    # 拿到广告位置
    ContentCategorys = ContentCategory.objects.all()
    for content in ContentCategorys:
        contents[content.key] = content.content_set.filter(status=True).order_by('sequence')
    # 构造返回数据字典
    context = {'categories': categories,
               'contents': contents}
    response = render(None, 'index.html', context)
    html_str = response.content.decode()
    # 写入文件
    index_path = os.path.join(settings.BASE_DIR,'static/contents/index.html')
    with open(index_path,'w') as f:
        f.write(html_str)
