from odoo import models, fields, api
from datetime import timedelta


class CentroAnalisiDashboard(models.Model):
    _name = 'centro.analisi.dashboard'
    _description = 'Dashboard Centro Analisi'

    total_analisi = fields.Integer(string="Totale Analisi", compute="_compute_total_analisi")
    analisi_in_scadenza = fields.Integer(string="Analisi in Scadenza", compute="_compute_analisi_in_scadenza")
    clienti_totali = fields.Integer(string="Totale Clienti", compute="_compute_clienti_totali")
    tipo_analisi_counts = fields.Json(string="Distribuzione Analisi", compute="_compute_tipo_analisi_counts")

    @api.model
    def create_dashboard_record(self):
        """ Crea un record fittizio per permettere il caricamento della dashboard """
        existing_record = self.env['centro.analisi.dashboard'].search([], limit=1)
        if not existing_record:
            self.create({})

    @api.depends()
    def _compute_total_analisi(self):
        self.total_analisi = self.env['centro.analisi.analisi'].search_count([])

    @api.depends()
    def _compute_analisi_in_scadenza(self):
        today = fields.Date.today()
        next_30_days = today + timedelta(days=30)

        self.analisi_in_scadenza = self.env['centro.analisi.analisi'].search_count([
            ('data_scadenza', '>', today),  # Dopo oggi
            ('data_scadenza', '<=', next_30_days)  # Entro 30 giorni
        ])

    @api.depends()
    def _compute_clienti_totali(self):
        self.clienti_totali = self.env['res.partner'].search_count([])

    @api.depends()
    def _compute_tipo_analisi_counts(self):
        analisi_data = self.env['centro.analisi.analisi'].read_group(
            [('tipo_analisi_id', '!=', False)],  # Filtra solo analisi con tipo valido
            ['tipo_analisi_id'],                 # Raggruppa per tipo di analisi
            ['tipo_analisi_id']                  # Conteggio automatico
        )

        # Costruisce il dizionario corretto per il grafico Odoo
        counts = {d['tipo_analisi_id'][1]: d['tipo_analisi_id_count'] for d in analisi_data if d['tipo_analisi_id']}

        # Salva i dati come JSON (Odoo lo supporta direttamente)
        self.tipo_analisi_counts = counts