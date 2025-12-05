from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from decimal import Decimal
import datetime
from datetime import timedelta
import random


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nombre = models.CharField("Nombre(s)", max_length=70)
    apellido_paterno = models.CharField("Apellido Paterno", max_length=50)
    apellido_materno = models.CharField("Apellido Materno", max_length=50, blank=True, null=True)
    rut = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{7,8}-[\dKk]$', message='Formato RUT inválido')],
        help_text="Ejemplo: 11527103-2"
    )
    telefono = models.CharField(max_length=15, blank=True, null=True)
    es_admin = models.BooleanField(default=False)

    def nombre_completo(self):
        if self.apellido_materno:
            return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"
        return f"{self.nombre} {self.apellido_paterno}"
    nombre_completo.short_description = "Nombre Completo"

    def __str__(self):
        return self.nombre_completo()

    class Meta:
        verbose_name_plural = "Perfiles"


class UnidadMedida(models.TextChoices):
    KG = 'KG', 'Kilogramos'
    UN = 'UN', 'Unidad / Bolsa'
    CJ = 'CJ', 'Caja'


class Producto(models.Model):
    codigo_barras = models.CharField(max_length=50, unique=True, blank=True, null=True,help_text="Se genera automáticamente si lo dejas vacío")
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)
    unidad_medida = models.CharField(max_length=2, choices=UnidadMedida.choices, default=UnidadMedida.UN)
    stock = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('0.000'))
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="Precio"
    )
    tamano_paquete = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1.000'), help_text="Ej: 10 para caja de 10 unidades")
    producto_hijo = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='productos_padre')

    fecha_vencimiento = models.DateField(null=True, blank=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} [{self.codigo_barras or 'Sin código'}]"

    def bajo_stock(self):
        return self.stock < Decimal('10.000')

    def agregar_stock(self, cantidad: Decimal):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        self.stock += cantidad
        self.save(update_fields=['stock'])
        if self.producto_hijo:
            self.producto_hijo.agregar_stock(cantidad * self.tamano_paquete)

    def restar_stock(self, cantidad: Decimal):
        if cantidad <= 0 or self.stock < cantidad:
            raise ValueError("Stock insuficiente")
        self.stock -= cantidad
        self.save(update_fields=['stock'])
        if self.producto_hijo:
            self.producto_hijo.restar_stock(cantidad * self.tamano_paquete)


class Carrito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'producto')

    def save(self, *args, **kwargs):
        if self.producto.stock < self.cantidad:
            raise ValueError(f"Stock insuficiente para {self.producto.nombre}")
        if not self.pk:
            self.producto.stock -= self.cantidad
            self.producto.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.producto.stock += self.cantidad
        self.producto.save()
        super().delete(*args, **kwargs)


class Orden(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente de Pago'),
        ('confirmacion', 'En Confirmación'),
        ('preparacion', 'En Preparación'),
        ('despacho', 'En Despacho / Listo para Retiro'),
        ('cancelado', 'Cancelado'),
        ('completado', 'Completado'),
    ]
    METODOS_PAGO = [
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Pago en Efectivo (Retiro)'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='transferencia')
    instrucciones_transferencia = models.TextField(default="Realice transferencia a Cuenta Corriente XXXX-XXXX y envíe comprobante por WhatsApp.")

    # CAMPO CORREGIDO: solo imagen
    comprobante = models.ImageField(upload_to='comprobantes/', blank=True, null=True, help_text="Foto del comprobante de pago")

    # CAMPO NUEVO: para notas o links (ej: link de WebPay, comentario, etc.)
    nota_comprobante = models.TextField(blank=True, null=True, help_text="Link o nota del comprobante (opcional)")

    mensaje_cliente = models.TextField(blank=True, help_text="Mensaje opcional del cliente")

    def __str__(self):
        return f"Orden #{self.id} - {self.usuario.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Restaurar stock si se cancela
        if self.estado == 'cancelado':
            for item in self.itemorden_set.all():
                item.producto.agregar_stock(item.cantidad)


class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class ConfiguracionHome(models.Model):
    fotos_carrusel = models.JSONField(default=list, blank=True, null=True)
    numero_contacto = models.CharField(max_length=15, default="56949071013")
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Configuración Home"


class CodigoVerificacion(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    creado_en = models.DateTimeField(auto_now_add=True)
    expirado = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = f"{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)

    def es_valido(self):
        return not self.expirado and timezone.now() < self.creado_en + timedelta(minutes=10)