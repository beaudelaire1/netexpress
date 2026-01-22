"""
Décorateurs personnalisés pour le contrôle d'accès dans NetExpress.

Ce module fournit des décorateurs réutilisables pour gérer les permissions
d'accès aux vues Django.
"""

from django.contrib.auth.decorators import user_passes_test


def is_business_admin(user):
    """
    Vérifie si l'utilisateur est staff ou appartient au groupe admin_business.
    
    Cette fonction est utilisée comme test par le décorateur business_admin_required
    pour autoriser l'accès aux utilisateurs qui sont soit :
    - membres du staff (is_staff=True), OU
    - membres du groupe 'admin_business'
    
    Args:
        user: L'objet utilisateur Django à vérifier
        
    Returns:
        bool: True si l'utilisateur a les permissions, False sinon
    """
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return user.groups.filter(name='admin_business').exists()


business_admin_required = user_passes_test(
    is_business_admin,
    login_url='/admin/login/'
)
"""
Décorateur pour restreindre l'accès aux utilisateurs staff ou admin_business.

Utilisation:
    @business_admin_required
    def ma_vue(request):
        # Votre code ici
        pass
        
Ce décorateur remplace @staff_member_required dans les vues où les utilisateurs
du groupe 'admin_business' doivent également avoir accès, même s'ils ne sont
pas staff.
"""
