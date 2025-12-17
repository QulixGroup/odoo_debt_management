from odoo import models, fields


class DebtPromiseWizard(models.TransientModel):
    _name = "debt.promise.wizard"
    _description = "Create Payment Promise"

    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    promise_date = fields.Date(
        string="Promise Date", required=True, default=fields.Date.today
    )
    amount = fields.Monetary(
        string="Amount", required=True, currency_field="currency_id"
    )
    note = fields.Text(
        string="Note", help="What the client said about the payment"
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    invoice_ids = fields.Many2many(
        "account.move",
        string="Related Invoices",
        help="Invoices related to this payment promise",
    )

    def action_create_promise(self):
        self.ensure_one()
        self.env["debt.promise.payment"].create(
            {
                "partner_id": self.partner_id.id,
                "promise_date": self.promise_date,
                "amount": self.amount,
                "note": self.note,
                "currency_id": self.currency_id.id,
                "invoice_ids": [(6, 0, self.invoice_ids.ids)],
            }
        )
        return {"type": "ir.actions.act_window_close"}
