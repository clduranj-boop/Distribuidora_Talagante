from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Producto, Orden, Carrito, ItemCarrito, Perfil, ItemOrden
import urllib.parse
from .serializers import ProductoSerializer
from .forms import ProductoForm
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import ensure_csrf_cookie
import requests
from datetime import timedelta
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Carrito, ItemCarrito, Orden, ItemOrden, User
from .serializers import OrdenSerializer
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Producto, Orden
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
from decimal import Decimal
from .models import Producto
from .forms import EscaneoEntradaForm, ProductoRapidoForm
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


#Validación de contraseña y registro
from .validators import validar_contraseña_fuerte  
import re
#Verificacion Correo seguro
from django.core.mail import send_mail
# Decorador para verificar si el usuario es superusuario
from .models import Perfil, CodigoVerificacion
import random


def is_superuser(user):
    return user.is_superuser

# Vistas existentes de tu proyecto
def home(request):
    # Obtener 4 productos aleatorios para mostrar en el home
    # El '?' ordena aleatoriamente (random)
    productos_destacados = Producto.objects.filter(activo=True).order_by('?')[:4]
    
    context = {
        'mensaje': 'Bienvenido a Distribuidora Talagante',
        'productos': productos_destacados
    }
    return render(request, 'core/home.html', context)

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


def verificar_codigo(request):
    # FORZAR QUE EL USUARIO ESTÉ LOGUEADO (aunque is_active=False)
    if not request.user.is_authenticated:
        # Buscar si hay un usuario reciente con código pendiente
        try:
            ultimo_codigo = CodigoVerificacion.objects.filter(
                creado_en__gte=timezone.now() - timedelta(minutes=15)
            ).latest('creado_en')
            user = ultimo_codigo.usuario
            # LOGUEAR FORZADAMENTE AL USUARIO
            login(request, user)
        except CodigoVerificacion.DoesNotExist:
            return redirect('login')

    user = request.user

    # Si ya está activo → ir al home
    if user.is_active:
        return redirect('home')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        try:
            cod_obj = CodigoVerificacion.objects.get(
                usuario=user,
                codigo=codigo,
                expirado=False
            )
            if cod_obj.creado_en >= timezone.now() - timedelta(minutes=10):
                user.is_active = True
                user.save()
                cod_obj.expirado = True
                cod_obj.save()
                messages.success(request, "¡Cuenta verificada con éxito! Bienvenido.")
                return redirect('home')
            else:
                messages.error(request, "El código ha expirado.")
        except CodigoVerificacion.DoesNotExist:
            messages.error(request, "Código incorrecto.")

    return render(request, 'core/verificar_codigo.html')



