from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, View, DeleteView, DetailView, TemplateView
from django.views.generic.edit import FormView
from django.db.models import F, Sum
from django.contrib import messages
from applications.customers.models import Cliente
from applications.product.models import Producto
from applications.users.mixins import VentasPermisoMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils.timezone import now

from .models import Venta, VentaDetalle, CarShop, PagoVenta, Pago, HistorialSaldo
from .forms import VentaForm, PagoForm, AbonoForm
from .functions import procesar_venta, ganancia_total_por_dia, ganancias_ultimos_dias
from decimal import Decimal

from .functions import registrar_pago, aplicar_saldo_a_favor


from django.db import transaction

class AddCarView(VentasPermisoMixin, FormView):
    template_name = 'sales/index.html'
    form_class = VentaForm
    success_url = '.'

    # ============================================================
    # 0. Reset automático SOLO cuando empieza un nuevo proceso
    # ============================================================
    def dispatch(self, request, *args, **kwargs):

        # Si el carrito está vacío → nuevo proceso → resetear solo estos valores
        carrito_vacio = not CarShop.objects.filter(user=request.user).exists()

        if carrito_vacio:
            request.session.pop('cliente_id', None)
            request.session.pop('venta_producto_id', None)
            request.session.pop('venta_precio', None)

        return super().dispatch(request, *args, **kwargs)

    # ============================================================
    # 1. Ajustar formulario según lo que ya se eligió
    # ============================================================
    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Si ya hay cliente seleccionado → ocultarlo
        if 'cliente_id' in self.request.session:
            form.fields.pop('cliente', None)

        # Si ya hay producto y precio fijo → ocultarlos
        if 'venta_producto_id' in self.request.session:
            form.fields.pop('producto', None)
            form.fields.pop('precio_unitario', None)

        return form

    # ============================================================
    # 2. Contexto
    # ============================================================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        carrito = CarShop.objects.filter(user=self.request.user).select_related("producto")

        context["productos"] = carrito

        context["total_cobrar"] = carrito.aggregate(
            total=Sum(F("cantidad") * F("precio"))
        )["total"] or 0

        context["ganancia"] = carrito.aggregate(
            gan=Sum((F("precio") - F("producto__precio_compra")) * F("cantidad"))
        )["gan"] or 0

        ultima_venta=None

        ultima_venta_id = self.request.session.get('ultima_venta_id')

        if ultima_venta_id:
            context['ultima_venta'] = Venta.objects.filter(
                id=ultima_venta_id,
                status='confirmed'
            ).first()


        # Producto seleccionado una sola vez
        prod_id = self.request.session.get("venta_producto_id")
        if prod_id:
            context["producto_seleccionado"] = Producto.objects.filter(id=prod_id).first()
            context["precio_fijo"] = self.request.session.get("venta_precio")

        # Cliente seleccionado
        cliente_id = self.request.session.get("cliente_id")
        context["cliente"] = Cliente.objects.filter(id=cliente_id).first()

        

        

        return context

    # ============================================================
    # 3. Registrar cada peso como línea independiente
    # ============================================================
    def form_valid(self, form):
        with transaction.atomic():

            # Cliente (solo una vez)
            cliente_id = self.request.session.get("cliente_id")
            if not cliente_id:
                cliente = form.cleaned_data["cliente"]
                self.request.session["cliente_id"] = cliente.id
            else:
                cliente = Cliente.objects.get(id=cliente_id)

            # Producto y precio (solo una vez)
            if "venta_producto_id" not in self.request.session:
                producto = form.cleaned_data["producto"]
                precio_unitario = form.cleaned_data["precio_unitario"]
                self.request.session["venta_producto_id"] = producto.id
                self.request.session["venta_precio"] = float(precio_unitario)
            else:
                producto = Producto.objects.get(
                    id=self.request.session["venta_producto_id"]
                )
                precio_unitario = self.request.session["venta_precio"]

            # Cada peso es una fila
            cantidad = form.cleaned_data["cantidad"]

            CarShop.objects.create(
                user=self.request.user,
                producto=producto,
                cliente=cliente,
                cantidad=cantidad,
                precio=precio_unitario,
            )

            messages.success(
                self.request,
                f"{producto.nombre} — peso {cantidad} añadido."
            )

        return super().form_valid(form)
    
class AddPesoAjaxView(VentasPermisoMixin, View):
    def post(self, request):
        try:
            cantidad = Decimal(request.POST.get("cantidad"))
            producto_id = request.session.get("venta_producto_id")
            cliente_id = request.session.get("cliente_id")
            precio = Decimal(request.session.get("venta_precio"))

            if not all([cantidad, producto_id, cliente_id, precio]):
                return JsonResponse({"ok": False, "error": "Datos incompletos"})

            producto = Producto.objects.get(id=producto_id)
            cliente = Cliente.objects.get(id=cliente_id)

            item = CarShop.objects.create(
                user=request.user,
                producto=producto,
                cliente=cliente,
                cantidad=cantidad,
                precio=precio
            )

            # 🔹 SUBTOTAL (clave para que no reviente el JS)
            subtotal = cantidad * precio

            total = CarShop.objects.filter(user=request.user).aggregate(
                total=Sum(F("cantidad") * F("precio"))
            )["total"] or Decimal("0.00")

            return JsonResponse({
                "ok": True,
                "id": item.id,
                "cantidad": float(item.cantidad),
                "precio": float(item.precio),
                "subtotal": float(subtotal),   # 👈 CLAVE
                "total": float(total),
            })

        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)})
    
