from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.views.generic import ListView, TemplateView, DetailView
from django.db.models import Q
from .models import Cliente
from applications.sales.models import Pago, HistorialSaldo, VentaDetalle

# Create your views here.
class ClienteView(TemplateView):
    template_name='customers/clientes.html'

class ListClientes(ListView):
    context_object_name='lista_clientes'
    template_name='customers/lista_clientes.html'
    paginate_by=10

    def get_queryset(self):
        palabra_clave=self.request.GET.get('kword', '')
        return Cliente.objects.buscar_cliente(palabra_clave)
    
class HistorialVentasCliente(DetailView):
    model = Cliente
    template_name = 'customers/historial_cliente.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # mostrar solo las 20 ventas más recientes
        context['ultimas_ventas'] = (
        self.object.cliente_venta
        .filter(status='confirmed')   # 🔥 CLAVE
        .order_by('-Venta_Fecha')[:8]
    )
        return context

    

class HistorialClienteView(ListView):
    model = HistorialSaldo
    template_name = "customers/historial_pagos.html"
    context_object_name = "movimientos"
    paginate_by=10

    
    def get_queryset(self):
        return (
            HistorialSaldo.objects
            .filter(cliente_id=self.kwargs["pk"])
            .filter(Q(venta__isnull=True) | Q(venta__status='confirmed'))
            .select_related("venta", "pago")  # 👈 optimización
            .order_by("-fecha")[:50]
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = get_object_or_404(Cliente, id=self.kwargs["pk"])
        context["cliente"] = cliente

        # 🔹 Ganancia total acumulada (todas las ventas del cliente)
        ganancia_total = (
            VentaDetalle.objects
            .filter(VD_VentasId__Venta_CliId=self.kwargs["pk"])
            .aggregate(
                total=Sum(
                    (F('VD_Precio') - F('VD_precio_compra')) * F('VD_Cantidad'),
                    output_field=FloatField()
                )
            )['total'] or 0
        )
        context["ganancia_acumulada"] = ganancia_total

        return context

from django.db.models import Sum, F, FloatField
from applications.sales.models import Venta

class HistorialClienteUtilidad(ListView):
    model = Venta
    template_name = 'customers/cliente_utilidad.html'
    context_object_name = "ventas"
    paginate_by=10

    def get_queryset(self):
        cliente = Cliente.objects.get(pk=self.kwargs["pk"])
        return (
            Venta.objects.filter(Venta_CliId=cliente)
            .annotate(
                utilidad_total=Sum(
                    (F('detalles__VD_Precio') - F('detalles__VD_precio_compra')) * F('detalles__VD_Cantidad'),
                    output_field=FloatField()
                ),
                monto_total=Sum(
                    F('detalles__VD_Precio') * F('detalles__VD_Cantidad'),
                    output_field=FloatField()
                )
            )
            .order_by('-Venta_Fecha')[:20]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = Cliente.objects.get(pk=self.kwargs["pk"])
        context["cliente"] = cliente

        # 🔹 Utilidad acumulada de todas las ventas
        utilidad_acumulada = (
            self.get_queryset().aggregate(total=Sum('utilidad_total'))['total'] or 0
        )
        context["utilidad_acumulada"] = utilidad_acumulada
        return context


    


