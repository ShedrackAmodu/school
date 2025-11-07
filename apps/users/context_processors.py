from .models import Role


def user_roles(request):
    """
    Context processor to add user role information to all templates.
    """
    if request.user.is_authenticated:
        # Get all user roles
        user_roles_queryset = request.user.user_roles.filter(status='active').select_related('role')

        # Get primary role
        primary_role = user_roles_queryset.filter(is_primary=True).first()

        # Get all roles for the user
        user_roles_list = list(user_roles_queryset.values_list('role__role_type', flat=True))

        # Role type constants for template use
        role_types = {
            'SUPER_ADMIN': Role.RoleType.SUPER_ADMIN,
            'ADMIN': Role.RoleType.ADMIN,
            'PRINCIPAL': Role.RoleType.PRINCIPAL,
            'TEACHER': Role.RoleType.TEACHER,
            'STUDENT': Role.RoleType.STUDENT,
            'PARENT': Role.RoleType.PARENT,
            'ACCOUNTANT': Role.RoleType.ACCOUNTANT,
            'LIBRARIAN': Role.RoleType.LIBRARIAN,
            'DRIVER': Role.RoleType.DRIVER,
            'SUPPORT': Role.RoleType.SUPPORT,
            'TRANSPORT_MANAGER': Role.RoleType.TRANSPORT_MANAGER,
            'HOSTEL_WARDEN': Role.RoleType.HOSTEL_WARDEN,
        }

        # Staff roles (all except student and parent)
        staff_roles = Role.STAFF_ROLES

        # Check specific role memberships
        is_staff_member = any(role in staff_roles for role in user_roles_list)
        is_admin_user = request.user.is_staff or request.user.is_superuser
        is_super_admin = Role.RoleType.SUPER_ADMIN in user_roles_list
        is_admin = Role.RoleType.ADMIN in user_roles_list
        is_principal = Role.RoleType.PRINCIPAL in user_roles_list
        is_teacher = Role.RoleType.TEACHER in user_roles_list
        is_student = Role.RoleType.STUDENT in user_roles_list
        is_parent = Role.RoleType.PARENT in user_roles_list
        is_accountant = Role.RoleType.ACCOUNTANT in user_roles_list
        is_librarian = Role.RoleType.LIBRARIAN in user_roles_list
        is_driver = Role.RoleType.DRIVER in user_roles_list
        is_support = Role.RoleType.SUPPORT in user_roles_list
        is_transport_manager = Role.RoleType.TRANSPORT_MANAGER in user_roles_list
        is_hostel_warden = Role.RoleType.HOSTEL_WARDEN in user_roles_list

        # Role hierarchy for permission checks
        role_hierarchy = {
            Role.RoleType.SUPER_ADMIN: 100,
            Role.RoleType.ADMIN: 90,
            Role.RoleType.PRINCIPAL: 80,
            Role.RoleType.TEACHER: 50,
            Role.RoleType.ACCOUNTANT: 40,
            Role.RoleType.LIBRARIAN: 40,
            Role.RoleType.SUPPORT: 30,
            Role.RoleType.TRANSPORT_MANAGER: 30,
            Role.RoleType.HOSTEL_WARDEN: 30,
            Role.RoleType.DRIVER: 20,
            Role.RoleType.PARENT: 10,
            Role.RoleType.STUDENT: 5,
        }

        # Get highest role level
        highest_role_level = max([role_hierarchy.get(role, 0) for role in user_roles_list]) if user_roles_list else 0

        return {
            'user_primary_role': primary_role.role if primary_role else None,
            'user_roles': user_roles_queryset,
            'user_role_types': user_roles_list,
            'role_types': role_types,
            'staff_roles': staff_roles,

            # Role flags
            'is_staff_member': is_staff_member,
            'is_admin_user': is_admin_user,
            'is_super_admin': is_super_admin,
            'is_admin': is_admin,
            'is_principal': is_principal,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'is_parent': is_parent,
            'is_accountant': is_accountant,
            'is_librarian': is_librarian,
            'is_driver': is_driver,
            'is_support': is_support,
            'is_transport_manager': is_transport_manager,
            'is_hostel_warden': is_hostel_warden,

            # Permission helpers
            'can_manage_users': is_super_admin or is_admin or request.user.is_superuser,
            'can_manage_academics': is_super_admin or is_admin or is_principal or is_teacher,
            'can_manage_finance': is_super_admin or is_admin or is_accountant,
            'can_manage_library': is_super_admin or is_admin or is_librarian,
            'can_manage_transport': is_super_admin or is_admin or is_transport_manager or is_driver,
            'can_manage_hostels': is_super_admin or is_admin or is_hostel_warden,
            'can_view_student_data': is_super_admin or is_admin or is_principal or is_teacher or is_parent,
            'highest_role_level': highest_role_level,
        }

    return {
        'user_primary_role': None,
        'user_roles': [],
        'user_role_types': [],
        'role_types': {},
        'staff_roles': Role.STAFF_ROLES,

        # Default role flags (all False for anonymous users)
        'is_staff_member': False,
        'is_admin_user': False,
        'is_super_admin': False,
        'is_admin': False,
        'is_principal': False,
        'is_teacher': False,
        'is_student': False,
        'is_parent': False,
        'is_accountant': False,
        'is_librarian': False,
        'is_driver': False,
        'is_support': False,
        'is_transport_manager': False,
        'is_hostel_warden': False,

        # Default permissions (all False for anonymous users)
        'can_manage_users': False,
        'can_manage_academics': False,
        'can_manage_finance': False,
        'can_manage_library': False,
        'can_manage_transport': False,
        'can_manage_hostels': False,
        'can_view_student_data': False,
        'highest_role_level': 0,
    }
