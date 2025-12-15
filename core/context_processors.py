from core.models import UsuarioEmpresa


def multi_empresa_context(request):
    """
    Context processor para inyectar información de multi-empresa en todos los templates.
    Proporciona:
    - available_empresas: lista de empresas disponibles para el usuario
    - active_empresa: empresa actualmente activa en sesión
    """
    if not request.user.is_authenticated:
        return {
            'available_empresas': [],
            'active_empresa': None
        }
    
    active_empresa_id = request.session.get('active_empresa_id')
    
    # Obtener empresas del usuario
    mis_empresas_rels = UsuarioEmpresa.objects.filter(
        usuario=request.user
    ).select_related('empresa')
    
    empresas_select = []
    active_empresa = None
    
    for rel in mis_empresas_rels:
        is_selected = (rel.empresa.id == active_empresa_id)
        
        empresas_select.append({
            'id': rel.empresa.id,
            'nombre': rel.empresa.nombre,
            'rfc': rel.empresa.rfc,
            'rol': rel.get_rol_display(),
            'selected': is_selected
        })
        
        if is_selected:
            active_empresa = rel.empresa
    
    return {
        'available_empresas': empresas_select,
        'active_empresa': active_empresa
    }


def user_display(request):
    """
    Context processor to provide user display name globally to all templates.
    This avoids template tag rendering issues in navbars and dropdowns.
    """
    if request.user.is_authenticated:
        return {
            'user_display_name': request.user.get_full_name() or request.user.username
        }
    return {'user_display_name': ''}