def register(request):
    if request.method == 'POST':
        # --- Capturar datos ---
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        nombre = request.POST.get('nombre', '').strip().title()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip().title()
        apellido_materno = request.POST.get('apellido_materno', '').strip().title()
        rut_raw = request.POST.get('rut', '').strip().upper()
        telefono = request.POST.get('telefono', '').strip()

        # ==================== LIMPIAR RUT ====================
        rut_sin_formato = re.sub(r'[^\dK]', '', rut_raw)
        if len(rut_sin_formato) < 8:
            messages.error(request, "El RUT debe tener al menos 8 dígitos.")
            return redirect('/register/?tab=register')
        
        rut = rut_sin_formato[:-1] + '-' + rut_sin_formato[-1].upper()

        # ==================== VALIDACIONES ====================
        if not all([username, email, password1, password2, nombre, apellido_paterno, rut]):
            messages.error(request, "Todos los campos obligatorios deben estar completos.")
            return redirect('/register/?tab=register')

        if not re.fullmatch(r'[a-zA-Z0-9]+', username):
            messages.error(request, "El usuario solo puede contener letras y números.")
            return redirect('/register/?tab=register')

        if not re.match(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,}$", email):
            messages.error(request, "Ingresa un correo electrónico válido.")
            return redirect('/register/?tab=register')

        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('/register/?tab=register')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Ese usuario ya está en uso.")
            return redirect('/register/?tab=register')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Ya existe una cuenta con ese correo.")
            return redirect('/register/?tab=register')

        if Perfil.objects.filter(rut=rut).exists():
            messages.error(request, "Este RUT ya está registrado.")
            return redirect('/register/?tab=register')

        try:
            validar_contraseña_fuerte(password1)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return redirect('/register/?tab=register')

        # ==================== CREAR USUARIO Y LOGUEARLO ====================
        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.is_active = False
            user.save()

            # ESTA LÍNEA ES LA QUE HACÍA FALTA: LOGUEAR AL USUARIO
            login(request, user)

            Perfil.objects.create(
                usuario=user,
                nombre=nombre,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno or None,
                rut=rut,
                telefono=telefono or None,
                es_admin=False
            )

            # Generar código
            codigo_obj, _ = CodigoVerificacion.objects.get_or_create(usuario=user)
            codigo_obj.codigo = f"{random.randint(100000, 999999)}"
            codigo_obj.creado_en = timezone.now()
            codigo_obj.expirado = False
            codigo_obj.save()

            # Enviar email
            try:
                send_mail(
                    "Código de verificación - Distribuidora Talagante",
                    f"Hola {username}!\n\nTu código es: {codigo_obj.codigo}\n\nVálido 10 minutos.\n\n¡Gracias por registrarte!",
                    None,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, f"¡Código enviado a {email}!")
            except Exception:
                messages.warning(request, f"Usuario creado. Tu código es: {codigo_obj.codigo}")

            return redirect('verificar_codigo')  # AHORA SÍ TE LLEVA A VERIFICAR

        except Exception as e:
            messages.error(request, "Error inesperado al crear la cuenta.")
            return redirect('/register/?tab=register')

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

    if not carrito or not carrito.itemcarrito_set.exists():
        return render(request, 'core/carrito.html', {'mensaje': 'Tu carrito está vacío'})

    items = carrito.itemcarrito_set.all()
    total = sum(item.cantidad * item.producto.precio for item in items)

    context = {
        'items': items,
        'total': total,
    }
    return render(request, 'core/carrito.html', context)

