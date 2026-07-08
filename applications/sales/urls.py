from django.urls import path
from . import views

app_name = "venta_app"

urlpatterns = [
    path('ventas/', views.ventas, name='venta'),
    path('lista-ventas/', views.ListVentas.as_view(), name='lista-ventas'),
    path(
        'venta/index/', 
        views.AddCarView.as_view(),
        name='venta-index',
    ),
    path(
        'carshop/addview/<pk>/', 
        views.CarShopAddView.as_view(),
        name='carshop-add',
    ),
    path(
        'carshop/update/<pk>/', 
        views.CarShopUpdateView.as_view(),
        name='carshop-update',
    ),
    path(
        'carshop/delete/<pk>/', 
        views.CarShopDeleteView.as_view(),
        name='carshop-delete',
    ),
    path(
        'carshop/delete-all/', 
        views.CarShopDeleteAll.as_view(),
        name='carshop-delete_all',
    ),
    path(
        'venta/simple/', 
        views.ProcesoVentaSimpleView.as_view(),
        name='venta-simple',
    ),
    path('pago/registrar/', views.RegistrarPagoView.as_view(), name='registrar-pago'),
    path(
        'abonos/registrar/',
        views.RegistrarAbonoView.as_view(),
        name='registrar-abono'
    ),
    path('abonos/registrar/<int:cliente_id>/', views.RegistrarAbonoView.as_view(), name='registrar-abono'),

    path('confirmar-venta/', views.ConfirmarVentaView.as_view(), name='confirmar_venta'),
    path("venta/<int:pk>/", views.VentaDetailView.as_view(), name="venta-detalle"),
    path("ajax/add-peso/", views.AddPesoAjaxView.as_view(), name="ajax-add-peso"),
    path(
    "ajax/update-peso/",
    views.UpdateCantidadAjaxView.as_view(),
    name="ajax-update-peso"
    ),
    path(
    "ajax/delete-carshop/",
    views.CarShopDeleteAjaxView.as_view(),
    name="ajax-delete-carshop"
    ),
    path(
    'ventas/<int:pk>/anular/',
    views.AnularVentaView.as_view(),
    name='anular-venta'
    ),
    path('venta/ganancias/', views.GananciasUltimosDiasView.as_view(), name='ganancias'),
    path("saldo-total/", views.SaldoTotalView.as_view(), name="saldo_total"),

]
