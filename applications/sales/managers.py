from django.db import models
from datetime import timedelta
from django.utils.timezone import now
# django
from django.utils import timezone

from django.db.models import Sum

from django.db.models import Q, Sum, F, FloatField, ExpressionWrapper

class VentaQuerySet(models.QuerySet):

    def activas(self):
        return self.filter(status='confirmed')

    def anuladas(self):
        return self.filter(status='cancelled')


    
class VentaManagers(models.Manager.from_queryset(VentaQuerySet)):
            
    def listar_ventas(self):
        fecha_inicio = now() - timedelta(days=30)
        return (
            self.filter(
                status='confirmed',
                Venta_Fecha__gte=fecha_inicio
            )
            .select_related('Venta_CliId', 'user')
            .order_by('-Venta_Fecha')
        )

    def total_ventas(self):
        return self.aggregate(
            total=Sum('amount')
        )['total']
    
    def ventas_en_fecha(self, date_start, date_end):
        return self.filter(
            date_sale__range=(date_start, date_end),
        ).order_by('-date_sale')
    
class VentaDetalleManager(models.Manager):

    def detalle_por_venta(self, id_venta):
        return self.filter(
            sale__id=id_venta
        )

class CarShopManager(models.Manager):

    def total_cobrar(self):
        consulta=self.aggregate(
            total=Sum(
                F('cantidad')*F('precio'),
                output_field=FloatField()
            ),
        )
        if consulta['total']:
            return consulta['total']
        else:
            return 0
        
    def ganancia(self):
        utilidad = self.aggregate(
            total=Sum(
                (F('precio') - F('producto__precio_compra')) * F('cantidad'),
                output_field=FloatField()
            )
        )
        return utilidad['total'] or 0
