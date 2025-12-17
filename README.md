# Debt Management

**Debt Management for Odoo Enterprise**

This module extends Odoo 18 Accounting with comprehensive tools to manage and automate accounts receivable follow-ups. Take full control of your receivables, get paid faster, and work smarter with automated reminders, powerful analytics, and structured collection workflows.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Key Features](#key-features)
- [Troubleshooting](#troubleshooting)
- [Compatibility](#compatibility)
- [Maintainers](#maintainers)

## Installation

1. Download the module and place it in your Odoo addons folder
2. Install optional Python dependencies for XLSX support:
   ```bash
   python -m pip install -r addons/debt_management/requirements.txt
   ```
3. From the Odoo home screen, go to **Apps** → **Update Apps List**
4. Search for "Debt Management" and click **Install**

## Configuration

### Follow-up Levels

Navigate to **Configurations → Follow-up levels**:

Review existing and add new follow-up levels if needed.

**You can set:**
- What to send (email, SMS, letter)
- Template
- Follow-up activity
- Automatic response check
- Other options

### Email Templates

Navigate to **Configurations → Email Templates** to customize:

**Available Templates:**
- Payment reminder templates (fully customizable)
- Follow-up email templates
- Overdue notification templates

Templates support:
- Report attachments
- Partner placeholders
- Dynamic content based on invoice status

### Notification Frequency

Modify automated follow-up timing in **Settings → Technical → Scheduled Actions** by editing the relevant cron jobs in `data/cron_jobs.xml`.

## Usage

### For Finance & Accounting Teams:

**Create Overdue Invoices Export Configurations:**
1. Navigate to **Overdue Invoices → Export**
2. Choose from available options, set up schedule if needed
3. Use **Test Send** to validate email and attachment generation

**Send Payment Reminders:**
1. Open a partner record with overdue invoices
2. Click the **Send Reminder** button
3. Preview the email content and customize if needed
4. Send immediately or schedule for later

**Track Collection Activities:**
- Log calls, emails, and notes directly in the partner's chatter
- Log notes, reminders, activities in the invoice's chatter
- Record promises to pay with expected dates
- Track payment plans and partial payments

### For Management:

**Access Dashboard:**
- Navigate to **Debt Management → Receivables Dashboard**
- View real-time metrics on:
  - Total outstanding amounts
  - Overdue by aging buckets
  - Top debtors list
  - Expected payments timeline

**Generate Reports:**
- **Aged Receivable Report** – Detailed breakdown by aging periods
- **Overdue Invoices** – All past-due amounts with contact details
- **Top Debtors** – Ranked list of highest outstanding balances
- **Payment Promises** – List of payment promises

## Key Features

### Core Functionality

- **Scheduled Overdue Invoices exports** with configurable filters and email recipients (`models/aged_receivables_export_config.py`)
- **Email payment reminders** using `mail.template` and chatter integration (`wizard/send_reminder_wizard.py`, `models/account_followup_report.py`)
- **Follow-up reports and dashboard** for accounting users (`models/account_report.py`, `models/aged_receivables_dashboard.py`)
- **Optional XLSX export** using `openpyxl` with guarded imports (`requirements.txt`)
- **Frontend filter component** for account reports (`static/src/components/aged_receivables_report/filters.js`)

## Compatibility
- **Odoo Editions:** Enterprise
- **Version:** 18.0 (fully compatible with latest Odoo frameworks)

## Maintainers

This module is maintained by Qulix.

![Qulix Logo](https://6477711.fs1.hubspotusercontent-na1.net/hub/6477711/hubfs/Screenshot_13.png?width=108&height=108)

Qulix is a global provider of end-to-end Odoo solutions that help businesses streamline, automate, and optimize their operations.

For questions or support, please contact: qulix@qulix.com

**Because your cash flow deserves more than reminders.**