@login_required
def checkout(request):
    # Carrito más reciente del usuario
    carrito = Carrito.objects.filter(usuario=request.user).order_by('-creado').first()

    if not carrito or not carrito.itemcarrito_set.exists():
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito')

    items = carrito.itemcarrito_set.all()
    total = sum(item.cantidad * item.producto.precio for item in items)

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago', 'transferencia')
        mensaje = request.POST.get('mensaje', '').strip()
        comprobante = request.FILES.get('comprobante')

        with transaction.atomic():
            orden = Orden.objects.create(
                usuario=request.user,
                total=total,
                metodo_pago=metodo_pago,
                mensaje_cliente=mensaje,
                estado='confirmacion' if comprobante or metodo_pago != 'transferencia' else 'pendiente'
            )

            for item in items:
                ItemOrden.objects.create(
                    orden=orden,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio=item.producto.precio
                )

            if comprobante:
                orden.comprobante = comprobante
                orden.save()

            # Vaciar carrito
            items.delete()

        # ==================== WHATSAPP AL ADMIN (56958530495) ====================
        try:
            perfil = request.user.perfil
            nombre_completo = perfil.nombre_completo if perfil else request.user.username
            telefono = perfil.telefono if perfil and perfil.telefono else "No indicado"
        except:
            nombre_completo = request.user.username
            telefono = "No indicado"

        items_txt = ""
        for item in orden.itemorden_set.all():
            subtotal = item.cantidad * item.precio
            items_txt += f"• {item.cantidad}x {item.producto.nombre} → ${subtotal:,}\n"

        mensaje_linea = f"*Mensaje del cliente:*\n{mensaje}" if mensaje else ""
        comprobante_linea = "*Comprobante recibido*" if comprobante else ""

        admin_url = request.build_absolute_uri(f"/admin/core/orden/{orden.id}/change/")

        mensaje_wa = f"""*NUEVA ORDEN #{orden.id}*

*Cliente:* {request.user.username}
*Nombre:* {nombre_completo}
*Teléfono:* {telefono}
*Email:* {request.user.email}

*Productos:*
{items_txt}
*Total:* ${total:,}
*Método:* {orden.get_metodo_pago_display()}
{mensaje_linea}
{comprobante_linea}

Ver orden → {admin_url}""".strip()

        import urllib.parse
        import requests
        wa_url = f"https://wa.me/56958530495?text={urllib.parse.quote(mensaje_wa)}"
        try:
            requests.get(wa_url, timeout=10)
        except:
            pass

        # =========================== EMAILS HERMOSOS ===========================
        try:
            from django.template.loader import render_to_string
            from django.core.mail import EmailMultiAlternatives
            from django.utils.html import strip_tags

            # WhatsApp del local para el cliente
            whatsapp_cliente = f"https://wa.me/56912345678?text=Hola!%20Mi%20orden%20es%20%23{orden.id}%20-%20Total%20%24{total}"

            # Email al cliente
            html_cliente = render_to_string('emails/confirmacion_cliente.html', {
                'usuario': request.user.username,
                'orden_id': orden.id,
                'items': orden.itemorden_set.all(),
                'total': total,
                'metodo_pago': orden.get_metodo_pago_display(),
                'whatsapp_link': whatsapp_cliente,
            })
            email_c = EmailMultiAlternatives(
                f"¡Gracias por tu compra! Orden #{orden.id}",
                strip_tags(html_cliente),
                None,
                [request.user.email]
            )
            email_c.attach_alternative(html_cliente, "text/html")
            email_c.send()

            # Email al admin
            html_admin = render_to_string('emails/nueva_orden_admin.html', {
                'orden_id': orden.id,
                'usuario': request.user.username,
                'nombre_completo': nombre_completo,
                'telefono': telefono,
                'email': request.user.email,
                'fecha': orden.fecha.strftime('%d/%m/%Y %H:%M'),
                'items': orden.itemorden_set.all(),
                'total': total,
                'metodo_pago': orden.get_metodo_pago_display(),
                'mensaje_cliente': mensaje or '',
            })
            email_a = EmailMultiAlternatives(
                f"URGENTE - Nueva orden #{orden.id}",
                strip_tags(html_admin),
                None,
                ['fabriicratos10@gmail.com']
            )
            email_a.attach_alternative(html_admin, "text/html")
            if comprobante:
                email_a.attach(comprobante.name, comprobante.read(), comprobante.content_type)
            email_a.send()

        except Exception as e:
            print("Error enviando emails:", e)

        messages.success(request, f"¡Orden #{orden.id} creada con éxito! Te avisamos por WhatsApp y correo.")
        return redirect('orden_exitosa', orden_id=orden.id)

    # Vista GET
    context = {
        'items': items,
        'total': total,
    }
    return render(request, 'core/checkout.html', context)


@login_required
def orden_exitosa(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id, usuario=request.user)
    return render(request, 'core/orden_exitosa.html', {'orden': orden})

