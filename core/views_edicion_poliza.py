from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from core.models import Poliza, MovimientoPoliza, CuentaContable, Empresa
from decimal import Decimal
import json

@login_required
def editar_poliza(request, poliza_id):
    """
    Vista para editar movimientos de una póliza existente.
    Permite cambiar cuentas y montos de debe/haber.
    """
    poliza = get_object_or_404(Poliza, id=poliza_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                movimientos_data = json.loads(request.POST.get('movimientos_json', '[]'))
                
                # Validar cuadre
                total_debe = sum(Decimal(m['debe']) for m in movimientos_data)
                total_haber = sum(Decimal(m['haber']) for m in movimientos_data)
                diferencia = abs(total_debe - total_haber)
                
                if diferencia > Decimal('0.01'):
                    return JsonResponse({
                        'success': False,
                        'error': f'La póliza no cuadra. Diferencia: ${diferencia:.2f}'
                    })
                
                # Eliminar movimientos existentes
                poliza.movimientopoliza_set.all().delete()
                
                # Crear nuevos movimientos
                for mov_data in movimientos_data:
                    cuenta = CuentaContable.objects.get(id=mov_data['cuenta_id'])
                    MovimientoPoliza.objects.create(
                        poliza=poliza,
                        cuenta=cuenta,
                        debe=Decimal(mov_data['debe']),
                        haber=Decimal(mov_data['haber']),
                        descripcion=mov_data.get('descripcion', '')
                    )
                
                # Marcar como editada manualmente
                poliza.editada_manualmente = True
                poliza.usuario_edicion = request.user
                poliza.fecha_edicion = timezone.now()
                poliza.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Póliza editada exitosamente'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    # GET request - mostrar formulario
    movimientos = poliza.movimientopoliza_set.all().order_by('id')
    
    # Obtener empresa de la póliza
    empresa = poliza.factura.empresa if poliza.factura else Empresa.objects.first()
    cuentas = CuentaContable.objects.filter(empresa=empresa).order_by('codigo')
    
    return render(request, 'core/editar_poliza.html', {
        'poliza': poliza,
        'movimientos': movimientos,
        'cuentas': cuentas,
        'empresa': empresa
    })


@login_required
def crear_poliza_manual(request):
    """
    Vista para crear una póliza manual sin factura asociada.
    Útil para ajustes contables, pagos de impuestos, etc.
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                empresa_id = request.POST.get('empresa_id')
                fecha = request.POST.get('fecha')
                descripcion = request.POST.get('descripcion')
                movimientos_data = json.loads(request.POST.get('movimientos_json', '[]'))
                
                # Validar cuadre
                total_debe = sum(Decimal(m['debe']) for m in movimientos_data)
                total_haber = sum(Decimal(m['haber']) for m in movimientos_data)
                diferencia = abs(total_debe - total_haber)
                
                if diferencia > Decimal('0.01'):
                    return JsonResponse({
                        'success': False,
                        'error': f'La póliza no cuadra. Diferencia: ${diferencia:.2f}'
                    })
                
                # Crear póliza
                poliza = Poliza.objects.create(
                    factura=None,  # Póliza manual sin factura
                    fecha=fecha,
                    descripcion=descripcion,
                    editada_manualmente=True,
                    usuario_edicion=request.user,
                    fecha_edicion=timezone.now()
                )
                
                # Crear movimientos
                for mov_data in movimientos_data:
                    cuenta = CuentaContable.objects.get(id=mov_data['cuenta_id'])
                    MovimientoPoliza.objects.create(
                        poliza=poliza,
                        cuenta=cuenta,
                        debe=Decimal(mov_data['debe']),
                        haber=Decimal(mov_data['haber']),
                        descripcion=mov_data.get('descripcion', '')
                    )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Póliza creada exitosamente',
                    'poliza_id': poliza.id
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    # GET request - mostrar formulario
    empresas = Empresa.objects.all()
    
    return render(request, 'core/crear_poliza_manual.html', {
        'empresas': empresas
    })


@login_required
def validar_cuadre_ajax(request):
    """
    Endpoint AJAX para validar cuadre de póliza en tiempo real.
    Retorna totales y estado de cuadre.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movimientos = data.get('movimientos', [])
            
            total_debe = sum(Decimal(str(m.get('debe', 0))) for m in movimientos)
            total_haber = sum(Decimal(str(m.get('haber', 0))) for m in movimientos)
            diferencia = total_debe - total_haber
            
            cuadra = abs(diferencia) < Decimal('0.01')
            
            return JsonResponse({
                'cuadra': cuadra,
                'total_debe': f'{total_debe:.2f}',
                'total_haber': f'{total_haber:.2f}',
                'diferencia': f'{diferencia:.2f}'
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def obtener_cuentas_ajax(request):
    """
    Endpoint AJAX para obtener cuentas de una empresa.
    Usado por Select2 para búsqueda rápida.
    """
    empresa_id = request.GET.get('empresa_id')
    search = request.GET.get('search', '')
    
    if not empresa_id:
        return JsonResponse({'results': []})
    
    cuentas = CuentaContable.objects.filter(
        empresa_id=empresa_id
    )
    
    if search:
        cuentas = cuentas.filter(
            Q(codigo__icontains=search) |
            Q(nombre__icontains=search)
        )
    
    cuentas = cuentas.order_by('codigo')[:50]  # Limitar a 50 resultados
    
    results = [
        {
            'id': c.id,
            'text': f'{c.codigo} - {c.nombre}',
            'codigo': c.codigo,
            'nombre': c.nombre
        }
        for c in cuentas
    ]
    
    return JsonResponse({'results': results})
