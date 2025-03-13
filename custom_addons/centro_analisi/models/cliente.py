from odoo import models, fields

class Cliente(models.Model):
    _inherit = 'res.partner'  # NON usare _name!

    analisi_ids = fields.One2many(
        'centro.analisi.analisi',  # Nome della tabella di destinazione
        'partner_id',              # Nome del campo Many2one nella tabella Analisi
        string='Storico Analisi'
    )