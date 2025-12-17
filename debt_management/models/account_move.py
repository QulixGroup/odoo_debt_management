from odoo import api, fields, models
from datetime import date


class AccountMoveDebtManagement(models.Model):
    _inherit = "account.move"

    payment_state = fields.Selection(
        selection_add=[
            ("expecting_payment", "Expecting Payment"),
        ]
    )

    invoice_overdue_days = fields.Integer(
        string="Overdue Days",
        compute="_compute_invoice_overdue_days",
        store=False,
    )

    total_return_display = fields.Char(
        string="Total / Received",
        compute="_compute_total_remainder_display",
        store=False,
    )

    last_notification_date = fields.Date(
        string="Last Notification Date",
        compute="_compute_reminder_date_and_count",
        store=False,
    )
    notification_count = fields.Integer(
        string="Notifications Sent",
        compute="_compute_reminder_date_and_count",
        store=False,
    )
    is_disputed = fields.Boolean("In Dispute", default=False)
    is_in_collection = fields.Boolean("In Collection", default=False)

    @api.depends("message_ids", "activity_ids")
    def _compute_reminder_date_and_count(self):
        """
        Calculate number of notifications sent for an outstanding invoice.

        And last notification date.
        A notification is defined as an email message
        related to the invoice, sent/created on or after the invoice due date.
        """
        for move in self:
            counter = 0
            last_message_date = None
            reminder_messages = move.message_ids.filtered(
                    lambda m: m.res_id == move.id and m.body
                    and m.date.date() >= move.invoice_date_due
                )
            if reminder_messages:
                last_message = max(reminder_messages.mapped("date"))
                last_message_date = last_message.date()
                counter = len(reminder_messages)
            # if move.activity_ids:
                # TODO: refine to only count relevant activities

            move.notification_count = counter
            move.last_notification_date = last_message_date

    @api.depends("invoice_date_due", "state", "payment_state")
    def _compute_invoice_overdue_days(self):
        """Calculate days overdue for unpaid invoices"""
        today = date.today()
        for move in self:
            if (
                move.invoice_date_due
                and move.state == "posted"
                and move.payment_state in ("not_paid", "partial")
            ):
                delta = today - move.invoice_date_due
                move.invoice_overdue_days = max(0, delta.days)
            else:
                move.invoice_overdue_days = 0

    @api.depends("amount_total", "amount_residual")
    def _compute_total_remainder_display(self):
        """Combine total and return with / separator"""
        for move in self:
            total = move.amount_total
            current_return = total - move.amount_residual
            move.total_return_display = f"{total:,.2f} / {current_return:,.2f}"
