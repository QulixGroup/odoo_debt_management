from odoo import api, models


class SalespersonCustomHandler(models.AbstractModel):
    _inherit = "account.aged.receivable.report.handler"

    def _get_custom_display_config(self):
        return {
            "components": {
                "AccountReportFilters": "debts_management.SalespersonBalanceFilters",
            },
        }

    @api.model
    def _get_options_salesperson_domain(self, options):
        """Get domain for salesperson filter"""
        domain = []
        if options.get("salesperson_ids"):
            salesperson_ids = [int(sp) for sp in options["salesperson_ids"]]
            domain.append(("invoice_user_id", "in", salesperson_ids))
        return domain

    def _get_aml_domain(self, report, options, partner):
        """Override to add salesperson domain to account move line queries"""
        domain = super()._get_aml_domain(report, options, partner)
        domain += self._get_options_salesperson_domain(options)
        return domain