class CarShopAddView(VentasPermisoMixin, View):
    """ aumenta en 1 la cantidad en un carshop """

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')

        updated = CarShop.objects.filter(id=pk).update(cantidad=F('cantidad') + 1)

        if not updated:
            messages.error(request, "Producto no encontrado en el carrito.")

        return HttpResponseRedirect(reverse('venta_app:venta-index'))
    
class CarShopUpdateView(VentasPermisoMixin, View):
    """ quita en 1 la cantidad en un carshop """

    def post(self, request, *args, **kwargs):
        car = CarShop.objects.get(id=self.kwargs['pk'])
        if car.cantidad > 1:
            car.cantidad = car.cantidad - 1
            car.save()
        #
        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )

class CarShopDeleteView(VentasPermisoMixin, DeleteView):
    model = CarShop
    success_url = reverse_lazy('venta_app:venta-index')

class CarShopDeleteAll(VentasPermisoMixin, View):
    
    def post(self, request, *args, **kwargs):
        #
        CarShop.objects.filter(user=request.user).delete()
        #

        self.request.session.pop('cliente_id', None)

        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )
class CarShopDeleteAjaxView(VentasPermisoMixin, View):
    def post(self, request):
        item_id = request.POST.get("id")

        CarShop.objects.filter(
            id=item_id,
            user=request.user
        ).delete()

        total = CarShop.objects.filter(
            user=request.user
        ).aggregate(
            total=Sum(F("cantidad") * F("precio"))
        )["total"] or Decimal("0.00")

        return JsonResponse({
            "ok": True,
            "total": float(total)
        })
    
class ProcesoVentaSimpleView(VentasPermisoMixin, View):
    """ Procesa una venta simple """

    def post(self, request, *args, **kwargs):
        cliente = request.POST.get('cliente_id')  # El id del cliente debe venir en el POST
        if not cliente:
            return HttpResponseRedirect(reverse('venta_app:venta-index'))
        #
        procesar_venta(
            self=self,
            user=self.request.user,
        )
        #
        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )


def ventas(request):
    return render(request, 'sales/ventas.html')

class ListVentas(ListView):
    context_object_name='lista_ventas'
    template_name='sales/lista_ventas.html'
    paginate_by=8
    ordering=['Venta_Fecha']

    def get_queryset(self):
        return Venta.objects.listar_ventas()
    
class RegistrarPagoView(FormView):
    template_name = 'sales/registrar_pago.html'
    form_class = PagoForm
    success_url = reverse_lazy('venta_app:lista-ventas')

    def form_valid(self, form):
        cliente=form.cleaned_data['cliente']
        registrar_pago(
            cliente=cliente,
            total_pagado=form.cleaned_data['total_pagado'],
            metodo_pago=form.cleaned_data['metodo_pago']
        )

       
        return super().form_valid(form)
    
    
    
