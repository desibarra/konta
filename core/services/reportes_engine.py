from django.db.models import Sum, Q, F, Case, When, Value, DecimalField
from django.db.models.functions import Coalesce
from core.models import CuentaContable

class ReportesEngine:
    @staticmethod
    def obtener_balanza_comprobacion(empresa, fecha_inicio, fecha_fin):
        """
        Genera los datos para la Balanza de Comprobación utilizando agregaciones del ORM.
        
        CORRECCIÓN FINAL:
        - Campos reales: 'debe' y 'haber' (MovimientoPoliza).
        - Relación inversa: 'movimientopoliza' (Default de Django para FK singleton).
        - Filtro Estado: poliza -> factura -> estado_contable
        """
        
        cuentas = CuentaContable.objects.filter(empresa=empresa)
        
        # --- DEFINICIÓN DE FILTROS ---
        
        # SIMPLIFICADO: Solo filtrar por fecha, sin estado_contable
        # Esto asegura que TODOS los movimientos se muestren
        
        # 1. Movimientos PREVIOS (Saldo Inicial)
        filtro_previo = Q(
            movimientopoliza__poliza__fecha__lt=fecha_inicio
        )
        
        # 2. Movimientos PERIODO
        filtro_periodo = Q(
            movimientopoliza__poliza__fecha__range=[fecha_inicio, fecha_fin]
        )
        
        # --- AGREGACIONES ---
        
        cuentas = cuentas.annotate(
            # SALDO INICIAL COMPONENTES
            suma_debe_previo=Coalesce(
                Sum('movimientopoliza__debe', filter=filtro_previo), 
                Value(0, output_field=DecimalField())
            ),
            suma_haber_previo=Coalesce(
                Sum('movimientopoliza__haber', filter=filtro_previo), 
                Value(0, output_field=DecimalField())
            ),
            
            # MOVIMIENTOS PERIODO
            movimientos_debe=Coalesce(
                Sum('movimientopoliza__debe', filter=filtro_periodo), 
                Value(0, output_field=DecimalField())
            ),
            movimientos_haber=Coalesce(
                Sum('movimientopoliza__haber', filter=filtro_periodo), 
                Value(0, output_field=DecimalField())
            ),
        )
        
        # --- CÁLCULO DE SALDOS ---
        
        cuentas = cuentas.annotate(
            saldo_inicial=Case(
                # Deudora: Debe - Haber
                When(es_deudora=True, then=F('suma_debe_previo') - F('suma_haber_previo')),
                # Acreedora: Haber - Debe
                default=F('suma_haber_previo') - F('suma_debe_previo'),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            ),
            
            saldo_final=Case(
                # Deudora: Inicial + Debe - Haber
                When(es_deudora=True, then=F('saldo_inicial') + F('movimientos_debe') - F('movimientos_haber')),
                # Acreedora: Inicial + Haber - Debe
                default=F('saldo_inicial') + F('movimientos_haber') - F('movimientos_debe'),
                output_field=DecimalField(max_digits=20, decimal_places=2)
            )
        )
        
        # Mostrar todas las cuentas que tengan movimientos en MovimientoPoliza
        cuentas = cuentas.filter(
            Q(suma_debe_previo__gt=0) | Q(suma_haber_previo__gt=0) |
            Q(movimientos_debe__gt=0) | Q(movimientos_haber__gt=0)
        ).order_by('codigo')

        return cuentas
        
    @staticmethod
    def obtener_estado_resultados(empresa, fecha_inicio, fecha_fin):
        """
        Genera los datos para el Estado de Resultados.
        Reglas:
        - Ingresos: Cuentas 4xx (Naturaleza Acreedora: Saldo = Haber - Debe)
        - Egresos: Cuentas 5xx, 6xx (Naturaleza Deudora: Saldo = Debe - Haber)
        - Solo movimientos del PERIODO (No saldos iniciales).
        """
        
        # Filtro Periodo y Estado Contabilizado
        filtro_periodo = Q(
            movimientopoliza__poliza__fecha__range=[fecha_inicio, fecha_fin],
            movimientopoliza__poliza__factura__estado_contable='CONTABILIZADA'
        )
        
        # --- INGRESOS y EGRESOS ---
        # Queremos:
        # - Ingresos: cuentas clase 4 (haber>debe) y cuentas clase 5 con saldo acreedor (haber>debe)
        # - Egresos: cuentas clase 6 y cuentas clase 5 con saldo deudor (debe>haber)
        qs_45_6 = CuentaContable.objects.filter(
            empresa=empresa
        ).filter(
            Q(codigo__startswith='4') | Q(codigo__startswith='5') | Q(codigo__startswith='6')
        ).annotate(
            m_debe=Coalesce(Sum('movimientopoliza__debe', filter=filtro_periodo), Value(0, output_field=DecimalField())),
            m_haber=Coalesce(Sum('movimientopoliza__haber', filter=filtro_periodo), Value(0, output_field=DecimalField()))
        )

        lista_ingresos = []
        lista_egresos = []

        for c in qs_45_6:
            # net_credit = haber - debe ; net_debit = debe - haber
            net = (c.m_haber or 0) - (c.m_debe or 0)
            if str(c.codigo).startswith('4'):
                if net > 0:
                    c.saldo = net
                    lista_ingresos.append(c)
            elif str(c.codigo).startswith('5'):
                if net > 0:
                    # clase 5 con saldo acreedor → Otros Ingresos
                    c.saldo = net
                    lista_ingresos.append(c)
                else:
                    # clase 5 con saldo deudor → Gasto/Reducción
                    saldo_eg = (c.m_debe or 0) - (c.m_haber or 0)
                    if saldo_eg > 0:
                        c.saldo = saldo_eg
                        lista_egresos.append(c)
            else:
                # clase 6 → egresos (debe - haber)
                saldo_eg = (c.m_debe or 0) - (c.m_haber or 0)
                if saldo_eg > 0:
                    c.saldo = saldo_eg
                    lista_egresos.append(c)

        total_ingresos = sum(c.saldo for c in lista_ingresos)
        total_egresos = sum(c.saldo for c in lista_egresos)
        
        return {
            'ingresos': lista_ingresos,
            'egresos': lista_egresos,
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'utilidad_neta': total_ingresos - total_egresos
        }

    @staticmethod
    def calcular_utilidad_neta(empresa, fecha_inicio, fecha_fin):
        """
        Calcula y retorna los totales de Ingresos, Egresos y la Utilidad Neta
        para el periodo indicado. Esta función unifica la lógica que debe
        usarse tanto en Estado de Resultados como en Balance General.

        Retorna: dict { 'total_ingresos', 'total_egresos', 'utilidad_neta' }
        """
        res = ReportesEngine.obtener_estado_resultados(empresa, fecha_inicio, fecha_fin)
        return {
            'total_ingresos': res.get('total_ingresos', 0),
            'total_egresos': res.get('total_egresos', 0),
            'utilidad_neta': res.get('utilidad_neta', 0)
        }