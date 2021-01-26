from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^carts/$',views.CartView.as_view()),
    url(r'^carts/selection/$',views.SelectAllView.as_view()),
    url(r'^carts/simple/$',views.SimpleCartView.as_view()),
]
