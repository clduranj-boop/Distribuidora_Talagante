from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Producto, Orden, Carrito, ItemCarrito, Perfil, ItemOrden, ConfiguracionHome
from .serializers import ProductoSerializer
from .forms import ProductoForm
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
from urllib.parse import quote
from io import BytesIO
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage

# Decorador para verificar si el usuario es superusuario
def is_superuser(user):
    return user.is_superuser

# Función para generar PDF de boleta
def generate_boleta_pdf(orden):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 800, "Boleta Electrónica")
    c.drawString(100, 780, f"Orden ID: {orden.id}")
    c.drawString(100, 760, f"Fecha: {orden.fecha}")
    c.drawString(100, 740, f"Cliente: {orden.usuario.username}")
    y = 700
    c.drawString(100, y, "Productos:")
    y -= 20
    for item in orden.itemorden_set.all():
        c.drawString(100, y, f"{item.cantidad} x {item.producto.nombre} - ${item.precio * item.cantidad}")
        y -= 20
    c.drawString(100, y, f"Total: ${orden.total}")
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Vistas
def home(request):
    return render(request, 'core/home.html', {'mensaje': 'Bienvenido a Distribuidora Talagante'})

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_home')
            try:
                perfil = Perfil.objects.get(usuario=user)
                if perfil.es_admin:
                    return redirect('admin_panel')
                else:
                    return redirect('catalogo')
            except Perfil.DoesNotExist:
                return redirect('catalogo')
        else:
            return render(request, 'core/login.html', {'error': 'Credenciales inválidas'})
    return render(request, 'core/login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        nombre_completo = request.POST['nombre_completo']
        rut = request.POST['rut']
        telefono = request.POST.get('telefono', '')
        if User.objects.filter(username=username).exists():
            return render(request, 'core/login.html', {'reg_error': 'El usuario ya existe'})
        if User.objects.filter(email=email).exists():
            return render(request, 'core/login.html', {'reg_error': 'El email ya está registrado'})
        if Perfil.objects.filter(rut=rut).exists():
            return render(request, 'core/login.html', {'reg_error': 'El RUT ya está registrado'})
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            perfil = Perfil.objects.create(
                usuario=user,
                nombre_completo=nombre_completo,
                rut=rut,
                telefono=telefono,
                es_admin=False
            )
            login(request, user)
            return redirect('catalogo')
        except ValidationError as e:
            return render(request, 'core/login.html', {'reg_error': str(e)})
    return render(request, 'core/login.html')

def catalogo(request):
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    categorias = Producto.objects.filter(activo=True).values_list('categoria', flat=True).distinct()
    if request.GET.get('categoria'):
        productos = productos.filter(categoria=request.GET.get('categoria'))
    if request.GET.get('precio_max'):
        productos = productos.filter(precio__lte=request.GET.get('precio_max'))
    context = {'productos': productos, 'categorias': categorias}
    return render(request, 'core/catalogo.html', context)

@login_required
def carrito(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)
    total = sum(item.subtotal for item in items)
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/carrito.html', context)

@login_required
def mis_compras(request):
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'core/mis_compras.html', {'ordenes': ordenes})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def admin_panel(request):
    try:
        perfil = Perfil.objects.get(usuario=request.user)
        if not perfil.es_admin:
            return redirect('home')
    except Perfil.DoesNotExist:
        return redirect('home')
    productos = Producto.objects.all()
    ordenes = Orden.objects.all()
    return render(request, 'core/admin_panel.html', {'productos': productos, 'ordenes': ordenes})

@login_required
def add_to_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    carrito, created = Carrito.objects.get_or_create(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    )
    item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
    if not created:
        item.cantidad += 1
    item.save()
    return redirect('catalogo')

@login_required
def remove_from_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    producto = item.producto
    producto.stock += item.cantidad
    producto.save()
    item.delete()
    return redirect('carrito')

@login_required
def checkout(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})
    items = carrito.itemcarrito_set.all()
    for item in items:
        item.subtotal = item.producto.precio * Decimal(item.cantidad)
    total = sum(item.subtotal for item in items)
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'core/checkout.html', context)

