from odoo import fields, models

class AccountFollowupLine(models.Model):
    _inherit = 'account_followup.followup.line'

    enable_response_check = fields.Boolean(
        string="Enable Response Check",
        help=(
            "If enabled, check for customer response after sending email "
            "and False activity if none received."
        )
    )
    response_wait_days = fields.Integer(
        string="Response Wait Days",
        default=7,
        help="Days to wait after sending email before checking for response."
    )
