{
    'name': 'Insurance Management',
    'version': '1.0',
    'category': 'Sales/Insurance',
    'summary': 'Manage insurance policies and quotations',
    'description': """
        Insurance Agency Management System
        - Manage customers with insurance-specific information
        - Create and manage insurance policies
        - Generate insurance quotations
        - Track policy payments and installments
    """,
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/insurance_data.xml',
        'views/dashboard_views.xml',
        'views/task_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_payment_views.xml',
        'views/client_list_view.xml',
        'views/improved_policy_views.xml',
        'views/insurance_menu.xml',
    ],
    # No custom assets needed anymore as we're using standard Odoo buttons
    # 'post_init_hook': 'create_scheduled_actions',
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}