class ProductoListAPIView(APIView):
    def get(self, request):
        productos = Producto.objects.filter(activo=True).order_by('nombre')
        categoria = request.query_params.get('categoria')
        precio_max = request.query_params.get('precio_max')
        if categoria:
            productos = productos.filter(categoria=categoria)
        if precio_max:
            try:
                productos = productos.filter(precio__lte=float(precio_max))
            except ValueError:
                return Response({"error": "precio_max debe ser un número válido"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProductoSerializer(productos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def admin_home(request):
    productos_bajo_stock = Producto.objects.filter(stock__lt=10)
    ordenes = Orden.objects.filter(estado__in=['pendiente', 'confirmacion', 'preparacion'])
    context = {
        'productos_bajo_stock': productos_bajo_stock,
        'ordenes': ordenes,
    }
    return render(request, 'core/admin_home.html', context)

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_list(request):
    productos = Producto.objects.all().order_by('nombre')
    if request.GET.get('categoria'):
        productos = productos.filter(categoria=request.GET.get('categoria'))
    if request.GET.get('stock_max'):
        try:
            productos = productos.filter(stock__lte=int(request.GET.get('stock_max')))
        except ValueError:
            messages.error(request, 'El stock máximo debe ser un número válido.')
    return render(request, 'core/admin_productos.html', {'productos': productos})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_create(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado exitosamente.')
            return redirect('producto_list')
        else:
            messages.error(request, 'Error en el formulario. Revisa los campos.')
    else:
        form = ProductoForm()
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Crear'})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_update(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado exitosamente.')
            return redirect('producto_list')
        else:
            messages.error(request, 'Error en el formulario. Revisa los campos.')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Editar', 'producto': producto})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def producto_delete(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('producto_list')
    return render(request, 'core/producto_confirm_delete.html', {'producto': producto})

@login_required
@user_passes_test(is_superuser, login_url='catalogo')
def orden_detail(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    items = orden.itemorden_set.all()
    if request.method == 'POST':
        new_estado = request.POST.get('estado')
        if new_estado in [e[0] for e in Orden.ESTADOS]:
            orden.estado = new_estado
            orden.save()
            if new_estado == 'pagado':
                pdf = generate_boleta_pdf(orden)
                user_email = orden.usuario.email
                if user_email:
                    email = EmailMessage(
                        f'Boleta Electrónica para Orden #{orden.id}',
                        'Gracias por su compra. Adjuntamos la boleta electrónica.',
                        'noreply@distribuidora.com',
                        [user_email],
                    )
                    email.attach(f'boleta_{orden.id}.pdf', pdf, 'application/pdf')
                    email.send()
                    messages.success(request, 'Estado actualizado y boleta enviada por email.')
                else:
                    messages.warning(request, 'Estado actualizado, pero no se pudo enviar boleta: usuario sin email.')
            else:
                messages.success(request, 'Estado actualizado.')
        return redirect('orden_detail', orden_id=orden.id)
    return render(request, 'core/orden_detail.html', {'orden': orden, 'items': items})

@login_required
def generate_whatsapp(request):
    carrito = Carrito.objects.filter(
        usuario=request.user,
        creado__gte=timezone.now() - timezone.timedelta(minutes=15)
    ).first()
    if not carrito:
        return redirect('carrito')
    items = carrito.itemcarrito_set.all()
    total = sum(item.producto.precio * Decimal(item.cantidad) for item in items)
    orden = Orden.objects.create(
        usuario=request.user,
        estado='pendiente',
        total=total,
        metodo_pago='transferencia',
    )
    for item in items:
        ItemOrden.objects.create(
            orden=orden,
            producto=item.producto,
            cantidad=item.cantidad,
            precio=item.producto.precio
        )
    carrito.delete()
    message = f"Pedido #{orden.id}\n"
    for item in orden.itemorden_set.all():
        message += f"{item.cantidad} x {item.producto.nombre} - ${item.precio * item.cantidad}\n"
    message += f"Total: ${orden.total}\nPor favor, confirme el pago."
    config = ConfiguracionHome.objects.first()
    number = config.numero_contacto if config else '56912345678'
    wa_url = f"https://wa.me/{number}?text={quote(message)}"
    return redirect(wa_url)