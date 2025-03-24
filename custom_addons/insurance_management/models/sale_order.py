from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Policy fields
    is_policy = fields.Boolean(string="Is Insurance Policy", default=True, 
                             help="Identifies this sales order as an insurance policy")
    policy_number = fields.Char(string="Policy Number", readonly=True, copy=False,
                              help="Unique identifier for the policy")
    policy_status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Policy Active'),
        ('cancel', 'Cancelled'),
    ], string="Policy Status", related="state", store=True)
    
    # Insurance policy date fields
    start_date = fields.Date(string="Start Date", help="Policy start date")
    end_date = fields.Date(string="End Date", help="Policy end date")
    next_payment_date = fields.Date(string="Next Payment Date", compute="_compute_next_payment", store=True,
                                  help="Date when the next payment is due")
    duration_months = fields.Integer(string="Duration (Months)", default=12,
                                   help="Policy duration in months")
    
    # Vehicle details
    vehicle_license_plate = fields.Char(string="License Plate", help="Vehicle license plate number")
    vehicle_brand = fields.Char(string="Vehicle Brand", help="Vehicle manufacturer")
    vehicle_model = fields.Char(string="Vehicle Model", help="Vehicle model")
    vehicle_year = fields.Integer(string="Year", help="Year of manufacture")
    
    # Coverage options
    has_theft_coverage = fields.Boolean(string="Theft Coverage", help="Includes theft protection")
    has_fire_coverage = fields.Boolean(string="Fire Coverage", help="Includes fire protection")
    has_black_box = fields.Boolean(string="Black Box", help="Includes black box device")
    has_assistance = fields.Boolean(string="Roadside Assistance", help="Includes roadside assistance")
    
    # Payment options
    payment_frequency = fields.Selection([
        ('annual', 'Annual'),
        ('semiannual', 'Semi-Annual'),
        ('quarterly', 'Quarterly'),
        ('monthly', 'Monthly')
    ], string="Payment Frequency", default='annual', required=True)
    installment_count = fields.Integer(string="Number of Installments", compute="_compute_installment_count")
    installment_amount = fields.Monetary(string="Installment Amount", compute="_compute_installment_amount")
    payment_ids = fields.One2many('account.payment', 'policy_id', string="Payments")
    payment_count = fields.Integer(string="Payment Count", compute="_compute_payment_count")
    
    @api.model
    def create(self, vals):
        if vals.get('is_policy', True):
            if not vals.get('policy_number') and vals.get('state') not in ['draft', 'cancel']:
                sequence = self.env['ir.sequence'].next_by_code('insurance.policy')
                vals['policy_number'] = sequence or '/'
        
        # Calculate end date based on start date and duration
        if vals.get('start_date') and vals.get('duration_months'):
            start_date = fields.Date.from_string(vals.get('start_date'))
            vals['end_date'] = start_date + relativedelta(months=vals.get('duration_months'))
            
        return super(SaleOrder, self).create(vals)
    
    @api.onchange('start_date', 'duration_months')
    def _onchange_policy_duration(self):
        if self.start_date and self.duration_months:
            self.end_date = self.start_date + relativedelta(months=self.duration_months)
    
    @api.onchange('has_theft_coverage', 'has_fire_coverage', 'has_black_box', 'has_assistance')
    def _onchange_coverage_options(self):
        """Trigger premium recalculation when coverage options change"""
        if not self.order_line:
            return
            
        # Here you would typically implement your premium calculation logic
        # This is a simplified example
        self._calculate_premium()
    
    def _calculate_premium(self):
        """Calculate insurance premium based on selected coverage options"""
        # This is a simplified example - real implementation would have more complex logic
        base_premium = 500.0
        
        if self.has_theft_coverage:
            base_premium += 200.0
        if self.has_fire_coverage:
            base_premium += 150.0
        if self.has_black_box:
            base_premium -= 50.0  # discount for having black box
        if self.has_assistance:
            base_premium += 100.0
            
        # Find the product to use for the premium line
        insurance_product = self.env['product.product'].search([
            ('default_code', '=', 'INS_PREMIUM')
        ], limit=1)
        
        if not insurance_product:
            return
            
        # Update or create the premium order line
        premium_line = self.order_line.filtered(lambda l: l.product_id.id == insurance_product.id)
        if premium_line:
            premium_line.write({
                'price_unit': base_premium,
                'name': _('Insurance Premium'),
            })
        else:
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': insurance_product.id,
                'name': _('Insurance Premium'),
                'product_uom_qty': 1,
                'price_unit': base_premium,
            })
    
    @api.depends('payment_frequency')
    def _compute_installment_count(self):
        for policy in self:
            if policy.payment_frequency == 'annual':
                policy.installment_count = 1
            elif policy.payment_frequency == 'semiannual':
                policy.installment_count = 2
            elif policy.payment_frequency == 'quarterly':
                policy.installment_count = 4
            elif policy.payment_frequency == 'monthly':
                policy.installment_count = 12
            else:
                policy.installment_count = 1
    
    @api.depends('amount_total', 'installment_count')
    def _compute_installment_amount(self):
        for policy in self:
            if policy.installment_count > 0:
                policy.installment_amount = policy.amount_total / policy.installment_count
            else:
                policy.installment_amount = policy.amount_total
    
    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for policy in self:
            policy.payment_count = len(policy.payment_ids)
    
    @api.depends('payment_ids', 'payment_ids.date')
    def _compute_next_payment(self):
        today = fields.Date.today()
        for policy in self:
            next_payment = False
            future_payments = policy.payment_ids.filtered(
                lambda p: p.date and p.date > today and p.state != 'cancelled'
            ).sorted('date')
            
            if future_payments:
                next_payment = future_payments[0].date
            
            policy.next_payment_date = next_payment
    
    def action_create_payments(self):
        """Create installment payments based on payment frequency"""
        self.ensure_one()
        if self.state not in ['sale']:
            raise UserError(_("You can only create payments for confirmed policies."))
            
        # Check if payments already exist
        if self.payment_ids:
            raise UserError(_("Payments already exist for this policy."))
            
        # Create payment records
        payment_vals = []
        start_date = self.start_date or fields.Date.today()
        
        for i in range(self.installment_count):
            if self.payment_frequency == 'annual':
                payment_date = start_date
            elif self.payment_frequency == 'semiannual':
                payment_date = start_date + relativedelta(months=i*6)
            elif self.payment_frequency == 'quarterly':
                payment_date = start_date + relativedelta(months=i*3)
            elif self.payment_frequency == 'monthly':
                payment_date = start_date + relativedelta(months=i)
                
            # Create the payment
            self.env['account.payment'].create({
                'policy_id': self.id,
                'partner_id': self.partner_id.id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'amount': self.installment_amount,
                'date': payment_date,
                'ref': f"Policy {self.policy_number} - Installment {i+1}/{self.installment_count}",
            })
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('Policy Payments'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
        }
    
    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Policy Payments'),
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
        }
    
    def action_confirm(self):
        """Override to add policy-specific behavior on confirmation"""
        for order in self:
            if order.is_policy and not order.policy_number:
                order.policy_number = self.env['ir.sequence'].next_by_code('insurance.policy')
        return super(SaleOrder, self).action_confirm()
        
    @api.model
    def _run_insurance_daily_tasks(self):
        """Scheduled action method to run daily insurance tasks"""
        today = fields.Date.today()
        
        # Identify policies expiring in the next 30 days
        expiring_policies = self.search([
            ('is_policy', '=', True),
            ('policy_status', '=', 'sale'),
            ('end_date', '>=', today),
            ('end_date', '<=', today + relativedelta(days=30)),
        ])
        
        # Process expiring policies
        for policy in expiring_policies:
            # Create activity for policy expiration
            policy.activity_schedule(
                'mail.mail_activity_data_call',
                summary=_('Policy Expiration'),
                note=_('Policy %s will expire on %s. Contact the client for renewal.') % 
                     (policy.policy_number, policy.end_date),
                date_deadline=policy.end_date - relativedelta(days=7),
                user_id=policy.partner_id.agent_id.id or self.env.user.id
            )
        
        # Find upcoming payments due in the next 7 days
        upcoming_payments = self.env['account.payment'].search([
            ('policy_id', '!=', False),
            ('state', '!=', 'posted'),
            ('date', '>=', today),
            ('date', '<=', today + relativedelta(days=7)),
        ])
        
        # Process upcoming payments
        for payment in upcoming_payments:
            payment.activity_schedule(
                'mail.mail_activity_data_call',
                summary=_('Payment Reminder'),
                note=_('Payment of %s %s is due on %s for policy %s.') % 
                     (payment.amount, payment.currency_id.symbol, payment.date, 
                      payment.policy_id.policy_number),
                date_deadline=payment.date - relativedelta(days=2),
                user_id=payment.policy_id.partner_id.agent_id.id or self.env.user.id
            )
        
        return True