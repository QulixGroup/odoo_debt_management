from datetime import timedelta

from odoo import api, fields, models


class AccountFollowupPendingCheck(models.Model):
    _name = "account.followup.pending.check"
    _description = "Pending Follow-up Response Check"

    partner_id = fields.Many2one(
        "res.partner", string="Partner", required=True, index=True
    )
    followup_line_id = fields.Many2one(
        "account_followup.followup.line",
        string="Follow-up Level",
        required=True,
    )
    send_date = fields.Date(
        string="Send Date", default=fields.Date.today(), required=True
    )
    expected_response_date = fields.Date(
        string="Expected Response Date",
        compute="_compute_expected_response_date",
        store=True,
    )
    responded = fields.Boolean(string="Responded", default=False)

    @api.depends("send_date", "followup_line_id.response_wait_days")
    def _compute_expected_response_date(self):
        for record in self:
            wait_days = record.followup_line_id.response_wait_days or 0
            record.expected_response_date = record.send_date + timedelta(
                days=wait_days
            )

    @api.model
    def check_pending_responses(self):
        """Cron method to check for responses and schedule activities if needed."""
        today = fields.Date.today()
        pendings = self.search(
            [("expected_response_date", "<=", today), ("responded", "=", False)]
        )
        # partner should have at most 1 pending response check
        for pending in pendings:
            invoice_ids = (
                self.env["account.move"]
                .search(
                    [
                        ("partner_id", "=", pending.partner_id.id),
                        ("move_type", "=", "out_invoice"),
                    ]
                )
                .ids
            )
            res_ids = [pending.partner_id.id] + invoice_ids

            # any response from partner since we had sent last reminder is considered as relevant
            responses = self.env["mail.message"].search(
                [
                    ("author_id", "=", pending.partner_id.id),
                    ("date", ">", pending.send_date),
                    ("message_type", "in", ("email", "comment")),
                    ("model", "in", ("res.partner", "account.move")),
                    ("res_id", "in", res_ids),
                ]
            )
            if responses:
                pending.responded = True
                continue

            followup_line = pending.followup_line_id
            user = pending.partner_id._get_followup_responsible()
            activity_data = {
                "activity_type_id": followup_line.activity_type_id
                and followup_line.activity_type_id.id
                or self._default_activity_type().id,
                "note": followup_line.activity_note,
                "summary": followup_line.activity_summary,
                "user_id": user.id,
                "date_deadline": today,
            }
            pending.partner_id.activity_schedule(**activity_data)
            for invoice in pending.partner_id.overdue_invoice_ids:
                invoice.activity_schedule(**activity_data)
            pending.unlink()
