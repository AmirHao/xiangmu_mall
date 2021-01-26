from django.db import models

# Create your models here.
class Area(models.Model):
    """省市区"""
    name = models.CharField(max_length=30)
    parent = models.ForeignKey('self',related_name='subs', null=True)

    class Meta:
        db_table = 'tb_areas'