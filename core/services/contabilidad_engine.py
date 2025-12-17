from django.db.models import Sum, Q, F, Value, DecimalField
from django.db.models.functions import Coalesce
from core.models import CuentaContable, MovimientoPoliza
from datetime import date

class ContabilidadEngine:
    """
    Motor Unificado de Reportes Financieros.
    Responsable de calcular ER y BG con consistencia matemática.
    """

    @staticmethod
    def obtener_resultados(empresa, fecha_inicio, fecha_fin):
        """
        Calcula el Estado de Resultados (Cuentas Nominales) para un periodo.
        Retorna: { 'ingresos': [], 'egresos': [], 'utilidad_neta': Decimal, ... }
        """
        # Filtro Base: Movimientos del periodo (sin filtrar por estado de factura)
        filtro_periodo = Q(
            movimientopoliza__poliza__fecha__range=[fecha_inicio, fecha_fin]
        )

        # Helper para anotar saldo del periodo
        def annotate_saldo(queryset, naturaleza):
            if naturaleza == 'A': # Acreedora (Ingresos): Haber - Debe
                expr = F('m_haber') - F('m_debe')
            else: # Deudora (Costos/Gastos): Debe - Haber
                expr = F('m_debe') - F('m_haber')

            return queryset.annotate(
                m_debe=Coalesce(Sum('movimientopoliza__debe', filter=filtro_periodo), Value(0, output_field=DecimalField())),
                m_haber=Coalesce(Sum('movimientopoliza__haber', filter=filtro_periodo), Value(0, output_field=DecimalField()))
            ).annotate(saldo=expr).exclude(saldo=0)

        # 1. Ingresos (Tipo: INGRESO, Nat: A)
        # Excluir cuenta 702-99 (ajustes técnicos, no cuenta real de negocio)
        ingresos_qs = CuentaContable.objects.filter(empresa=empresa, tipo='INGRESO').exclude(codigo='702-99')
        ingresos = list(annotate_saldo(ingresos_qs, 'A'))

        # 2. Egresos (Tipo: COSTO o GASTO, Nat: D)
        # Excluir cuenta 702-99 (ajustes técnicos, no cuenta real de negocio)
        egresos_qs = CuentaContable.objects.filter(empresa=empresa, tipo__in=['COSTO', 'GASTO']).exclude(codigo='702-99')
        egresos = list(annotate_saldo(egresos_qs, 'D'))

        # 3. Totales
        total_ingresos = sum(c.saldo for c in ingresos)
        total_egresos = sum(c.saldo for c in egresos)
        utilidad_neta = total_ingresos - total_egresos

        # Cálculo explícito de Subtotal (Ventas) vs IVA (trasladado)
        # Heurística: cuentas de ventas suelen empezar por '401' o '4', IVA trasladado por '216' o '216-01'
        subtotal_qs = CuentaContable.objects.filter(empresa=empresa).filter(Q(codigo__startswith='401') | Q(codigo__startswith='4'))
        iva_qs = CuentaContable.objects.filter(empresa=empresa).filter(Q(codigo__startswith='216') | Q(codigo__icontains='iva'))

        subtotal = sum(
            c.m_haber if hasattr(c, 'm_haber') else (
                c.movimientopoliza_set.filter(poliza__fecha__range=[fecha_inicio, fecha_fin]).aggregate(total=Sum('haber'))['total'] or 0
            ) for c in subtotal_qs
        )

        iva_trasladado = sum(
            c.m_haber if hasattr(c, 'm_haber') else (
                c.movimientopoliza_set.filter(poliza__fecha__range=[fecha_inicio, fecha_fin]).aggregate(total=Sum('haber'))['total'] or 0
            ) for c in iva_qs
        )

        return {
            'ingresos': ingresos,
            'egresos': egresos,
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'utilidad_neta': utilidad_neta,
            'subtotal_ventas': subtotal,
            'iva_trasladado': iva_trasladado
        }

    @staticmethod
    def obtener_balance_general(empresa, fecha_corte):
        """
        Calcula el Balance General (Cuentas Reales) acumulado hasta fecha_corte.
        Integra la Utilidad del Ejercicio (ER) al Capital.
        """
        # Filtro Acumulado: Todo movimiento hasta la fecha de corte (sin filtrar por estado de factura)
        filtro_acumulado = Q(
            movimientopoliza__poliza__fecha__lte=fecha_corte
        )

        def annotate_saldo_acum(queryset, naturaleza):
            if naturaleza == 'D': # Activos (Deudora): Debe - Haber
                 expr = F('s_debe') - F('s_haber')
            else: # Pasivo/Capital (Acreedora): Haber - Debe
                 expr = F('s_haber') - F('s_debe')
            
            return queryset.annotate(
                s_debe=Coalesce(Sum('movimientopoliza__debe', filter=filtro_acumulado), Value(0, output_field=DecimalField())),
                s_haber=Coalesce(Sum('movimientopoliza__haber', filter=filtro_acumulado), Value(0, output_field=DecimalField()))
            ).annotate(saldo=expr).exclude(saldo=0)

        # 1. Activos
        activos = list(annotate_saldo_acum(
            CuentaContable.objects.filter(empresa=empresa, tipo='ACTIVO'), 'D'))
        
        # 2. Pasivos
        pasivos = list(annotate_saldo_acum(
            CuentaContable.objects.filter(empresa=empresa, tipo='PASIVO'), 'A'))
            
        # 3. Capital Contribuido (Cuentas tipo CAPITAL)
        capital_contribuido = list(annotate_saldo_acum(
            CuentaContable.objects.filter(empresa=empresa, tipo='CAPITAL'), 'A'))

        # 4. Cálculo de Utilidad del Ejercicio
        # Se calcula desde el inicio de los tiempos (o inicio fiscal) hasta la fecha de corte
        # Para simplificar, asumimos "Resultados Acumulados" si no hay cierre fiscal anual purgado.
        # Llamamos al metodo de resultados con fecha inicio muy antigua (o 1 de Enero del año)
        anio_fiscal = fecha_corte.year
        fecha_inicio_ejercicio = date(anio_fiscal, 1, 1)
        
        # OJO: Si queremos "Balance General al día X", la utilidad es la del ejercicio en curso.
        # Los ejercicios pasados deberían estar en una cuenta de capital "Resultados Ejercicios Anteriores".
        # Como no tenemos cierre anual implementado, calcularemos la Utilidad acumulada "histórica" 
        # para que cuadre el balance global (A = P + C).
        # Usaremos fecha_inicio = date(2000, 1, 1) para atrapar todo si no hay cierres.
        fecha_hist = date(2000, 1, 1)
        res = ContabilidadEngine.obtener_resultados(empresa, fecha_hist, fecha_corte)
        utilidad_ejercicio = res['utilidad_neta']

        # Totales
        total_activo = sum(c.saldo for c in activos)
        total_pasivo = sum(c.saldo for c in pasivos)
        total_capital_contribuido = sum(c.saldo for c in capital_contribuido)
        
        total_capital = total_capital_contribuido + utilidad_ejercicio
        
        # Validación Contable / Cuadre
        suma_pasivo_capital = total_pasivo + total_capital
        diferencia = total_activo - suma_pasivo_capital
        cuadra = abs(diferencia) < 0.1

        return {
            'activos': activos,
            'pasivos': pasivos,
            'capital_contribuido': capital_contribuido,
            'utilidad_ejercicio': utilidad_ejercicio,
            'total_activo': total_activo,
            'total_pasivo': total_pasivo,
            'total_capital': total_capital,
            'cuadra': cuadra,
            'diferencia': diferencia
        }

    @staticmethod
    def calcular_balanza(empresa, fecha_inicio, fecha_fin):
        """
        Calcula saldos para la Balanza de Comprobación en un periodo.
        Retorna lista de dicts: {'codigo','nombre','saldo_ini','debe','haber','saldo_fin','codigo_sat','nivel'}
        """
        from decimal import Decimal
        cuentas = CuentaContable.objects.filter(empresa=empresa).order_by('codigo')
        rows = []

        for c in cuentas:
            # Saldos antes del periodo (acumulado hasta día previo)
            antes_qs = MovimientoPoliza.objects.filter(
                cuenta=c,
                poliza__fecha__date__lt=fecha_inicio
            )
            antes_debe = antes_qs.aggregate(total=Sum('debe'))['total'] or Decimal('0')
            antes_haber = antes_qs.aggregate(total=Sum('haber'))['total'] or Decimal('0')

            # Movimientos en periodo
            periodo_qs = MovimientoPoliza.objects.filter(
                cuenta=c,
                poliza__fecha__date__gte=fecha_inicio,
                poliza__fecha__date__lte=fecha_fin
            )
            mov_debe = periodo_qs.aggregate(total=Sum('debe'))['total'] or Decimal('0')
            mov_haber = periodo_qs.aggregate(total=Sum('haber'))['total'] or Decimal('0')

            # Naturaleza: 'A' acreedora => saldo = haber - debe
            if getattr(c, 'naturaleza', 'D') == 'A':
                saldo_ini = (antes_haber or Decimal('0')) - (antes_debe or Decimal('0'))
                saldo_fin = saldo_ini + ((mov_haber or Decimal('0')) - (mov_debe or Decimal('0')))
            else:
                saldo_ini = (antes_debe or Decimal('0')) - (antes_haber or Decimal('0'))
                saldo_fin = saldo_ini + ((mov_debe or Decimal('0')) - (mov_haber or Decimal('0')))

            rows.append({
                'codigo': c.codigo,
                'nombre': c.nombre,
                'saldo_ini': saldo_ini,
                'debe': mov_debe,
                'haber': mov_haber,
                'saldo_fin': saldo_fin,
                'codigo_sat': getattr(c, 'codigo_sat', ''),
                'nivel': getattr(c, 'nivel', 1)
            })

        return rows
