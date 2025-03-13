from odoo import models, fields

class TipiAnalisi(models.Model):
    _name = 'centro.analisi.tipianalisi'
    _description = 'Tipi di Analisi'

    name = fields.Char(string='Nome', required=True)