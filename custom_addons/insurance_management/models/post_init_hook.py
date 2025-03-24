from odoo import api, SUPERUSER_ID
from dateutil.relativedelta import relativedelta

def create_scheduled_actions(cr, env=None):
    """Create scheduled actions after module installation"""
    if not env:
        env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Create scheduled action for insurance daily tasks
    env['ir.cron'].create({
        'name': 'Insurance: Daily Management Tasks',
        'model_id': env.ref('sale.model_sale_order').id,
        'state': 'code',
        'code': 'model._run_insurance_daily_tasks()',
        'interval_number': 1,
        'interval_type': 'days',
        'numbercall': -1,
        'doall': False,
        'active': True,
        'user_id': env.ref('base.user_root').id,
    })