from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_validate(self):
        """Link payment to matching promises after validation.

        Override the standard action_validate method to associate payments
        with any debt payment promises related to the invoices being paid.
        """
        res = super(AccountPayment, self).action_validate()
        for payment in self:
            invoices = (
                self.invoice_ids | self.reconciled_invoice_ids
            ).with_context(create=False)

            if not invoices:
                continue

            promises = self.env["debt.promise.payment"].search(
                [
                    ("partner_id", "=", payment.partner_id.id),
                    ("invoice_ids", "in", invoices.ids),
                ],
                order="promise_date asc",
            )
            # works even if there are no promises
            promises.account_payment_id = payment.id
        return res
