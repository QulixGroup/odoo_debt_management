import base64

from odoo import fields, models
from odoo.exceptions import UserError


class AgedReceivablesExportWizard(models.TransientModel):
    _name = "aged.receivables.export.wizard"
    _inherit = ["aged.receivables.export.mixin"]
    _description = "AR Dashboard Export Wizard"

    export_format = fields.Selection(
        [("pdf", "PDF"), ("xlsx", "Excel")],
        string="Export Format",
        default="pdf",
        required=True,
    )

    config_name = fields.Char(string="Configuration Name")
    partner_ids = fields.Many2many("res.partner", string="Clients")
    region_ids = fields.Many2many("res.country.state", string="Regions")
    user_ids = fields.Many2many("res.users", string="Account Managers")
    days_overdue_min = fields.Integer(string="Min Days Overdue", default=0)
    days_overdue_max = fields.Integer(string="Max Days Overdue")

    schedule_export = fields.Boolean(string="Schedule Periodic Export")
    schedule_interval = fields.Selection(
        [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        string="Frequency",
    )
    email_recipients = fields.Char(string="Email Recipients")

    def action_export(self):
        """Export AR Dashboard data"""
        self.ensure_one()

        domain = self._build_domain()
        records = self.env["aged.receivables.dashboard"].search(domain)

        if not records:
            raise UserError("No records found matching the criteria.")

        if self.export_format == "pdf":
            return self._export_pdf(records)
        else:
            return self._export_xlsx(records)

    def _build_domain(self):
        """Build search domain based on filters"""
        domain = [("days_overdue", ">", 0)]

        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))

        if self.region_ids:
            domain.append(("partner_region", "in", self.region_ids.ids))

        if self.user_ids:
            domain.append(("user_id", "in", self.user_ids.ids))

        if self.days_overdue_min:
            domain.append(("days_overdue", ">=", self.days_overdue_min))

        if self.days_overdue_max:
            domain.append(("days_overdue", "<=", self.days_overdue_max))

        return domain

    def _export_pdf(self, records):
        """Generate PDF report"""
        return self.env.ref("debts_management.action_ar_report").report_action(
            records
        )

    def _export_xlsx(self, records):
        """Generate Excel report"""
        xlsx_data = self.generate_xlsx_data(records)

        attachment = self.env["ir.attachment"].create(
            {
                "name": "AR_Dashboard_Export.xlsx",
                "type": "binary",
                "datas": base64.b64encode(xlsx_data),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_schedule_export(self):
        """Create scheduled action for periodic exports"""
        self.ensure_one()

        if not self.schedule_interval or not self.email_recipients:
            raise UserError("Please specify frequency and email recipients.")

        if not self.config_name:
            raise UserError("Please provide a configuration name.")

        config_vals = {
            "name": self.config_name,
            "export_format": self.export_format,
            "partner_ids": [(6, 0, self.partner_ids.ids)],
            "region_ids": [(6, 0, self.region_ids.ids)],
            "user_ids": [(6, 0, self.user_ids.ids)],
            "days_overdue_min": self.days_overdue_min,
            "days_overdue_max": self.days_overdue_max,
            "schedule_interval": self.schedule_interval,
            "email_recipients": self.email_recipients,
        }

        config = self.env["aged.receivables.export.config"].create(config_vals)
        config.action_create_or_update_schedule()

        return {
            "type": "ir.actions.act_window",
            "res_model": "aged.receivables.export.config",
            "res_id": config.id,
            "view_mode": "form",
            "target": "current",
        }
