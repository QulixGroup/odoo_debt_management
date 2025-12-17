import datetime

from odoo import models, fields, api


class DebtPromisePayment(models.Model):
    _name = "debt.promise.payment"
    _description = "Debt Payment Promise"
    _order = "promise_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    partner_id = fields.Many2one(
        "res.partner", string="Partner", required=True, ondelete="cascade"
    )
    promise_date = fields.Date(string="Promise Date", required=True)
    amount = fields.Monetary(
        string="Amount", required=True, currency_field="currency_id"
    )
    invoice_ids = fields.Many2many(
        "account.move",
        string="Related Invoices",
        help="Invoices related to this payment promise",
    )
    note = fields.Text(string="Note")
    account_payment_id = fields.Many2one(
        "account.payment", string="Payment", readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection(
        [("pending", "Pending"), ("paid", "Paid"), ("overdue", "Overdue")],
        string="Status",
        compute="_compute_state",
        store=True,
    )
    reminder_sent = fields.Boolean(string="Reminder Sent", default=False)

    @api.depends("promise_date", "account_payment_id")
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            if record.account_payment_id:
                record.state = "paid"
            elif record.promise_date and record.promise_date < today:
                record.state = "overdue"
            else:
                record.state = "pending"

    @api.model
    def _cron_send_payment_reminders(self):
        """Send reminder emails for promises due tomorrow"""
        tomorrow = fields.Date.today() + datetime.timedelta(days=1)
        promises = self.search(
            [
                ("promise_date", "=", tomorrow),
                ("account_payment_id", "=", False),
                ("reminder_sent", "=", False),
                ("partner_id.email", "!=", False),
            ]
        )

        template = self.env.ref(
            "debt_management.email_template_payment_promise_reminder"
        )
        for promise in promises:
            template.send_mail(promise.id, force_send=True)
            promise.reminder_sent = True

    def assign_status(self):
        """Assign status based on payment and due date."""
        today = datetime.date.today()
        promises_to_process = self.env["debt.promise.payment"].search([
                ("state", "!=", "paid")
        ])
        for promise in promises_to_process:
            if promise.account_payment_id:
                promise.state = "paid"
            elif promise.promise_date and promise.promise_date < today:
                promise.state = "overdue"
            else:
                promise.state = "pending"
