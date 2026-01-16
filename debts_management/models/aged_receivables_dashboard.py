from odoo import models, fields, api, tools
from datetime import date


PAYMENT_STATE_SELECTION = [
    ("not_paid", "Not Paid"),
    ("in_payment", "In Payment"),
    ("paid", "Paid"),
    ("partial", "Partially Paid"),
    ("reversed", "Reversed"),
    ("blocked", "Blocked"),
    ("invoicing_legacy", "Invoicing App Legacy"),
]


class AgedRreceivablesDashboard(models.Model):
    _name = "aged.receivables.dashboard"
    _description = "Accounts Receivable Dashboard"
    _auto = False  # This is a SQL view, not a regular table

    partner_id = fields.Many2one("res.partner", string="Client", readonly=True)
    partner_region = fields.Char(string="Region", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Account Manager", readonly=True
    )
    invoice_id = fields.Many2one(
        "account.move", string="Invoice", readonly=True
    )
    invoice_name = fields.Char(string="Name", readonly=True)
    invoice_date = fields.Date(string="Invoice Date", readonly=True)
    invoice_due_date = fields.Date(string="Due Date", readonly=True)
    days_overdue = fields.Integer(string="Days Overdue", readonly=True)
    total_due = fields.Monetary(string="Total Amount Due", readonly=True)
    amount_residual = fields.Monetary(
        string="Amount Outstanding", readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", readonly=True
    )
    state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION
        + [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
        ],
        string="Initial Status",
        readonly=True,
    )
    total_remainder_display = fields.Char(
        string="Initial/Remainder", compute="_compute_total_remainder_display"
    )

    @api.depends("invoice_due_date")
    def _compute_days_overdue(self):
        today = date.today()
        for record in self:
            if record.invoice_due_date and record.invoice_due_date < today:
                record.days_overdue = (today - record.invoice_due_date).days
            else:
                record.days_overdue = 0

    @api.depends("amount_residual", "total_due")
    def _compute_total_remainder_display(self):
        for record in self:
            record.total_remainder_display = (
                f"{record.total_due} / {record.total_due - record.amount_residual}"
            )

    def init(self):
        """Create SQL view for AR Dashboard"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    am.id as id,
                    am.name as invoice_name,
                    am.partner_id as partner_id,
                    rp.state_id as partner_region,
                    am.invoice_user_id as user_id,
                    am.id as invoice_id,
                    am.invoice_date as invoice_date,
                    am.invoice_date_due as invoice_due_date,
                    CASE
                        WHEN am.invoice_date_due < CURRENT_DATE
                        THEN CURRENT_DATE - am.invoice_date_due
                        ELSE 0
                    END as days_overdue,
                    am.amount_total as total_due,
                    am.amount_residual as amount_residual,
                    am.currency_id as currency_id,
                    am.state as state
                FROM
                    account_move am
                LEFT JOIN
                    res_partner rp ON am.partner_id = rp.id
                WHERE
                    am.move_type = 'out_invoice'
                    AND am.state = 'posted'
                    AND am.amount_residual > 0
            )
        """
        self.env.cr.execute(query)
