from odoo import models, fields, Command
from odoo.exceptions import UserError
from odoo.addons.mail.models.mail_composer_mixin import MailComposerMixin


class SendReminderWizard(models.TransientModel):
    # _name = "send.reminder.wizard"
    _inherit = 'account_followup.manual_reminder'
    _description = "Send Payment Reminder Wizard"

    invoice_id = fields.Many2one(comodel_name='account.move')

    def default_get(self, fields_list):
        """Override to get the invoice from context and set defaults accordingly."""
        if not (chosen_invoices := self.env.context['active_ids']):
            raise UserError(
                "No active invoices found to send reminders for. "
                "Choose one invoice."
            )
        if len(chosen_invoices) > 1:
            raise UserError(
                "Please select only one invoice to send a reminder."
            )
        defaults = super(MailComposerMixin, self).default_get(fields_list)
        invoice = self.env['account.move'].browse(chosen_invoices[0])
        partner = invoice.partner_id
        partner.ensure_one()
        followup_line = partner.followup_line_id
        if followup_line:
            defaults.update(self._get_defaults_from_followup_line(followup_line))
        defaults.update(
            partner_id=partner.id,
            attachment_ids=[Command.set(partner.unreconciled_aml_ids.move_id.message_main_attachment_id.ids)],
            render_model='res.partner',
            invoice_id=invoice.id,
        )
        return defaults

    def _get_wizard_options(self):
        """Get options specific to this wizard."""
        res = super(SendReminderWizard, self)._get_wizard_options()
        res.update({'invoice_id': self.invoice_id.id})
        return res
