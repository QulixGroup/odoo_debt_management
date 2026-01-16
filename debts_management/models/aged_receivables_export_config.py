import base64
from datetime import datetime

from odoo import api, fields, models

DEFAULT_INTERVAL = 1


class AgedReceivablesExportConfig(models.Model):
    _name = "aged.receivables.export.config"
    _description = "AR Export Configuration"
    _inherit = ["aged.receivables.export.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Configuration Name", required=True)
    active = fields.Boolean(string="Active", default=True)

    export_format = fields.Selection(
        [("pdf", "PDF"), ("xlsx", "Excel")],
        string="Export Format",
        default="pdf",
        required=True,
    )

    # Filters
    partner_ids = fields.Many2many("res.partner", string="Clients")
    region_ids = fields.Many2many("res.country.state", string="Regions")
    user_ids = fields.Many2many("res.users", string="Account Managers")
    days_overdue_min = fields.Integer(string="Min Days Overdue", default=0)
    days_overdue_max = fields.Integer(string="Max Days Overdue")

    # Schedule settings
    schedule_interval = fields.Selection(
        [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        string="Frequency",
        required=True,
    )
    email_recipients = fields.Char(
        string="Email Recipients",
        required=True,
        help="Comma-separated email addresses",
    )

    # Link to cron job
    cron_id = fields.Many2one(
        "ir.cron",
        string="Scheduled Action",
        readonly=True,
    )
    next_execution = fields.Datetime(
        string="Next Execution", related="cron_id.nextcall", readonly=True
    )

    def _build_domain(self):
        """Build search domain based on filters"""
        self.ensure_one()
        domain = []

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

    def _generate_pdf_attachment(self, records):
        """Generate PDF and return as attachment"""
        self.ensure_one()
        report = self.env.ref("debts_management.action_ar_report")
        pdf_content, _ = self.env[
            'ir.actions.report'
        ]._render_qweb_pdf(report, res_ids=records.ids)

        attachment = self.env["ir.attachment"].create(
            {
                "name": f"AR_Dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "mimetype": "application/pdf",
            }
        )
        return attachment

    def _generate_xlsx_attachment(self, records):
        """Generate Excel and return as attachment"""
        self.ensure_one()
        xlsx_data = self.generate_xlsx_data(records)

        attachment = self.env["ir.attachment"].create(
            {
                "name": f"AR_Dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "type": "binary",
                "datas": base64.b64encode(xlsx_data),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return attachment

    def send_email_with_attachment(self):
        """Send email with report attachment - called by scheduled exports"""
        for config in self:
            if not config.active:
                continue

            domain = config._build_domain()
            records = self.env["aged.receivables.dashboard"].search(domain)

            if not records:
                continue

            if config.export_format == "pdf":
                attachment = config._generate_pdf_attachment(records)
            else:
                attachment = config._generate_xlsx_attachment(records)

            email_list = [
                email.strip() for email in config.email_recipients.split(",")
            ]

            filter_summary = []
            if config.partner_ids:
                filter_summary.append(
                    f"Clients: {', '.join(config.partner_ids.mapped('name'))}"
                )
            if config.region_ids:
                filter_summary.append(
                    f"Regions: {', '.join(config.region_ids.mapped('name'))}"
                )
            if config.user_ids:
                filter_summary.append(
                    f"Account Managers: {', '.join(config.user_ids.mapped('name'))}"
                )
            if config.days_overdue_min or config.days_overdue_max:
                overdue_range = f"{config.days_overdue_min or 0} - {config.days_overdue_max or 'unlimited'} days"
                filter_summary.append(f"Days Overdue: {overdue_range}")

            filters_html = (
                "<ul>"
                + "".join([f"<li>{f}</li>" for f in filter_summary])
                + "</ul>"
                if filter_summary
                else "<p>No filters applied</p>"
            )

            mail_values = {
                "subject": f"AR Dashboard Report - {config.name} - {datetime.now().strftime('%Y-%m-%d')}",
                "body_html": f"""
                    <p>Dear Recipient,</p>
                    <p>Please find attached the Accounts Receivable Dashboard report for <strong>{config.name}</strong>.</p>
                    <p><strong>Report Details:</strong></p>
                    <ul>
                        <li>Format: {config.export_format.upper()}</li>
                        <li>Total Records: {len(records)}</li>
                        <li>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</li>
                    </ul>
                    <p><strong>Applied Filters:</strong></p>
                    {filters_html}
                    <p>Best regards,</p>
                """,
                "email_to": ", ".join(email_list),
                "attachment_ids": [(6, 0, [attachment.id])],
            }

            mail = self.env["mail.mail"].create(mail_values)
            mail.send()

    def action_create_or_update_schedule(self):
        """Create or update scheduled action"""
        self.ensure_one()

        interval_map = {"daily": "days", "weekly": "weeks", "monthly": "months"}

        if self.cron_id:
            self.cron_id.write(
                {
                    "name": f"AR Export: {self.name}",
                    "active": self.active,
                    "interval_number": DEFAULT_INTERVAL,
                    "interval_type": interval_map[self.schedule_interval],
                    "nextcall": datetime.now(),
                }
            )
        else:
            cron_vals = {
                "name": f"AR Export: {self.name}",
                "model_id": self.env.ref(
                    "debts_management.model_aged_receivables_export_config"
                ).id,
                "state": "code",
                "code": f"model.browse({self.id}).send_email_with_attachment()",
                "interval_number": DEFAULT_INTERVAL,
                "interval_type": interval_map[self.schedule_interval],
                "nextcall": datetime.now(),
                "active": self.active,
            }
            cron = self.env["ir.cron"].create(cron_vals)
            self.cron_id = cron.id

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": f"Schedule {'updated' if self.cron_id else 'created'} successfully!",
                "type": "success",
                "sticky": False,
            },
        }

    def action_test_send(self):
        """Send a test email immediately"""
        self.ensure_one()
        self.send_email_with_attachment()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": "Test email sent successfully!",
                "type": "success",
                "sticky": False,
            },
        }

    def unlink(self):
        """Delete associated cron job when config is deleted"""
        for config in self:
            if config.cron_id:
                config.cron_id.unlink()
        return super(AgedReceivablesExportConfig, self).unlink()

    def write(self, vals):
        """Auto-update cron when config changes"""
        res = super(AgedReceivablesExportConfig, self).write(vals)

        # If schedule-related fields change, update the cron
        schedule_fields = ["schedule_interval", "active", "name"]
        if any(field in vals for field in schedule_fields):
            for config in self:
                if config.cron_id:
                    config.action_create_or_update_schedule()

        return res
