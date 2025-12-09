from django.contrib import admin
from .models import Perfil, Producto, Banner, Carrito, ItemCarrito, Orden, ItemOrden, ConfiguracionHome

admin.site.register(Perfil)
admin.site.register(Producto)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
admin.site.register(ItemOrden)
admin.site.register(ConfiguracionHome)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'activo', 'orden')
    list_editable = ('activo', 'orden')

class ItemOrdenInline(admin.TabularInline):
    """Permite ver los productos comprados dentro de la misma pantalla de la Orden"""
    model = ItemOrden
    extra = 0
    readonly_fields = ('producto', 'cantidad', 'precio')

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'usuario', 'total', 'estado', 'fecha', 'ver_comprobante_miniatura')
    
    list_filter = ('estado', 'fecha', 'metodo_pago')
    
    search_fields = ('usuario__username', 'usuario__email', 'id')
    
    readonly_fields = ('ver_comprobante_grande',)
    
    exclude = ('comprobante_b64',)


    inlines = [ItemOrdenInline]

    
    def ver_comprobante_miniatura(self, obj):
        if obj.comprobante_b64:
           
            return format_html(
                '<img src="data:image/jpeg;base64,{}" width="50" height="50" style="object-fit:cover; border-radius:4px; border:1px solid #ccc;" />',
                obj.comprobante_b64
            )
        return "Sin comprobante"
    ver_comprobante_miniatura.short_description = "Comprobante"

    
    def ver_comprobante_grande(self, obj):
        if obj.comprobante_b64:
            
            return format_html(
                '<div style="text-align:center;">'
                '<img src="data:image/jpeg;base64,{}" style="max-width: 500px; max-height:600px; border: 2px solid #ddd; padding: 5px;" />'
                '<br><span style="color:#666;">Imagen decodificada desde Base64</span>'
                '</div>',
                obj.comprobante_b64
            )
        return "El cliente no ha subido comprobante."
    ver_comprobante_grande.short_description = "Vista Previa del Comprobante"
