from django.contrib import admin
from .models import Perfil, Producto, Carrito, ItemCarrito, Orden, ItemOrden, ConfiguracionHome

admin.site.register(Perfil)
admin.site.register(Producto)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
admin.site.register(Orden)
admin.site.register(ItemOrden)
admin.site.register(ConfiguracionHome)