class RegistrarAbonoView(FormView):
    template_name = 'sales/registrar_abono.html'
    form_class = AbonoForm
    success_url = reverse_lazy('venta_app:venta-index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente_id = self.kwargs.get('cliente_id')

        if cliente_id:
            context['cliente_seleccionado'] = Cliente.objects.get(id=cliente_id)

        return context
    
    def get_initial(self):
        initial = super().get_initial()
        cliente_id = self.kwargs.get('cliente_id')

        if cliente_id:
            initial['cliente'] = Cliente.objects.get(id=cliente_id)

        return initial
    
    def form_valid(self, form):
        cliente_id = self.kwargs.get('cliente_id')
        cliente = (
            Cliente.objects.get(id=cliente_id)
            if cliente_id
            else form.cleaned_data['cliente']
        )

        monto = form.cleaned_data['monto']
        metodo_pago = form.cleaned_data['metodo_pago']

        with transaction.atomic():
            pago = Pago.objects.create(
                cliente=cliente,
                total_pagado=monto,
                metodo_pago=metodo_pago
            )

            monto_restante = Decimal(monto)

            ventas_pendientes = (
                Venta.objects.activas()
                .filter(Venta_CliId=cliente)
                .order_by("Venta_Fecha")
            )

            
            for venta in ventas_pendientes:

                total_pagado_venta = (
                    venta.pagos_aplicados.aggregate(
                        total=Sum('monto_pagado')
                    )['total'] or Decimal("0.00")
                )

                saldo_venta = venta.Venta_Total - total_pagado_venta

                # SOLO si realmente debe
                if saldo_venta <= 0:
                    continue

                abono = min(saldo_venta, monto_restante)

                PagoVenta.objects.create(
                    pago=pago,
                    venta=venta,
                    monto_pagado=abono
                )

                monto_restante -= abono

                if monto_restante <= 0:
                    break

            cliente.actualizar_saldo()

            HistorialSaldo.objects.create(
                cliente=cliente,
                saldo=cliente.saldo,
                pago=pago
            )
            pago.saldo_despues = cliente.saldo
            pago.save(update_fields=["saldo_despues"])

        return super().form_valid(form)
        
class ConfirmarVentaView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cliente_id = request.session.get('cliente_id')
        if not cliente_id:
            return redirect('venta_app:venta-index')  # Redirigir si no hay cliente

        cliente = Cliente.objects.get(id=cliente_id)
        carrito = CarShop.objects.filter(user=request.user)

        if not carrito.exists():
            return redirect('venta_app:venta-index')  # Redirigir si el carrito está vacío

        with transaction.atomic():
            # Calcular totales
            total_venta = sum(item.precio * item.cantidad for item in carrito)
            cantidad_total = sum(item.cantidad for item in carrito)

            # Crear la venta
            venta = Venta.objects.create(
                Venta_Fecha=now(),
                Venta_CliId=cliente,
                Venta_cantidad=cantidad_total,
                Venta_Total=total_venta,
                status='confirmed',
                user=request.user  # usuario cajero
            )
            #aplicar_saldo_a_favor(cliente, venta)
            cliente.actualizar_saldo()

            HistorialSaldo.objects.create(
                cliente=cliente,
                saldo=cliente.saldo,
                venta=venta
            )

        # Crear los detalles
        for item in carrito:
            VentaDetalle.objects.create(
                VD_VentasId=venta,
                producto=item.producto,
                VD_Cantidad=item.cantidad,
                VD_Precio=item.precio,
                VD_precio_compra=item.producto.precio_compra
            )

        # Limpiar el carrito
        carrito.delete()

        # Limpiar la sesión del cliente
        del request.session['cliente_id']

        request.session['ultima_venta_id'] = venta.id

        return redirect('venta_app:venta-detalle', pk=venta.pk)  # Redirigir a página principal
    



class VentaDetailView(DetailView):
    model = Venta
    template_name = "sales/venta_detalle.html"
    context_object_name = "venta"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.get_object()
        detalles = venta.detalles.select_related("producto")
        context["detalles"] = detalles
        context["total_peso"] = (
            detalles.aggregate(total=Sum("VD_Cantidad"))["total"] or 0
        )

        return context

class GananciasUltimosDiasView(TemplateView):
    template_name = "sales/ganancias_ultimos_dias.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ganancias'] = ganancias_ultimos_dias(7)
        return context

class SaldoTotalView(TemplateView):
    template_name = "sales/saldo_total.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["saldo_global"] = Cliente.objects.aggregate(total=Sum("saldo"))["total"] or 0
        return ctx



    
class UpdateCantidadAjaxView(VentasPermisoMixin, View):
    def post(self, request):

        carshop_id = request.POST.get("id")
        cantidad = request.POST.get("cantidad")

        if not carshop_id or not cantidad:
            return JsonResponse({"ok": False, "error": "Datos incompletos"})

        try:
            cantidad = Decimal(cantidad)
        except:
            return JsonResponse({"ok": False, "error": "Cantidad inválida"})

        item = CarShop.objects.get(
            id=carshop_id,
            user=request.user
        )

        item.cantidad = cantidad
        item.save(update_fields=["cantidad"])

        total = CarShop.objects.filter(
            user=request.user
        ).aggregate(
            total=Sum(F("cantidad") * F("precio"))
        )["total"] or Decimal("0.00")

        return JsonResponse({
            "ok": True,
            "id": item.id,
            "cantidad": float(item.cantidad),
            "precio": float(item.precio),
            "subtotal": float(item.cantidad * item.precio),
            "total": float(total)
        })
    
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

class AnularVentaView(VentasPermisoMixin, View):

    @transaction.atomic
    def post(self, request, pk):

        # 1️⃣ Obtener venta
        venta = get_object_or_404(Venta, pk=pk)

        # 2️⃣ Si ya está anulada
        if venta.status == 'cancelled':
            messages.warning(request, "La venta ya está anulada.")
            return redirect('venta_app:lista-ventas')

        # 3️⃣ Verificar pagos reales
        total_pagado = (
            venta.pagos_aplicados.aggregate(
                total=Sum('monto_pagado')
            )['total'] or Decimal("0.00")
        )

        if total_pagado > 0:
            messages.error(
                request,
                "No se puede anular una venta que tiene pagos registrados."
            )
            return redirect('venta_app:lista-ventas')

        # 4️⃣ Restituir stock
        for detalle in venta.detalles.select_related('producto'):
            producto = detalle.producto
            producto.cantidad += detalle.VD_Cantidad
            producto.save(update_fields=["cantidad"])

        # 5️⃣ Marcar como anulada
        venta.status = 'cancelled'
        venta.save(update_fields=["status"])

        messages.success(request, "Venta anulada correctamente.")

        # 6️⃣ Redirección neutra
        return redirect('venta_app:lista-ventas')
