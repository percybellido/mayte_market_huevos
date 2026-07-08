from django.utils import timezone
from datetime import timedelta
from applications.customers.models import Cliente
from datetime import datetime
from django.db.models import Sum, DecimalField, F
from applications.product.models import Producto

from .models import Venta, VentaDetalle, CarShop, Pago, PagoVenta

from django.db import transaction

def generar_nro_factura():
    hoy = datetime.now()
    año = hoy.year
    mes = hoy.month
    prefijo = f"{año}-{mes:05d}"
    
    ultima = Venta.objects.filter(Venta_NroFact__startswith=prefijo).order_by('Venta_NroFact').last()

    if ultima and ultima.Venta_NroFact:
        try:
            ultimo_num = int(ultima.Venta_NroFact.split('-')[-1])
        except (ValueError, IndexError):
            ultimo_num = 0
        nuevo_num = ultimo_num + 1
    else:
        nuevo_num = 1

    return f"{prefijo}-{nuevo_num:06d}"

def aplicar_saldo_a_favor(cliente, venta):
    """
    Aplica el saldo a favor del cliente como pago automático.
    """
    saldo = cliente.saldo_pendiente   # puede ser negativo

    if saldo >= 0:
        return  # no hay saldo a favor

    saldo_a_favor = abs(saldo)

    
    monto_a_usar = min(saldo_a_favor, venta.Venta_Total)

    PagoVenta.objects.create(
        venta=venta,
        monto_pagado=monto_a_usar,
        descripcion="Aplicación automática de saldo a favor"
    )

    cliente.actualizar_saldo()

def procesar_venta(self, **params_venta):

    # recupera la lista de productos en el carrito
    productos_en_car=CarShop.objects.all()

    if productos_en_car.exists() > 0:

        #Crea el objeto venta
        cliente=Cliente.objects.get(id=params_venta['cliente_id'])

        venta=Venta.objects.create(
            Venta_Fecha=timezone.now(),
            Venta_CliId=cliente,
            Venta_cantidad=0,
            Venta_NroFact=generar_nro_factura(),
            Venta_Total=0,
        )

        ventas_detalle=[]
        total=0
        productos_en_venta=[]
        cantidad_total=0

        for producto_car in productos_en_car:
            subtotal = producto_car.cantidad * producto_car.precio
            venta_detalle=VentaDetalle(
                producto=producto_car.producto,
                venta=producto_car.VD_VentasId,
                cantidad=producto_car.VD_Cantidad,
                precio_venta=producto_car.precio_venta
            )
            producto=producto_car.producto
            ventas_detalle.append(venta_detalle)
            productos_en_venta.append(producto)
        venta.save()
        VentaDetalle.objects.bulk_create(ventas_detalle)
        #Completada la vente, eliminamos productos del Carrito
        productos_en_car.delete()
        return venta
    else:
        return None
    
def registrar_pago(cliente, total_pagado, metodo_pago):
    ventas_pendientes = Venta.objects.filter(
        Venta_CliId=cliente,
        status='confirmed'
    ).order_by('Venta_Fecha')

    with transaction.atomic():
        pago = Pago.objects.create(
            cliente=cliente,
            total_pagado=total_pagado,
            metodo_pago=metodo_pago
        )
        
        restante = total_pagado
        for venta in ventas_pendientes:
            total_pagado_en_venta = venta.pagos_aplicados.aggregate(total=Sum('monto_pagado'))['total'] or 0
            saldo = venta.Venta_Total - total_pagado_en_venta

            if saldo <= 0:
                continue

            abono = min(restante, saldo)
            PagoVenta.objects.create(
                pago=pago,
                venta=venta,
                monto_pagado=abono
            )

            restante -= abono
            if restante <= 0:
                break

        cliente.actualizar_saldo()
        
        #if restante > 0:
            # Guardamos el excedente como saldo a favor (saldo negativo)
            #cliente.saldo -= restante
            #cliente.save(update_fields=["saldo"])
        #else:
            #cliente.actualizar_saldo()
    

def ganancia_total_por_dia(fecha):

    utilidad = VentaDetalle.objects.filter(
        VD_VentasId__Venta_Fecha__date=fecha,
        VD_VentasId__status='confirmed'
    ).aggregate(
        total=Sum(
            (F('VD_Precio') - F('producto__precio_compra')) * F('VD_Cantidad'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )['total'] or 0

    return utilidad

def ganancias_ultimos_dias(dias=7):
    """Devuelve una lista con la ganancia de los últimos 'dias' días."""
    hoy = timezone.now().date()
    datos = []

    for i in range(dias):
        fecha = hoy - timedelta(days=i)
        utilidad = ganancia_total_por_dia(fecha)
        datos.append({
            'fecha': fecha,
            'ganancia': utilidad
        })

    return datos[::-1] 

