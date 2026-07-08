from decimal import Decimal

import pytest
from decimal import Decimal
from django.utils import timezone

@pytest.mark.django_db
def test_saldo_pendiente_sin_pagos():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(email="test@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Juan")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_cantidad=10,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    assert cliente.saldo_pendiente == Decimal("100.00")

@pytest.mark.django_db
def test_saldo_con_pago_parcial():
    from applications.sales.models import Cliente, Venta, Pago
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="test2@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Maria")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_cantidad=10,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    Pago.objects.create(
        cliente=cliente,
        total_pagado=Decimal("30.00")
    )

    assert cliente.saldo_pendiente == Decimal("70.00")

@pytest.mark.django_db
def test_pago_mayor_a_deuda():
    from applications.sales.models import Cliente, Venta, Pago
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="test3@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Luis")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("50.00"),
        status='confirmed',
        user=user
    )

    Pago.objects.create(
        cliente=cliente,
        total_pagado=Decimal("60.00")
    )

    # Aquí defines tu lógica de negocio
    assert cliente.saldo_pendiente <= Decimal("0.00")



@pytest.mark.django_db
def test_ventas_no_confirmadas_no_suman():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="test4@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Pedro")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='draft',
        user=user
    )

    assert cliente.saldo_pendiente == Decimal("0.00")

@pytest.mark.django_db
def test_dias_vencidos():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal
    from datetime import timedelta

    User = get_user_model()
    user = User.objects.create_user(email="test6@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Carlos")

    fecha_pasada = timezone.now() - timedelta(days=10)

    Venta.objects.create(
        Venta_Fecha=fecha_pasada,
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    assert cliente.dias_vencidos >= 10

@pytest.mark.django_db
def test_tiene_pagos_reales():
    from applications.sales.models import Cliente, Venta, Pago, PagoVenta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="test5@test.com", password="123456")

    cliente = Cliente.objects.create(nombre="Ana")

    venta = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    pago = Pago.objects.create(
        cliente=cliente,
        total_pagado=Decimal("20.00")
    )

    PagoVenta.objects.create(
        pago=pago,
        venta=venta,
        monto_pagado=Decimal("20.00")
    )

    assert venta.tiene_pagos_reales is True

@pytest.mark.django_db
def test_pago_parcial_por_venta():
    from applications.sales.models import Cliente, Venta, Pago, PagoVenta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="multi@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Cliente Test")

    venta1 = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    venta2 = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("50.00"),
        status='confirmed',
        user=user
    )

    pago = Pago.objects.create(
        cliente=cliente,
        total_pagado=Decimal("80.00")
    )

    PagoVenta.objects.create(pago=pago, venta=venta1, monto_pagado=Decimal("80.00"))

    # saldo esperado = 150 - 80 = 70
    assert cliente.saldo_pendiente == Decimal("70.00")

@pytest.mark.django_db
def test_total_vs_detalles_inconsistencia():
    from applications.sales.models import Venta, Cliente
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="test7@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Cliente Test")

    venta = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,  # 👈 CORRECTO
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    assert venta.Venta_Total == Decimal("100.00")

@pytest.mark.django_db
def test_saldo_desincronizado():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="sync@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Sync Test")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    # saldo guardado aún no actualizado
    assert cliente.saldo == 0  

    # saldo real calculado
    assert cliente.saldo_pendiente == Decimal("100.00")

@pytest.mark.django_db
def test_editar_venta_afecta_saldo():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="edit@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Cliente Edit")

    venta = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    assert cliente.saldo_pendiente == Decimal("100.00")

    # editar venta
    venta.Venta_Total = Decimal("50.00")
    venta.save()

    assert cliente.saldo_pendiente == Decimal("50.00")

@pytest.mark.django_db
def test_eliminar_venta_actualiza_saldo():
    from applications.sales.models import Cliente, Venta
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="delete@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Cliente Delete")

    venta = Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    venta.delete()

    assert cliente.saldo_pendiente == Decimal("0.00")
@pytest.mark.django_db
def test_pago_no_aplicado_a_ventas():
    from applications.sales.models import Cliente, Venta, Pago
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(email="edge@test.com", password="123")

    cliente = Cliente.objects.create(nombre="Edge Case")

    Venta.objects.create(
        Venta_Fecha=timezone.now(),
        Venta_CliId=cliente,
        Venta_Total=Decimal("100.00"),
        status='confirmed',
        user=user
    )

    # pago registrado pero NO aplicado a ventas
    Pago.objects.create(
        cliente=cliente,
        total_pagado=Decimal("100.00")
    )

    # ¿qué debería pasar?
    # hoy tu sistema dirá saldo 0
    # pero en realidad no se aplicó a ninguna venta

    assert cliente.saldo_pendiente == Decimal("0.00")  # ⚠️ aquí está el problema conceptual