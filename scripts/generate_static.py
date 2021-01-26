#!/usr/bin/env python

import os
import django
import sys

sys.path.insert(0,'../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xiangmu_mall.settings.dev")
django.setup()

from goods.models import SKU
from celery_tasks.detail.tasks import generate_static_detail_html


if __name__ == '__main__':
    # 查询所有商品，遍历执行
    skus = SKU.objects.filter(is_launched=True)
    for sku in skus:
        generate_static_detail_html(sku.id)
    print('OK')