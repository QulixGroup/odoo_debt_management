import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class SalespersonBalanceFilters extends AccountReportFilters {
    static template = "debts_management.SalespersonBalanceFilters";
}

AccountReport.registerCustomComponent(SalespersonBalanceFilters);