@login_required
def mis_compras(request):
    # 1. Obtener todas las órdenes
    ordenes = Orden.objects.filter(usuario=request.user).order_by('-fecha')

    # 2. CAPTURAR DATOS DEL BUSCADOR (Esto es lo que faltaba)
    busqueda = request.GET.get('q')      
    estado_filtro = request.GET.get('estado')

    # 3. FILTRAR POR NÚMERO (#6 o 6)
    if busqueda:
        busqueda = busqueda.strip()
        if busqueda.isdigit():
            ordenes = ordenes.filter(id=busqueda)
        elif busqueda.startswith('#') and busqueda[1:].isdigit():
            ordenes = ordenes.filter(id=busqueda[1:])
    
    # 4. FILTRAR POR ESTADO
    if estado_filtro:
        ordenes = ordenes.filter(estado=estado_filtro)

    # 5. Calcular subtotales
    for orden in ordenes:
        for item in orden.itemorden_set.all():
            item.subtotal_temp = item.cantidad * item.precio

    context = {
        'ordenes': ordenes,
        'ESTADOS': Orden.ESTADOS, # Vital para el filtro
    }
    return render(request, 'core/mis_compras.html', context)

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
@user_passes_test(is_superuser)
def admin_panel(request):
    estado_filtro = request.GET.get('estado', '')

    # TODAS LAS ÓRDENES SIN FILTRO RARO
    ordenes = Orden.objects.all().select_related('usuario__perfil').prefetch_related('itemorden_set__producto').order_by('-fecha')

    # Si hay filtro específico
    if estado_filtro:
        ordenes = ordenes.filter(estado=estado_filtro)
    # SI NO HAY FILTRO → MOSTRAR TODAS MENOS CANCELADAS Y COMPLETADAS
    else:
        ordenes = ordenes.exclude(estado__in=['cancelado', 'completado'])

    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(ordenes, 25)
    page = request.GET.get('page')
    ordenes = paginator.get_page(page)

    context = {
        'ordenes': ordenes,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'core/admin_panel.html', context)
    
@login_required
@user_passes_test(is_superuser)
def cambiar_estado_pedido(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    
    if request.method == "POST":
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Orden.ESTADOS):
            orden.estado = nuevo_estado
            orden.save()
            
            # Enviar email al cliente (opcional pero pro)
            if orden.usuario.email:
                send_mail(
                    f"Tu pedido #{orden.id} ha cambiado de estado",
                    f"Hola {orden.usuario.username},\n\nTu pedido ahora está en: {orden.get_estado_display()}\n\n¡Gracias por comprar en Distribuidora Talagante!",
                    settings.EMAIL_HOST_USER,
                    [orden.usuario.email],
                    fail_silently=True,
                )
            
            messages.success(request, f"Estado actualizado a {orden.get_estado_display()}")
        else:
            messages.error(request, "Estado inválido")
    
    return redirect('admin_panel')

@login_required
@user_passes_test(is_superuser)
def gestion_pedidos(request):
    estado_filtro = request.GET.get('estado', '')

    # TODAS las órdenes que necesitan atención
    qs = Orden.objects.select_related('usuario', 'usuario__perfil') \
        .prefetch_related('itemorden_set__producto') \
        .order_by('-fecha')

    if estado_filtro and estado_filtro in dict(Orden.ESTADOS):
        qs = qs.filter(estado=estado_filtro)
    else:
        # Excluir solo canceladas y completadas
        qs = qs.exclude(estado__in=['cancelado', 'completado'])

    paginator = Paginator(qs, 25)
    page = request.GET.get('page')
    ordenes = paginator.get_page(page)

    context = {
        'ordenes': ordenes,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'core/gestion_pedidos.html', context)


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

    texto_accion = "añadido" if created else "actualizada"

    messages.success(
        request,
        f'<i class="bi bi-cart-check-fill me-2"></i> '
        f'<strong>{producto.nombre}</strong> { "añadido" if created else "actualizada" } al carrito '
        f'<span class="badge bg-success ms-2 fs-6">{item.cantidad} und</span>',
        extra_tags='safe'
    )

    return redirect('catalogo')

from django.shortcuts import render, redirect
from .models import ItemOrden, Producto # Asegúrate de tener estas importaciones

# ---------------------------------------------------
# SUMAR (VERSIÓN SEGURA)
# ---------------------------------------------------
def sumar_producto(request, item_id):
    print(f"--- INTENTO SUMAR ITEM {item_id} ---")

    # Usamos filter().first() en lugar de get_object_or_404
    # Si no existe, devuelve None (vacío) en vez de error 404
    item = ItemOrden.objects.filter(id=item_id).first()
    
    if item:
        # Solo sumamos si existe y hay stock
        if item.producto.stock > item.cantidad:
            item.cantidad += 1
            item.save()
            print(f"--- NUEVA CANTIDAD: {item.cantidad} ---")
        else:
            print("--- NO HAY MÁS STOCK ---")
    else:
        print("--- ITEM NO ENCONTRADO (Tal vez ya se borró) ---")
    
    return redirect('carrito')

