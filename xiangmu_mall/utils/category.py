from goods.models import GoodsChannel


# 获得三级商品列表
def get_categories():
    # 类别
    categories = {}
    # 频道
    channels = GoodsChannel.objects.order_by('group_id' ,'sequence')
    # 遍历频道
    for channel in channels:
        # 第几频道
        group_id = channel.group_id
        # 判断当前频道是否存在
        if group_id not in categories:
            categories[group_id] = {'cat1' :[] ,'cat2' :[]}
        # 当前一级类别
        cat1 = channel.category
        # 追加一级分类
        categories[group_id]['cat1'].append({
            'name' :cat1.name,
            'url' :channel.url
        })
        # 追加二级分类
        for cat2 in cat1.subs.all():
            # 追加二级分类
            categories[group_id]['cat2'].append(cat2)
            # 三级分类列表
            cat2.cat3 = []
            # 追加三级分类
            for cat3 in cat2.subs.all():
                cat2.cat3.append(cat3)

    return categories

# 获得面包屑路径
def get_breadcrumb(categories3):
    categories2 = categories3.parent
    categories1 = categories2.parent
    # 构建前端字典
    breadcrumb = {
        'cat1': {
            'url': categories1.goodschannel_set.all()[0].url,
            'name': categories1.name
        },
        'cat2': categories2,
        'cat3': categories3,
    }
    return breadcrumb
