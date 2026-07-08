from decimal import Decimal
from django.db import models
from django.db.models import Sum, F, FloatField, DecimalField
from django.conf import settings
from applications.product.models import Producto
from applications.customers.models import Cliente
from applications.users.models import User
from .managers import VentaManagers, CarShopManager

# Create your models here.
class Venta(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Anulada'),
    )
    
    Venta_Fecha=models.DateTimeField('Fecha de Venta')
    Venta_CliId=models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='cliente_venta', null=False)
    Venta_cantidad=models.DecimalField('Cantidad de Producto', max_digits=10, decimal_places=2, default=0)
    Venta_NroFact = models.CharField('Número de Boleta', max_length=20, null=True, blank=True)
    Venta_Total=models.DecimalField('Total', max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='cajero',
        related_name="user_venta",
    )

    @property
    def ganancia_total(self):
        if self.status != 'confirmed':
            return Decimal("0.00")

        return self.detalles.aggregate(
            total=Sum(
                (F('VD_Precio') - F('producto__precio_compra')) * F('VD_Cantidad'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )['total'] or Decimal("0.00")


    @property
    def total(self):
        return sum((d.subtotal for d in self.detalles.all()), Decimal('0.00'))

    objects=VentaManagers()

    class Meta:
        verbose_name='Ventas'
        ordering = ['-created']
        indexes = [
        models.Index(fields=['user', 'Venta_Fecha']),
        models.Index(fields=['Venta_CliId']),
        models.Index(fields=['status']),
    ]

    def __str__(self):
        return str(self.Venta_CliId)
    
    @property
    def tiene_pagos_reales(self):
        total = self.pagos_aplicados.aggregate(
            total=Sum('monto_pagado')
        )['total'] or Decimal('0.00')
        return total > 0
    
class VentaDetalle(models.Model):
    VD_VentasId=models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles" )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name='producto',
        related_name='product_sale'
    )
    VD_Cantidad = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    VD_Precio=models.DecimalField('Precio Venta', max_digits=10, decimal_places=2)
    VD_precio_compra=models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name='Detalle de Ventas'
        ordering=['VD_VentasId']
        
    @property
    def subtotal(self):
        return self.VD_Cantidad * self.VD_Precio
    
    def __str__(self):
        return str(self.VD_VentasId)+'--'+str(self.VD_Cantidad)+'--'+str(self.VD_Precio)

class MetodosPago(models.Model):
    description=models.CharField('Metodos Pago', max_length=50, null=True)
    status=models.IntegerField(null=True, default=1)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name='Metodos de Pago'

    def __str__(self):
        return self.description

class Pago(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.ForeignKey(MetodosPago, on_delete=models.SET_NULL, null=True)
    saldo_despues = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # 👈 nuevo campo

    def __str__(self):
        return f"Pago de {self.cliente} - S/ {self.total_pagado}"

class PagoVenta(models.Model):
    pago = models.ForeignKey(Pago, on_delete=models.CASCADE, related_name='detalle_ventas')
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos_aplicados')
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)

    
    class Meta:
        unique_together = ('pago', 'venta')

    def __str__(self):
        return f"S/ {self.monto_pagado} para venta #{self.venta.id}"
    
class HistorialSaldo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="historial_saldos")
    fecha = models.DateTimeField(auto_now_add=True)
    saldo = models.DecimalField(max_digits=10, decimal_places=2)
    pago = models.ForeignKey("Pago", on_delete=models.SET_NULL, null=True, blank=True)
    venta = models.ForeignKey("Venta", on_delete=models.SET_NULL, null=True, blank=True)  # 👈 nuevo campo

    def __str__(self):
        return f"{self.cliente.nombre} - Saldo: {self.saldo} ({self.fecha.strftime('%Y-%m-%d %H:%M')})"



class CarShop(models.Model):
    """Modelo que representa a un carrito de compras"""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name='producto',
        related_name='product_car'
    )

    cliente = models.ForeignKey(
    Cliente,
    on_delete=models.CASCADE,
    verbose_name='Cliente',
    null=True,
    blank=True
    )
    cantidad = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0
    )
    user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    null=True,      # << IMPORTANTE
    blank=True,     # << IMPORTANTE
)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    objects=CarShopManager()
    
    class Meta:
        verbose_name = 'Carrito de compras'
        verbose_name_plural = 'Carrito de compras'
        ordering = ['-created']

    def __str__(self):
        return str(self.product.name)
