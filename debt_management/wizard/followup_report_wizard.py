from odoo import models, fields
from datetime import timedelta

TOP_DEBTORS_NUMBER = 10


class FollowupReportWizard(models.TransientModel):
    _name = "followup.report.wizard"
    _description = "Follow-up Report Wizard"

    period_days = fields.Integer(
        string="Period (Days)", default=30, required=True
    )
    salesperson_ids = fields.Many2many("res.users", string="Salespersons")
    partner_category_ids = fields.Many2many(
        "res.partner.category", string="Client Categories"
    )
    top_debtors_only = fields.Boolean(
        string="Top 10 Debtors Only", default=False
    )

    # Computed statistics
    clients_with_overdue = fields.Integer(
        string="Clients with Overdue Invoices", readonly=True
    )
    invoices_1_7_days = fields.Integer(
        string="Moved to 1-7 days", readonly=True
    )
    invoices_8_30_days = fields.Integer(
        string="Moved to 8-30 days", readonly=True
    )
    invoices_31_60_days = fields.Integer(
        string="Moved to 31-60 days", readonly=True
    )
    invoices_61_90_days = fields.Integer(
        string="Moved to 61-90 days", readonly=True
    )
    invoices_90_plus_days = fields.Integer(
        string="Moved to 90+ days", readonly=True
    )
    promises_count = fields.Integer(string="Payment Promises", readonly=True)
    promises_paid_count = fields.Integer(string="Promises Kept", readonly=True)
    promises_paid_percentage = fields.Float(
        string="Promises Kept %", readonly=True
    )

    def _get_filtered_partners(self):
        """Get partners based on filters"""
        domain = []

        if self.salesperson_ids:
            domain.append(("user_id", "in", self.salesperson_ids.ids))

        if self.partner_category_ids:
            domain.append(("category_id", "in", self.partner_category_ids.ids))

        partners = self.env["res.partner"].search(domain)

        if self.top_debtors_only:  # previous partners are irrelevant
            partner_debts = []
            for partner in partners:
                if partner.total_all_overdue:
                    partner_debts.append((partner, partner.total_all_overdue))
            partner_debts.sort(key=lambda x: x[1], reverse=True)
            partners = self.env["res.partner"].browse(
                [p[0].id for p in partner_debts[:TOP_DEBTORS_NUMBER]]
            )

        return partners

    def _get_transition_counts(
        self, invoice, stage_transitions: dict[str, int]
    ) -> None:
        """Determine the overdue stage transitions counts."""
        # Get the later date between the period start and the invoice due date
        today = fields.Date.today()
        latest_date = max(
            (today - timedelta(days=self.period_days)),
            invoice.invoice_date_due,
        )
        relative_overdue_days = (today - latest_date).days

        stages = [
            (7, "1-7"),
            (30, "8-30"),
            (60, "31-60"),
            (90, "61-90"),
            (float("inf"), "90+"),
        ]

        for threshold, stage_key in stages:
            stage_transitions[stage_key] += 1
            if relative_overdue_days <= threshold:
                break

    def _compute_real_statistics(self):
        """Compute actual statistics based on filters"""
        self.ensure_one()
        today = fields.Date.today()

        partners = self._get_filtered_partners()

        invoice_domain = [
            ("partner_id", "in", partners.ids),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("invoice_date_due", "<", today),
        ]

        overdue_invoices = self.env["account.move"].search(invoice_domain)
        clients_with_overdue = len(overdue_invoices.mapped("partner_id"))

        stage_transitions = {
            "1-7": 0,
            "8-30": 0,
            "31-60": 0,
            "61-90": 0,
            "90+": 0,
        }

        for invoice in overdue_invoices:
            self._get_transition_counts(invoice, stage_transitions)

        promise_domain = [
            ("partner_id", "in", partners.ids),
            ("promise_date", ">=", today - timedelta(days=self.period_days)),
            ("promise_date", "<=", today),
        ]

        promises = self.env["debt.promise.payment"].search(promise_domain)
        promises_count = len(promises)
        promises_paid_count = len(
            promises.filtered(lambda p: p.state == "paid")
        )
        promises_paid_percentage = (
            (promises_paid_count / promises_count)
            if promises_count > 0
            else 0.0
        )

        return {
            "clients_with_overdue": clients_with_overdue,
            "invoices_1_7_days": stage_transitions["1-7"],
            "invoices_8_30_days": stage_transitions["8-30"],
            "invoices_31_60_days": stage_transitions["31-60"],
            "invoices_61_90_days": stage_transitions["61-90"],
            "invoices_90_plus_days": stage_transitions["90+"],
            "promises_count": promises_count,
            "promises_paid_count": promises_paid_count,
            "promises_paid_percentage": promises_paid_percentage,
        }

    def action_view_report(self):
        self.ensure_one()
        stats = self._compute_real_statistics()
        self.write(stats)

        # Force refresh
        self.invalidate_recordset()

        return {
            "type": "ir.actions.act_window",
            "res_model": "followup.report.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "name": "Follow-up Report",
            "context": {"show_statistics": True},
        }
