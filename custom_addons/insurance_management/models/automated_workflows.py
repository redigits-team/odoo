from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class InsuranceTask(models.Model):
    _name = 'insurance.task'
    _description = 'Insurance Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, id'
    
    name = fields.Char(string="Task", required=True)
    description = fields.Text(string="Description")
    task_type = fields.Selection([
        ('expiration', 'Policy Expiration'),
        ('payment', 'Payment Reminder'),
        ('approval', 'Policy Approval'),
        ('follow_up', 'Client Follow-up'),
        ('other', 'Other'),
    ], string="Type", required=True, default='other')
    
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='new', tracking=True)
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Urgent'),
        ('3', 'Critical'),
    ], string="Priority", default='0', tracking=True)
    
    user_id = fields.Many2one('res.users', string="Assigned To", default=lambda self: self.env.user, tracking=True)
    policy_id = fields.Many2one('sale.order', string="Related Policy", domain=[('is_policy', '=', True)])
    partner_id = fields.Many2one('res.partner', string="Client")
    payment_id = fields.Many2one('account.payment', string="Related Payment")
    
    create_date = fields.Datetime(string="Created On", readonly=True)
    due_date = fields.Date(string="Due Date", required=True, tracking=True)
    completion_date = fields.Datetime(string="Completed On", readonly=True)
    
    kanban_state = fields.Selection([
        ('normal', 'Ready'),
        ('done', 'Done'),
        ('blocked', 'Blocked')
    ], string="Kanban State", default='normal', tracking=True)
    
    color = fields.Integer(string="Color Index")
    
    def action_mark_in_progress(self):
        self.write({'state': 'in_progress'})
        
    def action_mark_done(self):
        self.write({
            'state': 'done',
            'kanban_state': 'done',
            'completion_date': fields.Datetime.now()
        })
        
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        
    def action_reset_new(self):
        self.write({
            'state': 'new',
            'kanban_state': 'normal',
            'completion_date': False
        })
        
    def action_view_policy(self):
        return {
            'name': _('Policy'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.policy_id.id,
        }
        
    def action_view_client(self):
        return {
            'name': _('Client'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
        }
        
    def action_view_payment(self):
        return {
            'name': _('Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': self.payment_id.id,
        }
        
    @api.onchange('policy_id')
    def _onchange_policy_id(self):
        if self.policy_id:
            self.partner_id = self.policy_id.partner_id

    @api.model
    def create_expiration_tasks(self):
        """Create tasks for policies expiring in the next 30 days"""
        today = fields.Date.today()
        expiration_date = today + timedelta(days=30)
        
        # Find policies expiring in the next 30 days without existing tasks
        expiring_policies = self.env['sale.order'].search([
            ('is_policy', '=', True),
            ('policy_status', '=', 'sale'),
            ('end_date', '>=', today),
            ('end_date', '<=', expiration_date),
        ])
        
        for policy in expiring_policies:
            existing_task = self.search([
                ('policy_id', '=', policy.id),
                ('task_type', '=', 'expiration'),
                ('state', 'in', ['new', 'in_progress']),
            ], limit=1)
            
            if not existing_task:
                self.create({
                    'name': f"Policy Expiration: {policy.policy_number}",
                    'description': f"The policy {policy.policy_number} for {policy.partner_id.name} is expiring on {policy.end_date}. Contact the client for renewal.",
                    'task_type': 'expiration',
                    'policy_id': policy.id,
                    'partner_id': policy.partner_id.id,
                    'due_date': policy.end_date - timedelta(days=10),
                    'priority': '1',
                })
                
                # Create activity for the policy
                policy.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary=_('Policy Expiration'),
                    note=_('Policy will expire on %s. Contact the client for renewal.') % policy.end_date,
                    date_deadline=policy.end_date - timedelta(days=7),
                    user_id=policy.partner_id.agent_id.id or self.env.user.id
                )
        
        return True
    
    @api.model
    def create_payment_reminder_tasks(self):
        """Create tasks for payments due in the next 7 days"""
        today = fields.Date.today()
        reminder_date = today + timedelta(days=7)
        
        # Find payments due in the next 7 days without existing tasks
        due_payments = self.env['account.payment'].search([
            ('policy_id', '!=', False),
            ('date', '>=', today),
            ('date', '<=', reminder_date),
            ('state', '!=', 'posted'),
        ])
        
        for payment in due_payments:
            existing_task = self.search([
                ('payment_id', '=', payment.id),
                ('task_type', '=', 'payment'),
                ('state', 'in', ['new', 'in_progress']),
            ], limit=1)
            
            if not existing_task:
                policy = payment.policy_id
                self.create({
                    'name': f"Payment Reminder: {policy.policy_number}",
                    'description': f"Payment of {payment.amount} is due on {payment.date} for policy {policy.policy_number}. Remind the client.",
                    'task_type': 'payment',
                    'policy_id': policy.id,
                    'partner_id': payment.partner_id.id,
                    'payment_id': payment.id,
                    'due_date': payment.date - timedelta(days=3),
                    'priority': '1' if (payment.date - today).days <= 3 else '0',
                })
                
                # Create activity for the payment
                msg = _('Payment of %s %s is due on %s') % (payment.amount, payment.currency_id.symbol, payment.date)
                payment.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary=_('Payment Reminder'),
                    note=msg,
                    date_deadline=payment.date - timedelta(days=2),
                    user_id=policy.partner_id.agent_id.id or self.env.user.id
                )
        
        return True


class InsuranceWorkflow(models.Model):
    _name = 'insurance.workflow'
    _description = 'Insurance Workflow'
    
    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    type = fields.Selection([
        ('expiration', 'Policy Expiration'),
        ('payment', 'Payment Reminder'),
        ('approval', 'Policy Approval'),
    ], string="Type", required=True)
    
    days_before = fields.Integer(string="Days Before", default=0,
                              help="For expiration workflows, days before expiration to trigger. For payment workflows, days before due date.")
    
    action_type = fields.Selection([
        ('email', 'Send Email'),
        ('task', 'Create Task'),
        ('activity', 'Create Activity'),
        ('sms', 'Send SMS'),
        ('approve', 'Auto-Approve'),
    ], string="Action Type", required=True)
    
    template_id = fields.Many2one('mail.template', string="Email Template",
                               domain="[('model', 'in', ['sale.order', 'account.payment', 'res.partner'])]")
    
    notify_agent = fields.Boolean(string="Notify Agent", default=True)
    notify_client = fields.Boolean(string="Notify Client", default=True)
    auto_execute = fields.Boolean(string="Auto Execute", default=True)
    
    description = fields.Text(string="Description")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    sequence = fields.Integer(string="Sequence", default=10)
    
    def _run_expiration_workflow(self):
        """Run the expiration workflow for policies"""
        if not self.active:
            return
        
        today = fields.Date.today()
        target_date = today + timedelta(days=self.days_before)
        
        # Find policies expiring on the target date
        policies = self.env['sale.order'].search([
            ('is_policy', '=', True),
            ('policy_status', '=', 'sale'),
            ('end_date', '=', target_date),
        ])
        
        for policy in policies:
            if self.action_type == 'email' and self.template_id:
                # Send email
                if self.notify_client:
                    self.template_id.send_mail(policy.id, force_send=True)
            
            elif self.action_type == 'task':
                # Create task
                self.env['insurance.task'].create({
                    'name': f"Policy Expiration: {policy.policy_number}",
                    'description': f"The policy {policy.policy_number} for {policy.partner_id.name} is expiring on {policy.end_date}.",
                    'task_type': 'expiration',
                    'policy_id': policy.id,
                    'partner_id': policy.partner_id.id,
                    'due_date': today,
                    'priority': '1',
                })
            
            elif self.action_type == 'activity':
                # Create activity
                policy.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary=_('Policy Expiration'),
                    note=_('Policy will expire on %s. Contact the client for renewal.') % policy.end_date,
                    date_deadline=today,
                    user_id=policy.partner_id.agent_id.id if self.notify_agent and policy.partner_id.agent_id else self.env.user.id
                )
            
            elif self.action_type == 'sms' and self.notify_client:
                # Send SMS (requires sms module)
                if hasattr(policy, 'message_post_send_sms') and policy.partner_id.mobile:
                    policy.message_post_send_sms(
                        _('Your policy %s is set to expire on %s. Please contact us for renewal options.') 
                        % (policy.policy_number, policy.end_date)
                    )
    
    def _run_payment_workflow(self):
        """Run the payment workflow for upcoming payments"""
        if not self.active:
            return
        
        today = fields.Date.today()
        target_date = today + timedelta(days=self.days_before)
        
        # Find payments due on the target date
        payments = self.env['account.payment'].search([
            ('policy_id', '!=', False),
            ('date', '=', target_date),
            ('state', '!=', 'posted'),
        ])
        
        for payment in payments:
            policy = payment.policy_id
            
            if self.action_type == 'email' and self.template_id:
                # Send email
                if self.notify_client:
                    self.template_id.send_mail(payment.id, force_send=True)
            
            elif self.action_type == 'task':
                # Create task
                self.env['insurance.task'].create({
                    'name': f"Payment Reminder: {policy.policy_number}",
                    'description': f"Payment of {payment.amount} is due on {payment.date} for policy {policy.policy_number}.",
                    'task_type': 'payment',
                    'policy_id': policy.id,
                    'partner_id': payment.partner_id.id,
                    'payment_id': payment.id,
                    'due_date': today,
                    'priority': '1',
                })
            
            elif self.action_type == 'activity':
                # Create activity
                msg = _('Payment of %s %s is due on %s') % (payment.amount, payment.currency_id.symbol, payment.date)
                payment.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary=_('Payment Reminder'),
                    note=msg,
                    date_deadline=today,
                    user_id=policy.partner_id.agent_id.id if self.notify_agent and policy.partner_id.agent_id else self.env.user.id
                )
            
            elif self.action_type == 'sms' and self.notify_client:
                # Send SMS (requires sms module)
                if hasattr(payment, 'message_post_send_sms') and payment.partner_id.mobile:
                    payment.message_post_send_sms(
                        _('Your payment of %s %s for policy %s is due on %s.') 
                        % (payment.amount, payment.currency_id.symbol, policy.policy_number, payment.date)
                    )
    
    def _run_approval_workflow(self):
        """Run the approval workflow for draft policies"""
        if not self.active:
            return
        
        # Find draft policies
        policies = self.env['sale.order'].search([
            ('is_policy', '=', True),
            ('policy_status', '=', 'draft'),
        ])
        
        for policy in policies:
            if self.action_type == 'email' and self.template_id:
                # Send email notification
                self.template_id.send_mail(policy.id, force_send=True)
            
            elif self.action_type == 'task':
                # Create approval task
                self.env['insurance.task'].create({
                    'name': f"Policy Approval: {policy.policy_number or policy.name}",
                    'description': f"The policy for {policy.partner_id.name} requires approval.",
                    'task_type': 'approval',
                    'policy_id': policy.id,
                    'partner_id': policy.partner_id.id,
                    'due_date': fields.Date.today(),
                    'priority': '1',
                })
            
            elif self.action_type == 'activity':
                # Create activity
                policy.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Policy Approval'),
                    note=_('New policy for %s requires approval.') % policy.partner_id.name,
                    date_deadline=fields.Date.today(),
                    user_id=policy.partner_id.agent_id.id if self.notify_agent and policy.partner_id.agent_id else self.env.user.id
                )
            
            elif self.action_type == 'approve':
                # Auto-approve policy if conditions met
                # This is a simplified example - you would add more logic here
                if policy.amount_total > 0 and policy.order_line:
                    try:
                        policy.action_confirm()
                    except Exception as e:
                        policy.message_post(body=_("Auto-approval failed: %s") % str(e))
    
    @api.model
    def run_workflows(self):
        """Cron job to run all active workflows"""
        workflows = self.search([('active', '=', True)])
        
        for workflow in workflows:
            if workflow.type == 'expiration':
                workflow._run_expiration_workflow()
            elif workflow.type == 'payment':
                workflow._run_payment_workflow()
            elif workflow.type == 'approval':
                workflow._run_approval_workflow()
        
        return True