from odoo import api, fields, models


class AccountMoveDebtManagement(models.Model):
    _inherit = "account.report"

    filter_salesperson = fields.Boolean(
        string="Salespeople",
        compute=lambda x: x._compute_report_option_filter("filter_salesperson"),
        readonly=False,
        store=True,
        depends=["root_report_id", "section_main_report_ids"],
    )

    def get_report_information(self, options):
        info = super().get_report_information(options)
        # those keys are garanted to be in options dictionary
        info["filters"]["show_salespeople"] = self.filter_salesperson
        return info

    def _init_options_salespeople(self, options, previous_options):
        if not self.filter_salesperson:
            return

        previous_salesperson_ids = previous_options.get("salesperson_ids") or []
        selected_salesperson_ids = [
            int(partner) for partner in previous_salesperson_ids
        ]
        # search instead of browse so that record rules apply and filter out the ones the user does not have access to
        selected_salespeople = (
            selected_salesperson_ids
            and self.env["res.users"]
            .with_context(active_test=False)
            .search(
                [
                    ("id", "in", selected_salesperson_ids),
                    ("share", "=", False),
                ]
            )
            or self.env["res.users"]
        )
        options["selected_salesperson_ids"] = selected_salespeople
        options["salesperson_ids"] = selected_salespeople.ids
        options["show_salespeople"] = True

    def _init_options_readonly_query(self, options, previous_options):
        super()._init_options_readonly_query(options, previous_options)
        options["readonly_query"] = options[
            "readonly_query"
        ] and not options.get("report_salespeople")

    @api.model
    def _get_options_salesperson_domain(self, options):
        domain = []
        if options.get("salesperson_ids"):
            salesperson_ids = [
                int(salesperson) for salesperson in options["salesperson_ids"]
            ]
            domain.append(("move_id.invoice_user_id", "in", salesperson_ids))
        return domain

    def _get_options_domain(self, options, date_scope):
        domain = super()._get_options_domain(options, date_scope)
        domain += self._get_options_salesperson_domain(options)
        return domain
