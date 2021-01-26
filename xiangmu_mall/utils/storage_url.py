from django.conf import settings
from django.core.files.storage import Storage


class FdfsStorage(Storage):

    def url(self, name):
        return settings.STORAGE_URL_PRE + name
