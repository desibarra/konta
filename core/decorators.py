from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import UsuarioEmpresa


def require_active_empresa(view_func):
    """
    Decorador que asegura que:
    1. Hay una empresa seleccionada en la sesión.
    2. El usuario actual tiene permiso para ver esa empresa.
    
    Uso:
        @login_required
        @require_active_empresa
        def mi_vista(request):
            # Ya puedes usar request.session['active_empresa_id'] con seguridad
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        active_id = request.session.get('active_empresa_id')
        
        # 1. Validación: ¿Existe ID en sesión?
        if not active_id:
            messages.warning(request, "⚠️ Por favor, selecciona una empresa para continuar.")
            return redirect('dashboard')
        
        # 2. Seguridad: ¿El usuario tiene acceso REAL a esa empresa?
        # Esto evita que alguien inyecte un ID de empresa en su cookie
        exists = UsuarioEmpresa.objects.filter(
            usuario=request.user, 
            empresa__id=active_id
        ).exists()

        if not exists:
            messages.error(request, "⛔ Acceso denegado: No tienes permiso en esta empresa.")
            # Limpiamos la sesión corrupta
            if 'active_empresa_id' in request.session:
                del request.session['active_empresa_id']
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper
