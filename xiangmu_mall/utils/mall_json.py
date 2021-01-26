import pickle
import base64


# 字典转化字符串
def dumps(param_dict):
    # 字典转字节
    param_bytes = pickle.dumps(param_dict)
    # 字节编码
    param_str = base64.b64encode(param_bytes)
    # 返回字符串
    return param_str.decode()
    '''
    {'selected': True, 'ocunt': 2}
    b'\x80\x03}q\x00(X\x08\x00\x00\x00selectedq\x01\x88X\x05\x00\x00\x00ocuntq\x02K\x02u.'
    b'gAN9cQAoWAgAAABzZWxlY3RlZHEBiFgFAAAAb2N1bnRxAksCdS4='
    gAN9cQAoWAgAAABzZWxlY3RlZHEBiFgFAAAAb2N1bnRxAksCdS4=
    '''

# 字符串转化字典
def loads(param_str):
    # 字符串转化为字节
    param_bytes = param_str.encode()
    # 字节解码为二进制
    param_dict = base64.b64decode(param_bytes)
    # 二进制转化为字典返回
    return pickle.loads(param_dict)
    '''
    gAN9cQAoWAgAAABzZWxlY3RlZHEBiFgFAAAAb2N1bnRxAksCdS4=
    b'gAN9cQAoWAgAAABzZWxlY3RlZHEBiFgFAAAAb2N1bnRxAksCdS4='
    b'\x80\x03}q\x00(X\x08\x00\x00\x00selectedq\x01\x88X\x05\x00\x00\x00ocuntq\x02K\x02u.'
    {'selected': True, 'ocunt': 2}
    '''


