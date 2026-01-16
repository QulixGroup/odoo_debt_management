from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def _send_email(self, options):
        """
        Send by email the followup to the customer's followup contacts.

        Override to post the followup email body on unreconciled invoices.
        """
        partner = self.env["res.partner"].browse(options.get("partner_id"))
        followup_line = options.get("followup_line", partner.followup_line_id)
        sent_at_least_once = False
        email_body = None
        for to_send_partner in self._get_email_recipients(options):
            email = to_send_partner.email
            if email and email.strip():
                self = self.with_context(
                    lang=partner.lang or self.env.user.lang
                )
                body_html = self.with_context(
                    mail=True
                ).get_followup_report_html(options)
                email_body = body_html

                # Should contain the followup report and invoice attachments if join_invoices is True.
                attachment_ids = options.get("attachment_ids")

                # If the follow-up was executed manually, the author_id will be set to the ID of the current logged-in user.
                # Otherwise, if the follow-up is automatic, the author_id will be the followup responsible or OdooBot.
                author_id = options.get(
                    "author_id",
                    partner._get_followup_responsible().partner_id.id,
                )

                partner.with_context(
                    mail_post_autofollow=True,
                    mail_notify_author=True,
                    lang=partner.lang or self.env.user.lang,
                ).message_post(
                    partner_ids=[to_send_partner.id],
                    author_id=author_id,
                    email_from=self._get_email_from(options),
                    body=body_html,
                    subject=self._get_email_subject(options),
                    reply_to=self._get_email_reply_to(options),
                    model_description=_("payment reminder"),
                    email_layout_xmlid="mail.mail_notification_light",
                    attachment_ids=attachment_ids,
                    subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_note"
                    ),
                )
                sent_at_least_once = True

                # add additional followers to the partner's chatter
                if followup_line and followup_line.additional_follower_ids:
                    partner.message_subscribe(
                        followup_line.additional_follower_ids.partner_id.ids
                    )
        if not sent_at_least_once:
            raise UserError(
                _(
                    "You are trying to send an Email, but no follow-up contact has any email address set for customer '%s'",
                    partner.name,
                )
            )
        if not (email_body and options.get("unreconciled_invoice_ids")):
            return

        unreconciled_invoices = self.env["account.move"].browse(
            options.get("unreconciled_invoice_ids")
        )
        for invoice in unreconciled_invoices:
            invoice.message_post(body=email_body)
