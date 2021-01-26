from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as TSerializer


# 加密
def dumps(json, expire):
    # 创建对象，一参为秘钥，二参为过期时间
    serializer = TSerializer(settings.SECRET_KEY, expire)
    # 获取二进制
    json_str = serializer.dumps(json)
    return json_str.decode()


# 解密
def loads(str, expire):
    # 创建对象
    serializer = TSerializer(settings.SECRET_KEY, expire)
    try:
        json_dic = serializer.loads(str)
    except:
        return None
    else:
        return json_dic
