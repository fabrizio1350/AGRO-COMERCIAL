from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('ofertas/', views.ventas_por_oferta, name='ventas_por_oferta'),
    path('oferta/<int:oferta_id>/responder/', views.responder_oferta, name='responder_oferta'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),
    path('productores/', views.lista_productores, name='productores'),
    path('carrito/', views.carrito_vista, name='carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('pasarela-pago/', views.pasarela_pago, name='pasarela_pago'),
    path('comprobante/<str:codigo>/', views.comprobante_pago, name='comprobante_pago'),
    path('registro/', views.registro_vista, name='registro'),
    path('login/', views.login_vista, name='login'),
    path('logout/', views.logout_vista, name='logout'),
    path('cambiar-modo/', views.cambiar_modo_vista, name='cambiar_modo'),
    path('panel-comprador/', views.panel_comprador, name='panel_comprador'),
    path('panel-productor/', views.panel_productor, name='panel_productor'),
    path('producto/nuevo/', views.crear_producto, name='crear_producto'),
    path('producto/<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    path('producto/<int:producto_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('pedido/<int:pedido_id>/estado/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('perfil/', views.perfil_vista, name='perfil'),
]
