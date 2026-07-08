from decimal import Decimal
from django import forms
from applications.product.models import Producto
from applications.customers.models import Cliente
from .models import Pago, MetodosPago
from .models import Venta

class VentaForm(forms.Form):

    # Cliente (solo para el primer ingreso)
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        required=True,
        label="Cliente",
        widget=forms.Select(attrs={"class": "form-select select-cliente"})
    )

    # Producto (solo se usa en el primer ingreso)
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(disponible=True),
        required=True,
        label="Producto",
        widget=forms.Select(attrs={"class": "form-select select-producto"})
    )

    # Cantidad / peso (SIEMPRE requerido)
    cantidad = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        required=True,
        min_value=Decimal("0.01"),
        label="Peso / Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Ingrese peso / cantidad",})
    )

    # Precio unitario (solo en primer ingreso)
    precio_unitario = forms.DecimalField(
        max_digits=7,
        decimal_places=2,
        required=False,   # <- requerido para que no falle cuando el campo desaparece
        min_value=Decimal("0.01"),
        label="Precio unitario (opcional)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Precio unitario (S/)",})
    )

    # -------------------------------------------------------
    # VALIDACIONES OPTIMIZADAS (solo lo estrictamente necesario)
    # -------------------------------------------------------

    def __init__(self, *args, **kwargs):
        """
        Ajuste dinámico:
        - si en AddCarView ya existe producto/precio en sesión,
          estos campos desaparecerán en get_form()
        - este __init__ evita errores de required=True
        """
        self.producto_fijado = kwargs.pop("producto_fijado", False)
        self.precio_fijado = kwargs.pop("precio_fijado", False)

        super().__init__(*args, **kwargs)

        # Si AddCarView eliminó los campos, aseguramos que no sean required
        if self.producto_fijado:
            self.fields["producto"].required = False

        if self.precio_fijado:
            self.fields["precio_unitario"].required = False

    # -------------------------
    def clean_precio_unitario(self):
        precio = self.cleaned_data.get("precio_unitario")

        # Si en esta etapa no existe el campo → no validar
        if self.precio_fijado:
            return precio

        if precio in (None, ""):
            return None

        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que cero.")

        return precio

    # -------------------------
    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]

        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")

        return cantidad


    
class PagoForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Cliente",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    total_pagado = forms.DecimalField(
        label="Monto del Pago",
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    metodo_pago = forms.ModelChoiceField(
        queryset=MetodosPago.objects.all(),
        label="Método de Pago",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class AbonoForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Cliente",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    monto = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Monto a abonar",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese monto del abono'
        })
    )
    metodo_pago = forms.ModelChoiceField(
        queryset=MetodosPago.objects.all(),
        label="Método de Pago",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
