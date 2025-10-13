from django.contrib import admin
from django.urls import path, include
from core.views import (  # Importa las vistas personalizadas de core
    home, catalogo, carrito, mis_compras, login_view, register, logout_view,
    admin_panel, add_to_carrito, remove_from_carrito, checkout, ProductoListAPIView,
    admin_home, producto_list, producto_create, producto_update, producto_delete,
    orden_detail, generate_whatsapp
)

urlpatterns = [
    # Rutas personalizadas (incluyendo las de "admin" personalizadas) - ANTES del admin de Django
    path('', home, name='home'),
    path('catalogo/', catalogo, name='catalogo'),
    path('carrito/', carrito, name='carrito'),
    path('mis-compras/', mis_compras, name='mis_compras'),
    path('login/', login_view, name='login'),
    path('register/', register, name='register'),
    path('logout/', logout_view, name='logout'),
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('add_to_carrito/<int:producto_id>/', add_to_carrito, name='add_to_carrito'),
    path('remove_from_carrito/<int:item_id>/', remove_from_carrito, name='remove_from_carrito'),
    path('api/productos/', ProductoListAPIView.as_view(), name='producto_list_api'),
    path('checkout/', checkout, name='checkout'),
    path('generate_whatsapp/', generate_whatsapp, name='generate_whatsapp'),
    path('admin_home/', admin_home, name='admin_home'),
    path('admin/producto/crear/', producto_create, name='producto_create'),
    path('admin/producto/editar/<int:producto_id>/', producto_update, name='producto_update'),
    path('admin/producto/eliminar/<int:producto_id>/', producto_delete, name='producto_delete'),
    path('admin/productos/', producto_list, name='producto_list'),  # ¡Esta es la clave para /admin/productos/!
    path('admin/orden/<int:orden_id>/', orden_detail, name='orden_detail'),

    # Django Admin - DESPUÉS de las personalizadas para evitar conflictos
    path('admin/', admin.site.urls),
]