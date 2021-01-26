from django.shortcuts import render
# Create your views here.
from django.views import View
from .models import Content,ContentCategory
from xiangmu_mall.utils.category import get_categories


class IndexView(View):

    def get(self,request):
        # 获得三级商品列表
        categories = get_categories()

        # 获得首页广告内容
        contents = {}
        # 拿到广告位置
        ContentCategorys = ContentCategory.objects.all()
        for content in ContentCategorys:
            contents[content.key] = content.content_set.filter(status=True).order_by('sequence')

        # 构造返回数据字典
        context = {'categories':categories,
                   'contents':contents}
        return render(request,'index.html',context)