# ---------------------------------------------------
# RESTAR (VERSIÓN SEGURA)
# ---------------------------------------------------
def restar_producto(request, item_id):
    print(f"--- INTENTO RESTAR ITEM {item_id} ---")
    
    item = ItemOrden.objects.filter(id=item_id).first()
    
    if item:
        if item.cantidad > 1:
            item.cantidad -= 1
            item.save()
            print(f"--- RESTADO. NUEVA CANTIDAD: {item.cantidad} ---")
        else:
            item.delete()
            print("--- ELIMINADO POR LLEGAR A 0 ---")
    else:
        print("--- ITEM NO ENCONTRADO ---")
            
    return redirect('carrito')

# ---------------------------------------------------
# ELIMINAR (VERSIÓN SEGURA)
# ---------------------------------------------------
def remove_from_carrito(request, item_id):
    print(f"--- ELIMINANDO ITEM {item_id} ---")
    
    item = ItemOrden.objects.filter(id=item_id).first()
    
    if item:
        item.delete()
        print("--- ELIMINADO ---")
        
    return redirect('carrito')

@login_required
def remove_from_carrito(request, item_id):
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    producto = item.producto
    producto.stock += item.cantidad
    producto.save()
    item.delete()
    return redirect('carrito')


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
@user_passes_test(is_superuser)
def admin_home(request):
    productos_bajo_stock = Producto.objects.filter(stock__lt=10)
    estado_filtro = request.GET.get('estado', '')  # Filtro por estado desde la URL
    ordenes_query = Orden.objects.filter(estado__in=['pendiente', 'confirmacion', 'preparacion'])
    if estado_filtro:
        ordenes_query = ordenes_query.filter(estado=estado_filtro)
    ordenes = ordenes_query.order_by('-fecha')
    paginator = Paginator(ordenes, 10)  # 10 órdenes por página
    page_number = request.GET.get('page')
    ordenes_paginated = paginator.get_page(page_number)

    item_id = request.GET.get('delete_item')
    orden_id = request.GET.get('delete_orden')
    if item_id:
        try:
            item = ItemOrden.objects.get(id=item_id)
            orden = item.orden
            producto = item.producto
            cantidad = item.cantidad
            item.delete()
            producto.stock += cantidad
            producto.save()
            orden.total -= item.cantidad * item.precio
            orden.save()
            messages.success(request, f'Ítem "{producto.nombre}" eliminado de la orden #{orden.id}. Stock restaurado.')
        except ItemOrden.DoesNotExist:
            messages.error(request, 'Ítem no encontrado.')
    elif orden_id:
        try:
            orden = Orden.objects.get(id=orden_id)
            orden.estado = 'cancelado'  # Esto activa el método save para restaurar stock
            orden.save()
            messages.success(request, f'Orden #{orden.id} cancelada y stock restaurado.')
        except Orden.DoesNotExist:
            messages.error(request, 'Orden no encontrada.')
            
    context = {
        'productos_bajo_stock': productos_bajo_stock,
        'ordenes': ordenes_paginated,
        'estado_filtro': estado_filtro,
    }
    return render(request, 'core/admin_home.html', context)

@login_required
@user_passes_test(is_superuser)
def producto_list(request):
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'core/admin_productos.html', {'productos': productos})

