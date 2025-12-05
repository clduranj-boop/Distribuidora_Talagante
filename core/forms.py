# core/forms.py
from django import forms
from .models import Producto
from decimal import Decimal


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_barras', 'nombre', 'categoria', 'precio', 'stock',
            'unidad_medida', 'tamano_paquete', 'producto_hijo',
            'fecha_vencimiento', 'imagen', 'activo'
        ]
        widgets = {
           'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Precio en pesos'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Frutas, Bebidas...'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'tamano_paquete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '1'}),
            'producto_hijo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'precio': 'Precio (CLP)',
            'tamano_paquete': 'Tamaño del paquete (ej: 12 unid por caja)',
            'producto_hijo': 'Producto contenido (opcional)',
        }

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Solo al CREAR (no al editar)
            if not self.instance.pk:
                self.fields['codigo_barras'].required = False
                self.fields['codigo_barras'].help_text = "Se generará automáticamente (ej: MAN-00123)"
                self.fields['codigo_barras'].widget.attrs['placeholder'] = "Dejar vacío para autogenerar"

            # Al editar → readonly
            else:
                self.fields['codigo_barras'].widget.attrs['readonly'] = True

    def clean_codigo_barras(self):
        codigo = self.cleaned_data.get('codigo_barras')
        instance = getattr(self, 'instance', None)
        
        # Si estamos CREANDO y el campo está vacío → generamos uno
        if not instance.pk and not codigo:
            # Generamos código tipo MAN-00001, MAN-00002...
            ultimo = Producto.objects.filter(
                codigo_barras__regex=r'^MAN-\d+$'
            ).order_by('-codigo_barras').first()
            
            if ultimo:
                num = int(ultimo.codigo_barras.split('-')[1]) + 1
            else:
                num = 1
            return f"MAN-{num:05d}"  # MAN-00001, MAN-00002...
        
        return codigo

    def clean_precio(self):
        precio = self.cleaned_data['precio']
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock
    
    


class EscaneoEntradaForm(forms.Form):
    codigo_barras = forms.CharField(max_length=50, widget=forms.HiddenInput())
    cantidad = forms.DecimalField(
        label="Cantidad",
        min_value=Decimal('0.001'),
        decimal_places=3,
        initial=Decimal('1.000'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'step': 'any',
            'autofocus': True,
            'placeholder': 'Ej: 10, 12.5, 1',
            'style': 'font-size: 2rem; height: 80px;'
        })
    )


class ProductoRapidoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'unidad_medida', 'fecha_vencimiento']  # ← precio, no precio_por_unidad
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control form-control-lg'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '1', 'placeholder': 'Precio en pesos'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'precio': 'Precio (CLP)',
        }


class ConfigurarPaqueteForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['tamano_paquete', 'producto_hijo']
        widgets = {
            'tamano_paquete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'producto_hijo': forms.Select(attrs={'class': 'form-select'}),
        }