from odoo import models, fields

class Analisi(models.Model):
    _name = 'centro.analisi.analisi'
    _description = 'Analisi Cliente'

    partner_id = fields.Many2one(
        'res.partner',  # 🔥 Cambiato da 'centro.analisi.cliente' a 'res.partner'
        string='Cliente',
        required=True,
        ondelete='cascade'
    )
    
    tipo_analisi_id = fields.Many2many(
        'centro.analisi.tipianalisi',
        string='Tipo di Analisi',
        required=True,
        ondelete='cascade'  
)
    
    data_effettuata = fields.Date(string='Data Effettuata', required=True)
    data_scadenza = fields.Date(string='Data Scadenza', required=True)