@login_required
@user_passes_test(is_superuser)
def producto_create(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado correctamente")
            return redirect('producto_list')
    else:
        form = ProductoForm()
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Crear'})

@login_required
@user_passes_test(is_superuser)
def producto_update(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado correctamente")
            return redirect('producto_list')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'core/producto_form.html', {'form': form, 'action': 'Editar', 'producto': producto})

@login_required
@user_passes_test(is_superuser)
def producto_delete(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente.')
        return redirect('producto_list')
    return render(request, 'core/producto_confirm_delete.html', {'producto': producto})

@login_required
@user_passes_test(is_superuser)  
def orden_detail(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    return render(request, 'core/orden_detail.html', {'orden': orden})

def test_endpoint_view(request):
    response_data = None
    if request.method == 'POST':
        from django.test import Client
        try:
            client = Client()
            response = client.post(reverse('probar_orden'))
            if response.status_code == 201:
                response_data = response.json()
            else:
                response_data = {"error": "Fallo en la solicitud", "detalle": response.content.decode()}
        except Exception as e:
            response_data = {"error": str(e)}
    return render(request, 'core/test_endpoint.html', {'response': response_data})

# Nuevas vistas para los endpoints de API
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Carrito, ItemCarrito, Orden, ItemOrden, User, Producto
from .serializers import OrdenSerializer
from decimal import Decimal

class CrearOrdenView(APIView):
    def post(self, request):
        print("Datos recibidos:", request.data)
        try:
            usuario = request.user if request.user.is_authenticated else User.objects.get_or_create(username='testuser')[0]
        except User.DoesNotExist:
            usuario = User.objects.create(username='testuser')
            usuario.save()

        carrito = Carrito.objects.filter(
            usuario=usuario,
            creado__gte=timezone.now() - timezone.timedelta(minutes=15)
        ).order_by('-creado').first()
        if not carrito:
            print("No se encontró carrito válido")
            return Response({"error": "No se encontró un carrito válido"}, status=status.HTTP_400_BAD_REQUEST)

        items_carrito = ItemCarrito.objects.filter(carrito=carrito)
        if not items_carrito.exists():
            print("Carrito vacío")
            return Response({"error": "El carrito está vacío"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        metodo_pago = data.get('metodo_pago', 'transferencia')
        total = Decimal(str(data.get('total', '0')))

        calculated_total = sum(item.cantidad * item.producto.precio for item in items_carrito)
        print(f"Calculated total: {calculated_total}, Received total: {total}")
        if abs(calculated_total - total) > Decimal('0.01'):
            print("Totales no coinciden")
            return Response({"error": "El total no coincide con los ítems"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            orden = Orden.objects.create(
                usuario=usuario,
                total=total,
                estado='confirmacion',
                metodo_pago=metodo_pago
            )
            for item in items_carrito:
                ItemOrden.objects.create(
                    orden=orden,
                    producto=item.producto,
                    cantidad=item.cantidad,
                    precio=item.producto.precio
                )
            items_carrito.delete()

        serializer = OrdenSerializer(orden)
        whatsapp_link = serializer.data['whatsapp_link']
        print(f"WhatsApp link: {whatsapp_link}")

        return Response({"whatsapp_link": whatsapp_link}, status=status.HTTP_200_OK)
    


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Orden
from django.core.mail import send_mail
from django.conf import settings

def is_superuser(user):
    return user.is_superuser

def test_correo(request):
    try:
        from django.core.mail import send_mail
        send_mail(
            subject="PRUEBA - CORREO DESDE DISTRIBUIDORA",
            message="Si ves esto, ¡EL CORREO FUNCIONA PERFECTO!",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=['valeveraleiva@gmail.com'],  # ← TU CORREO
            fail_silently=False,
        )
        return HttpResponse("<h1>CORREO ENVIADO. REVISA TU BANDEJA (y spam)</h1>")
    except Exception as e:
        return HttpResponse(f"<h1>ERROR: {e}</h1>")
    

@login_required
@user_passes_test(lambda u: u.is_superuser)
def gestion_estados(request):
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '')

    # 1. Obtener todas las órdenes ordenadas
    ordenes = Orden.objects.select_related('usuario', 'usuario__perfil') \
                           .prefetch_related('itemorden_set__producto') \
                           .order_by('-fecha')

    # 2. Aplicar Filtros (Búsqueda y Estado)
    if busqueda:
        ordenes = ordenes.filter(
            Q(id__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__perfil__nombre__icontains=busqueda) |
            Q(usuario__perfil__apellido_paterno__icontains=busqueda)
        )

    if estado_filtro:
        ordenes = ordenes.filter(estado=estado_filtro)

    # 3. Lógica POST (Cambio de estado rápido)
    if request.method == 'POST':
        orden_id = request.POST.get('orden_id')
        nuevo_estado = request.POST.get('estado')

        try:
            orden = Orden.objects.get(id=orden_id)
            estado_anterior = orden.get_estado_display()
            orden.estado = nuevo_estado
            orden.save()

            # Mensaje de WhatsApp y Correo (Tu lógica original)
            mensaje_wa = f"Hola! Mi pedido es el #{orden.id} - Estado: {orden.get_estado_display()}"
            whatsapp_link = f"https://wa.me/56949071013?text={urllib.parse.quote(mensaje_wa)}"

            if orden.usuario.email:
                try:
                    html_email = render_to_string('emails/cambio_estado.html', {
                        'cliente': orden.usuario.perfil.nombre_completo or orden.usuario.username,
                        'pedido_id': orden.id,
                        'estado_anterior': estado_anterior,
                        'nuevo_estado': orden.get_estado_display(),
                        'total': orden.total,
                        'whatsapp_link': whatsapp_link,
                    })

                    email = EmailMultiAlternatives(
                        subject=f"¡Tu pedido #{orden.id} ha cambiado de estado!",
                        body="Tu pedido ha cambiado de estado.",
                        from_email=settings.EMAIL_HOST_USER,
                        to=[orden.usuario.email]
                    )
                    email.attach_alternative(html_email, "text/html")
                    email.send()
                except Exception as e:
                    print(f"ERROR CORREO: {e}")

            return JsonResponse({'success': True, 'nuevo_estado': orden.get_estado_display()})

        except Exception as e:
            print(f"ERROR GENERAL: {e}")
            return JsonResponse({'success': False})

    # --- 4. PAGINACIÓN (AQUÍ ESTÁ EL CAMBIO) ---
    # Esto divide la lista 'ordenes' en páginas de 20 elementos
    paginator = Paginator(ordenes, 20) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'ordenes': page_obj,  # Pasamos el objeto paginado, no la lista completa
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'estados_choices': Orden.ESTADOS,
    }
    return render(request, 'core/gestion_estados.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def pedidos_despacho(request):
    ordenes = Orden.objects.select_related('usuario', 'usuario__perfil') \
                           .prefetch_related('itemorden_set__producto') \
                           .filter(estado__in=['despacho', 'preparacion']) \
                           .order_by('-fecha')
    
    context = {'ordenes': ordenes, 'titulo': 'Pedidos en Despacho / Listos para Retiro'}
    return render(request, 'core/pedidos_despacho.html', context)  # ← NOMBRE CORRECTO


@login_required
@user_passes_test(lambda u: u.is_superuser)
def pedidos_finalizados(request):
    ordenes = Orden.objects.select_related('usuario', 'usuario__perfil') \
                           .prefetch_related('itemorden_set__producto') \
                           .filter(estado__in=['completado', 'cancelado']) \
                           .order_by('-fecha')
    
    context = {'ordenes': ordenes, 'titulo': 'Pedidos Finalizados'}
    return render(request, 'core/pedidos_finalizados.html', context)  # ← NOMBRE CORRECTO

@login_required
@user_passes_test(is_superuser)
def update_orden_status(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Orden.ESTADOS):
            orden.estado = nuevo_estado
            orden.save()
            messages.success(request, f'Estado cambiado a {orden.get_estado_display()}')
        else:
            messages.error(request, 'Estado inválido')
        
        # ESTA ES LA ÚNICA LÍNEA QUE IMPORTA
        return redirect('/panel/')   # ← AHORA SÍ VUELVE AL PANEL BONITO
        
    context = {'orden': orden}
    return render(request, 'core/update_orden_status.html', context)


#Verificación correo electronico seguro
def enviar_codigo_verificacion(user):
    codigo_obj, _ = CodigoVerificacion.objects.get_or_create(usuario=user)
    codigo_obj.codigo = f"{random.randint(100000, 999999)}"
    codigo_obj.creado_en = timezone.now()
    codigo_obj.expirado = False
    codigo_obj.save()

    send_mail(
        "Tu código de verificación - Distribuidora Talagante",
        f"Hola {user.username}!\n\nTu código es:\n\n{codigo_obj.codigo}\n\nVálido por 10 minutos.\n\n¡Gracias!",
        None,
        [user.email],
        fail_silently=False,
    )

from django.http import JsonResponse
from .models import Producto

def api_buscar_por_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    
    if not codigo:
        return JsonResponse({'error': 'Código vacío'}, status=400)

    try:
        producto = Producto.objects.get(codigo_barra=codigo)
        return JsonResponse({
            'encontrado': True,
            'id': producto.id,
            'nombre': producto.nombre,
            'stock_actual': producto.stock,
            'mensaje': 'Producto encontrado. ¿Agregar stock?'
        })
    except Producto.DoesNotExist:
        return JsonResponse({
            'encontrado': False,
            'codigo_escaneado': codigo,
            'mensaje': 'Producto nuevo. Redirigiendo a creación...'
        })
    
def escaneo_rapido(request):
    if request.method == "POST":
        codigo = request.POST.get("codigo_barras", "").strip()
        cantidad_str = request.POST.get("cantidad", "1")
        
        try:
            cantidad = Decimal(cantidad_str)
        except:
            messages.error(request, "Cantidad inválida")
            return redirect('escaneo_rapido')

        if not codigo:
            messages.error(request, "No se recibió código")
            return redirect('escaneo_rapido')

        # 1. ¿Ya existe el producto?
        try:
            producto = Producto.objects.get(codigo_barras=codigo)
            producto.agregar_stock(cantidad)
            messages.success(request, f"✔ {producto.nombre} +{cantidad} {producto.unidad_medida}")
            return redirect('escaneo_rapido')

        # 2. No existe → buscar en OpenFoodFacts
        except Producto.DoesNotExist:
            url = f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json"
            try:
                r = requests.get(url, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == 1:
                        p = data["product"]
                        nombre = (p.get("product_name_es") or p.get("product_name") or "Sin nombre")[:200]
                        categoria = p.get("categories", "")[:50]

                        nuevo = Producto.objects.create(
                            codigo_barras=codigo,
                            nombre=nombre,
                            categoria=categoria,
                            precio_por_unidad=0,
                            stock=cantidad,
                            unidad_medida=Producto.UnidadMedida.KG if "kg" in nombre.lower() else Producto.UnidadMedida.UN
                        )
                        messages.success(request, f"Producto nuevo creado: {nombre}")
                        return redirect('editar_precio_rapido', nuevo.id)
            except:
                pass  # si falla OpenFoodFacts, seguimos al formulario manual

                        # 3. Todo falló → formulario rápido
            if request.POST.get('stock_inicial'):  # viene del formulario rápido
                form = ProductoRapidoForm(request.POST)
                if form.is_valid():
                    nuevo = form.save(commit=False)
                    nuevo.codigo_barras = codigo
                    nuevo.stock = Decimal(request.POST.get('stock_inicial', cantidad))
                    nuevo.save()
                    messages.success(request, f"Producto creado: {nuevo.nombre}")
                    return redirect('escaneo_rapido')
            else:
                form = ProductoRapidoForm(initial={
                    'nombre': 'Producto nuevo',
                    'precio_por_unidad': 0,
                })

            return render(request, 'core/producto_rapido.html', {
                'form': form,
                'codigo': codigo,
                'cantidad': cantidad
            })

    return render(request, 'core/escaneo_rapido.html')