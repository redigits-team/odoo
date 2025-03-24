from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Insurance-specific fields
    tax_id_number = fields.Char(string="Tax ID Number", help="Customer's tax identification number")
    profession = fields.Char(string="Profession", help="Customer's profession or occupation")
    agent_id = fields.Many2one('res.users', string="Insurance Agent", 
                              domain=[('share', '=', False)],
                              help="Salesperson responsible for managing this customer's policies")
    is_insurance_agent = fields.Boolean(string="Is Insurance Agent", 
                                      help="Check if this partner is an insurance agent")
    policy_count = fields.Integer(string="Policies", compute="_compute_policy_count", store=True)
    
    @api.depends('sale_order_ids')
    def _compute_policy_count(self):
        for partner in self:
            partner.policy_count = self.env['sale.order'].search_count([
                ('partner_id', '=', partner.id),
                ('is_policy', '=', True),
                ('state', 'not in', ['draft', 'cancel'])
            ])
    
    def action_view_policies(self):
        self.ensure_one()
        action = self.env.ref('insurance_management.action_insurance_policies').read()[0]
        action['domain'] = [
            ('partner_id', '=', self.id),
            ('is_policy', '=', True),
        ]
        return action