from rest_framework import serializers
from .models import Producto, ItemCarrito, Orden, ItemOrden
import urllib.parse
from django.db import models
from .models import ConfiguracionHome

class ProductoSerializer(serializers.ModelSerializer):
    imagen = models.JSONField(default=list, blank=True, null=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(source='producto.precio', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'precio', 'categoria', 'stock', 'fecha_vencimiento', 'imagen', 'activo']
        
class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(source='producto.precio', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal']

    def get_subtotal(self, obj):
        return obj.cantidad * obj.producto.precio

class ItemOrdenSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = ItemOrden
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio']


class OrdenSerializer(serializers.ModelSerializer):
    items = ItemOrdenSerializer(many=True, read_only=True, source='itemorden_set')
    whatsapp_link = serializers.SerializerMethodField()

    class Meta:
        model = Orden
        fields = ['id', 'usuario', 'fecha', 'estado', 'total', 'metodo_pago', 'items', 'whatsapp_link']

    def get_whatsapp_link(self, obj):
        # Generar el mensaje para WhatsApp
        mensaje = f"Resumen del pedido #{obj.id}:\n"
        for item in obj.itemorden_set.all():
            mensaje += f"- {item.producto.nombre} x {item.cantidad}: ${item.cantidad * item.precio}\n"
        mensaje += f"Total: ${obj.total}\nEstado: {obj.get_estado_display()}\nMétodo de pago: {obj.get_metodo_pago_display()}"
        # Codificar el mensaje para la URL
        mensaje_encoded = urllib.parse.quote(mensaje)
        # Obtener el número de WhatsApp desde ConfiguracionHome
        configuracion = ConfiguracionHome.objects.first()
        numero_whatsapp = configuracion.numero_contacto if configuracion else "56949071013"  # Fallback si no hay configuración
        return f"https://wa.me/{numero_whatsapp}?text={mensaje_encoded}"

