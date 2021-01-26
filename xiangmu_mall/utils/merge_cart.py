from . import mall_json
from django_redis import get_redis_connection


def cart_cookie_to_redis(request,response):
    user = request.user
    # 读取cookie
    cart_str = request.COOKIES.get('cart')
    if cart_str is None:
        return response
    cart_dict = mall_json.loads(cart_str)
    # 写入redis
    redis_cli = get_redis_connection('carts')
    redis_pl = redis_cli.pipeline()
    for sku_id,dict in cart_dict.items():
        # 写hash
        redis_pl.hset('user%s' %user.id,sku_id,dict['count'])
        # 写set
        if dict['selected']:
            redis_pl.sadd('selected%s' %user.id,sku_id)
        else:
            redis_pl.srem('selected%s' % user.id, sku_id)
    redis_pl.execute()
    # 删除cookie
    response.delete_cookie('cart')
    return response