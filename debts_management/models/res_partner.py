from odoo import models, fields, api


TOP_DEBTORS_NUMBER = 10


class Partner(models.Model):
    _inherit = "res.partner"

    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="partner_id",
        string="Customer Invoices",
        help="List of invoices",
    )
    invoice_message_ids = fields.Many2many(
        comodel_name="mail.message",
        string="Invoice Messages",
        compute="_compute_invoice_message_ids",
        help="All messages and notes from customer invoices",
    )
    overdue_invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="partner_id",
        string="Overdue Invoices",
        compute="_compute_overdue_invoice_ids",
        help="List of overdue customer invoices",
    )

    debt_promise_ids = fields.One2many(
        "debt.promise.payment", "partner_id", string="Payment Promises"
    )
    debt_promise_count = fields.Integer(
        string="Promises", compute="_compute_debt_promise_count"
    )

    def _compute_debt_promise_count(self):
        for partner in self:
            partner.debt_promise_count = len(partner.debt_promise_ids)

    def action_create_payment_promise(self):
        self.ensure_one()
        return {
            "name": "Create Payment Promise",
            "type": "ir.actions.act_window",
            "res_model": "debt.promise.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_partner_id": self.id},
        }

    def action_view_payment_promises(self):
        self.ensure_one()
        return {
            "name": "Payment Promises",
            "type": "ir.actions.act_window",
            "res_model": "debt.promise.payment",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }

    @api.depends(
        "invoice_ids",
        "invoice_ids.state",
        "invoice_ids.invoice_date_due",
        "invoice_ids.amount_residual",
        "invoice_ids.move_type",
    )
    def _compute_overdue_invoice_ids(self):
        """Compute overdue invoices"""
        today = fields.Date.today()
        for partner in self:
            overdue_invoices = partner.invoice_ids.filtered(
                lambda i: i.state == "posted"
                and i.move_type == "out_invoice"
                and i.invoice_date_due
                and i.invoice_date_due < today
                and i.amount_residual > 0
            )
            partner.overdue_invoice_ids = overdue_invoices

    @api.depends("invoice_ids")
    def _compute_invoice_message_ids(self):
        """Compute all messages related to customer invoices"""
        for partner in self:
            if partner.overdue_invoice_ids:
                messages = self.env["mail.message"].search(
                    [
                        ("model", "=", "account.move"),
                        ("res_id", "in", partner.overdue_invoice_ids.ids),
                        ("body", "!=", False),
                    ],
                    order="res_id, date desc",
                )
                partner.invoice_message_ids = messages
            else:
                partner.invoice_message_ids = False

    def action_view_overdue_invoices(self):
        """Open overdue invoices for this partner"""
        self.ensure_one()
        return {
            "name": f"Overdue Invoices - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.overdue_invoice_ids.ids)],
            "context": {"create": False},
            "target": "current",
        }

    def action_show_top_ten_debtors(self):
        """Action to show top 10 debtors"""
        today = fields.Date.today()

        results = self.env["account.move"].read_group(
            domain=[
                ("state", "=", "posted"),
                ("move_type", "=", "out_invoice"),
                ("invoice_date_due", "<", today),
                ("amount_residual", ">", 0),
                ("partner_id", "!=", False),
            ],
            fields=["partner_id", "amount_residual:sum"],
            groupby=["partner_id"],
            orderby="amount_residual desc",
            limit=TOP_DEBTORS_NUMBER,
        )

        partner_ids = [result["partner_id"][0] for result in results]

        return {
            "name": "Top Ten Debtors",
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "views": [
                (
                    self.env.ref(
                        "debts_management.view_partner_list_top_debtors"
                    ).id,
                    "list",
                ),
                (False, "form"),
            ],
            "domain": [("id", "in", partner_ids if partner_ids else [0])],
            "context": {},
        }

    def _execute_followup_partner(self, options=None):
        """ Execute follow-up for a partner.

        Overwritten to add handling of scheduled activities on invoices.
        """
        self.ensure_one()
        if options is None:
            options = {}
        if options.get("manual_followup", self.followup_status == "in_need_of_action"):
            followup_line = (self.followup_line_id or self._get_first_followup_level())
            unreconciled_invoices = (
                self.unreconciled_aml_ids.move_id.filtered(
                    lambda inv: inv.invoice_overdue_days
                    >= followup_line.delay
                    and inv.move_type == "out_invoice"
                )
            )
            options["unreconciled_invoice_ids"] = unreconciled_invoices.ids or [options.get("invoice_id")]

            if (
                followup_line.enable_response_check
                and followup_line.create_activity
            ):
                self.env["account.followup.pending.check"].create(
                    {
                        "partner_id": self.id,
                        "followup_line_id": followup_line.id,
                        "send_date": fields.Datetime.now(),
                    }
                )
            elif followup_line.create_activity:
                # log a next activity for today
                self.activity_schedule(
                    activity_type_id=followup_line.activity_type_id and followup_line.activity_type_id.id or self._default_activity_type().id,
                    note=followup_line.activity_note,
                    summary=followup_line.activity_summary,
                    user_id=(self._get_followup_responsible()).id
                )
            options['followup_line'] = followup_line
            self._update_next_followup_action_date(followup_line)

            self._get_followup_attachments(options)

            self._send_followup(options)

            return True
        return False

    def _get_followup_data_query(self, partner_ids=None):
        """Overwritten version filtering out is_disputed invoices."""
        self.env["account.move.line"].check_access("read")
        self.env["account.move.line"].flush_model()
        self.env["res.partner"].flush_model()
        self.env["account_followup.followup.line"].flush_model()
        ResPartner = self.env["res.partner"]
        return f"""
                SELECT partner.id as partner_id,
                    ful.id as followup_line_id,
                    CASE WHEN partner.balance <= 0 THEN 'no_action_needed'
                            WHEN in_need_of_action_aml.id IS NOT NULL AND (followup_next_action_date IS NULL OR followup_next_action_date <= %(current_date)s) THEN 'in_need_of_action'
                            WHEN exceeded_unreconciled_aml.id IS NOT NULL THEN 'with_overdue_invoices'
                            ELSE 'no_action_needed' END as followup_status
                FROM (
            SELECT partner.id,
                    {self.env.cr.mogrify(ResPartner._field_to_sql('partner', 'followup_next_action_date')).decode(self.env.cr.connection.encoding)} AS followup_next_action_date,
                    MAX(COALESCE(next_ful.delay, ful.delay)) as followup_delay,
                    SUM(aml.balance) as balance
                FROM res_partner partner
                JOIN account_move_line aml ON aml.partner_id = partner.id
                JOIN account_move move ON move.id = aml.move_id
                JOIN account_account account ON account.id = aml.account_id
        LEFT JOIN account_followup_followup_line ful ON ful.id = aml.followup_line_id
        LEFT JOIN account_followup_followup_line next_ful ON next_ful.id = (
                        SELECT next_ful.id
                        FROM account_followup_followup_line next_ful
                        WHERE next_ful.delay > COALESCE(ful.delay, %(min_delay)s - 1)
                        AND next_ful.company_id = %(company_id)s
                    ORDER BY next_ful.delay ASC
                        LIMIT 1
                    )
            WHERE account.account_type = 'asset_receivable'
                AND aml.parent_state = 'posted'
                AND aml.reconciled IS NOT TRUE
                AND move.is_disputed IS NOT TRUE
                AND aml.company_id = ANY(%(company_ids)s)
                {"" if partner_ids is None else "AND aml.partner_id IN %(partner_ids)s"}
            GROUP BY partner.id
                ) partner
                LEFT JOIN account_followup_followup_line ful ON ful.delay = partner.followup_delay AND ful.company_id = %(company_id)s
                -- Get the followup status data
                LEFT OUTER JOIN LATERAL (
                    SELECT line.id
                    FROM account_move_line line
                    JOIN account_move move ON move.id = line.move_id
                    JOIN account_account account ON line.account_id = account.id
                LEFT JOIN account_followup_followup_line ful ON ful.id = line.followup_line_id
                    WHERE line.partner_id = partner.id
                    AND account.account_type = 'asset_receivable'
                    AND line.no_followup IS NOT TRUE
                    AND line.parent_state = 'posted'
                    AND line.reconciled IS NOT TRUE
                    AND move.is_disputed IS NOT TRUE
                    AND line.balance > 0
                    AND line.company_id = ANY(%(company_ids)s)
                    AND COALESCE(ful.delay, %(min_delay)s - 1) < partner.followup_delay
                    AND line.date_maturity IS NOT NULL
                    AND line.date_maturity + COALESCE(ful.delay, %(min_delay)s - 1) < %(current_date)s
                    LIMIT 1
                ) in_need_of_action_aml ON true
                LEFT OUTER JOIN LATERAL (
                    SELECT line.id
                    FROM account_move_line line
                    JOIN account_move move ON move.id = line.move_id
                    JOIN account_account account ON line.account_id = account.id
                    WHERE line.partner_id = partner.id
                    AND account.account_type = 'asset_receivable'
                    AND line.no_followup IS NOT TRUE
                    AND line.parent_state = 'posted'
                    AND line.reconciled IS NOT TRUE
                    AND move.is_disputed IS NOT TRUE
                    AND line.balance > 0
                    AND line.company_id = ANY(%(company_ids)s)
                    AND line.date_maturity IS NOT NULL
                    AND line.date_maturity < %(current_date)s
                    LIMIT 1
                ) exceeded_unreconciled_aml ON true
    """, {
            "company_ids": self.env.company.search(
                [("id", "child_of", self.env.company.id)]
            ).ids,
            "company_id": self.env.company.id,
            "partner_ids": tuple(partner_ids or []),
            "current_date": fields.Date.context_today(
                self
            ),  # Allow mocking the current day for testing purpose.
            "min_delay": self._get_first_followup_level().delay or 0,
        }
