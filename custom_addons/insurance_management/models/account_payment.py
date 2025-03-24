from odoo import models, fields, api, _

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    policy_id = fields.Many2one('sale.order', string="Insurance Policy", 
                              domain=[('is_policy', '=', True)],
                              help="Related insurance policy")
    is_policy_payment = fields.Boolean(string="Is Policy Payment", compute="_compute_is_policy_payment", store=True)
    installment_number = fields.Char(string="Installment", compute="_compute_installment_info", store=True)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('late', 'Late'),
    ], string="Payment Status", compute="_compute_payment_status", store=True)
    
    @api.depends('policy_id')
    def _compute_is_policy_payment(self):
        for payment in self:
            payment.is_policy_payment = bool(payment.policy_id)
    
    @api.depends('policy_id', 'payment_reference')
    def _compute_installment_info(self):
        for payment in self:
            installment_number = ''
            if payment.policy_id and payment.payment_reference:
                # Try to extract installment info from reference
                if 'Installment' in payment.payment_reference:
                    installment_number = payment.payment_reference.split('Installment')[-1].strip()
            payment.installment_number = installment_number
    
    @api.depends('state', 'date')
    def _compute_payment_status(self):
        today = fields.Date.today()
        for payment in self:
            if payment.state == 'posted':
                payment.payment_status = 'paid'
            elif payment.date and payment.date < today:
                payment.payment_status = 'late'
            else:
                payment.payment_status = 'pending'