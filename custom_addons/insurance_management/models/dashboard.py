from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import json
import random
from dateutil.relativedelta import relativedelta

class InsuranceDashboard(models.Model):
    _name = 'insurance.dashboard'
    _description = 'Insurance Dashboard'
    _rec_name = 'name'
    
    # Override default search to always show dashboard record
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if not count:
            # Check if dashboard exists, if not create it
            if not self.search_count([]):
                self.create({'name': 'Insurance Dashboard'})
        return super(InsuranceDashboard, self).search(args, offset, limit, order, count)
    
    name = fields.Char(default="Dashboard", readonly=True)
    date_from = fields.Date(string="From Date", default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string="To Date", default=lambda self: fields.Date.today())
    
    # Policy Statistics
    total_policies = fields.Integer(string="Total Policies", compute="_compute_policy_statistics")
    active_policies = fields.Integer(string="Active Policies", compute="_compute_policy_statistics")
    draft_policies = fields.Integer(string="Draft Policies", compute="_compute_policy_statistics")
    expired_policies = fields.Integer(string="Expired Policies", compute="_compute_policy_statistics")
    
    # Revenue Statistics
    total_premium = fields.Monetary(string="Total Premium", compute="_compute_revenue_statistics", currency_field='company_currency_id')
    paid_premium = fields.Monetary(string="Paid Premium", compute="_compute_revenue_statistics", currency_field='company_currency_id')
    pending_premium = fields.Monetary(string="Pending Premium", compute="_compute_revenue_statistics", currency_field='company_currency_id')
    overdue_premium = fields.Monetary(string="Overdue Premium", compute="_compute_revenue_statistics", currency_field='company_currency_id')
    
    # Risk Profile
    vehicles_with_theft = fields.Integer(string="Vehicles with Theft Coverage", compute="_compute_risk_profile")
    vehicles_with_fire = fields.Integer(string="Vehicles with Fire Coverage", compute="_compute_risk_profile")
    vehicles_with_black_box = fields.Integer(string="Vehicles with Black Box", compute="_compute_risk_profile")
    average_premium = fields.Monetary(string="Average Premium", compute="_compute_risk_profile", currency_field='company_currency_id')
    
    # Sales Performance
    policies_by_agent = fields.Text(string="Policies by Agent", compute="_compute_sales_performance")
    premium_by_agent = fields.Text(string="Premium by Agent", compute="_compute_sales_performance")
    
    # Currency field
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Currency")
    
    # Method for the dashboard_graph widget
    def get_dashboard_data(self, field_name):
        self.ensure_one()
        
        # Define different graph data based on field name
        if field_name == 'active_policies':
            return self._get_policy_statistics_graph_data()
        elif field_name == 'total_premium':
            return self._get_revenue_statistics_graph_data()
        elif field_name == 'vehicles_with_theft':
            return self._get_risk_profile_graph_data()
        
        # Default return empty data
        return {'values': []}
    
    def _get_policy_statistics_graph_data(self):
        # Create graph data for the policy statistics
        data = {
            'values': [
                {'label': 'Active', 'value': self.active_policies, 'color': '#28a745'},
                {'label': 'Draft', 'value': self.draft_policies, 'color': '#ffc107'},
                {'label': 'Expired', 'value': self.expired_policies, 'color': '#dc3545'},
            ]
        }
        return data
    
    def _get_revenue_statistics_graph_data(self):
        # Create graph data for premium distribution
        data = {
            'values': [
                {'label': 'Paid', 'value': float(self.paid_premium), 'color': '#28a745'},
                {'label': 'Pending', 'value': float(self.pending_premium), 'color': '#ffc107'},
                {'label': 'Overdue', 'value': float(self.overdue_premium), 'color': '#dc3545'},
            ]
        }
        return data
    
    def _get_risk_profile_graph_data(self):
        # Create graph data for risk profile
        data = {
            'values': [
                {'label': 'Theft Coverage', 'value': self.vehicles_with_theft, 'color': '#17a2b8'},
                {'label': 'Fire Coverage', 'value': self.vehicles_with_fire, 'color': '#fd7e14'},
                {'label': 'Black Box', 'value': self.vehicles_with_black_box, 'color': '#6c757d'},
            ]
        }
        return data
    
    @api.depends('date_from', 'date_to')
    def _compute_policy_statistics(self):
        today = fields.Date.today()
        
        for record in self:
            # Total policies
            record.total_policies = self.env['sale.order'].search_count([
                ('is_policy', '=', True),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Active policies
            record.active_policies = self.env['sale.order'].search_count([
                ('is_policy', '=', True),
                ('policy_status', '=', 'sale'),
                ('end_date', '>=', today),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Draft policies
            record.draft_policies = self.env['sale.order'].search_count([
                ('is_policy', '=', True),
                ('policy_status', 'in', ['draft', 'sent']),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Expired policies
            record.expired_policies = self.env['sale.order'].search_count([
                ('is_policy', '=', True),
                ('policy_status', '=', 'sale'),
                ('end_date', '<', today),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
    
    @api.depends('date_from', 'date_to')
    def _compute_revenue_statistics(self):
        today = fields.Date.today()
        
        for record in self:
            # Get policies within date range
            policies = self.env['sale.order'].search([
                ('is_policy', '=', True),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Calculate total premium
            record.total_premium = sum(policies.mapped('amount_total'))
            
            # Calculate paid premium
            paid_amount = 0
            pending_amount = 0
            overdue_amount = 0
            
            for policy in policies:
                # Get payments related to this policy
                payments = self.env['account.payment'].search([
                    ('policy_id', '=', policy.id)
                ])
                
                # Paid amount
                paid_amount += sum(payments.filtered(lambda p: p.state == 'posted').mapped('amount'))
                
                # Pending amount for payments due in the future
                pending_amount += sum(payments.filtered(lambda p: p.state != 'posted' and p.date > today).mapped('amount'))
                
                # Overdue amount for payments due in the past
                overdue_amount += sum(payments.filtered(lambda p: p.state != 'posted' and p.date <= today).mapped('amount'))
            
            record.paid_premium = paid_amount
            record.pending_premium = pending_amount
            record.overdue_premium = overdue_amount
    
    @api.depends('date_from', 'date_to')
    def _compute_risk_profile(self):
        for record in self:
            # Get policies within date range
            policies = self.env['sale.order'].search([
                ('is_policy', '=', True),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Count vehicles with different coverages
            record.vehicles_with_theft = len(policies.filtered(lambda p: p.has_theft_coverage))
            record.vehicles_with_fire = len(policies.filtered(lambda p: p.has_fire_coverage))
            record.vehicles_with_black_box = len(policies.filtered(lambda p: p.has_black_box))
            
            # Calculate average premium
            if policies:
                record.average_premium = sum(policies.mapped('amount_total')) / len(policies)
            else:
                record.average_premium = 0
    
    @api.depends('date_from', 'date_to')
    def _compute_sales_performance(self):
        for record in self:
            # Get all policies in date range
            policies = self.env['sale.order'].search([
                ('is_policy', '=', True),
                ('create_date', '>=', record.date_from),
                ('create_date', '<=', record.date_to)
            ])
            
            # Group policies by agent
            agents = {}
            agent_premium = {}
            
            for policy in policies:
                agent = policy.partner_id.agent_id.name or "No Agent"
                
                if agent not in agents:
                    agents[agent] = 0
                agents[agent] += 1
                
                if agent not in agent_premium:
                    agent_premium[agent] = 0
                agent_premium[agent] += policy.amount_total
            
            # Format text for display
            policies_by_agent = ""
            for agent, count in agents.items():
                policies_by_agent += f"{agent}: {count} policies\n"
            
            premium_by_agent = ""
            for agent, premium in agent_premium.items():
                premium_by_agent += f"{agent}: {record.company_currency_id.symbol} {premium:.2f}\n"
            
            record.policies_by_agent = policies_by_agent
            record.premium_by_agent = premium_by_agent
            
    def action_view_policy_list(self):
        return {
            'name': 'Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('is_policy', '=', True)],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_customer_list(self):
        return {
            'name': 'Insurance Customers',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('is_company', '=', False)],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_graph(self):
        """Opens a separate action to show dashboard graphs"""
        self.ensure_one()
        
        # Get action from XML id
        action = self.env.ref('insurance_management.action_insurance_dashboard').read()[0]
        
        # Switch to graph view
        action.update({
            'name': 'Insurance Dashboard Graphs',
            'view_mode': 'graph',
            'views': [(self.env.ref('insurance_management.view_insurance_dashboard_graph').id, 'graph')],
            'domain': [('id', '=', self.id)],
            'context': {'create': False, 'edit': False, 'graph_measure': 'active_policies'},
        })
        
        return action
        
    # Policy Statistics Actions
    def action_view_all_policies(self):
        """View all policies"""
        return {
            'name': 'All Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_active_policies(self):
        """View only active policies"""
        today = fields.Date.today()
        return {
            'name': 'Active Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('policy_status', '=', 'sale'),
                ('end_date', '>=', today),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_draft_policies(self):
        """View draft policies"""
        return {
            'name': 'Draft Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('policy_status', 'in', ['draft', 'sent']),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_expired_policies(self):
        """View expired policies"""
        today = fields.Date.today()
        return {
            'name': 'Expired Insurance Policies',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('policy_status', '=', 'sale'),
                ('end_date', '<', today),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    # Revenue Statistics Actions
    def action_view_policies_with_premium(self):
        """View all policies with premium amounts"""
        return {
            'name': 'Policies with Premium',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('amount_total', '>', 0),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_paid_payments(self):
        """View paid payments"""
        today = fields.Date.today()
        return {
            'name': 'Paid Policy Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [
                ('policy_id', '!=', False),
                ('state', '=', 'posted'),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_pending_payments(self):
        """View pending payments"""
        today = fields.Date.today()
        return {
            'name': 'Pending Policy Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [
                ('policy_id', '!=', False),
                ('state', '!=', 'posted'),
                ('date', '>', today),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_overdue_payments(self):
        """View overdue payments"""
        today = fields.Date.today()
        return {
            'name': 'Overdue Policy Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [
                ('policy_id', '!=', False),
                ('state', '!=', 'posted'),
                ('date', '<=', today),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    # Risk Profile Actions
    def action_view_theft_coverage(self):
        """View policies with theft coverage"""
        return {
            'name': 'Policies with Theft Coverage',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('has_theft_coverage', '=', True),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_fire_coverage(self):
        """View policies with fire coverage"""
        return {
            'name': 'Policies with Fire Coverage',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('has_fire_coverage', '=', True),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }
        
    def action_view_black_box(self):
        """View policies with black box"""
        return {
            'name': 'Policies with Black Box',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('is_policy', '=', True),
                ('has_black_box', '=', True),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to)
            ],
            'context': {'search_default_filter_date': 1},
        }