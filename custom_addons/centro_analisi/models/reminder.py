from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class Reminder(models.Model):
    _name = 'centro.analisi.reminder'
    _description = 'Reminder per Analisi'

    analisi_id = fields.Many2one('centro.analisi.analisi', string='Analisi', required=True, ondelete='cascade')
    data_reminder = fields.Date(string='Data Reminder', required=True)
    inviato = fields.Boolean(string='Inviato', default=False)

    @api.model
    def invia_email_reminder(self):
        """Invia email ai clienti per le analisi in scadenza."""
        today = fields.Date.today()
        reminders = self.search([('data_reminder', '=', today), ('inviato', '=', False)])

        for reminder in reminders:
            template = self.env.ref('centro_analisi.email_template_reminder', raise_if_not_found=False)
            if template and reminder.analisi_id.cliente_id.email:
                template.send_mail(reminder.analisi_id.cliente_id.id, force_send=True)
                reminder.inviato = True
                _logger.info(f"Email di reminder inviata a {reminder.analisi_id.cliente_id.email}")

        return True
