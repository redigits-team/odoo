{
    'name': 'Centro Analisi',
    'version': '1.0',
    'summary': 'Gestione clienti e analisi con reminder',
    'category': 'Healthcare',
    'author': 'Il Tuo Nome',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/analisi_view.xml',
        'views/tipianalisi_view.xml',
        'views/cliente_view.xml',
        'views/reminder_view.xml',
        'views/dashboard_view.xml',
        'data/email_template.xml',
        # 'data/reminder_cron.xml',
        'views/menu.xml',

    ],
    'installable': True,
    'application': True,
}