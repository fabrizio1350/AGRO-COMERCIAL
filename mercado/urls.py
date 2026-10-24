from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('productores/', views.lista_productores, name='productores'),
    path('registro/', views.registro_vista, name='registro'),
    path('login/', views.login_vista, name='login'),
    path('logout/', views.logout_vista, name='logout'),
    path('panel-productor/', views.panel_productor, name='panel_productor'),
    path('producto/nuevo/', views.crear_producto, name='crear_producto'),
    path('producto/<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    path('producto/<int:producto_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('pedido/<int:pedido_id>/estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('perfil/', views.perfil_vista, name='perfil'),
]
