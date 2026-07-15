"""Reporting queries. Kept separate from app/api/reports.py so the
aggregation logic is testable without going through the HTTP layer.

All functions take tenant_id explicitly rather than reading flask.g,
so they can be called from scripts/tests outside a request context.
"""
from collections import defaultdict
from decimal import Decimal

from app.extensions import db
from app.models import Invoice, InvoiceLine, Bill, BillLine, Account, TaxRate, Customer

AR_OPEN_STATUSES = ("sent", "partial")
AR_RECOGNIZED_STATUSES = ("sent", "partial", "paid")
AP_RECOGNIZED_STATUSES = ("approved", "partial", "paid")


def _bucket_key(d, group_by):
    if group_by == "day":
        return d.isoformat()
    if group_by == "month":
        return d.strftime("%Y-%m")
    return "all"


def profit_and_loss(tenant_id, start, end, group_by="none"):
    income_rows = (
        db.session.query(InvoiceLine.account_id, InvoiceLine.amount, Invoice.issue_date)
        .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.is_deleted == False,  # noqa: E712
            Invoice.status.in_(AR_RECOGNIZED_STATUSES),
            Invoice.issue_date >= start,
            Invoice.issue_date <= end,
        )
        .all()
    )
    expense_rows = (
        db.session.query(BillLine.account_id, BillLine.amount, Bill.bill_date)
        .join(Bill, BillLine.bill_id == Bill.id)
        .filter(
            Bill.tenant_id == tenant_id,
            Bill.is_deleted == False,  # noqa: E712
            Bill.status.in_(AP_RECOGNIZED_STATUSES),
            Bill.bill_date >= start,
            Bill.bill_date <= end,
        )
        .all()
    )

    accounts = {a.id: a.name for a in Account.query.filter_by(tenant_id=tenant_id).all()}

    def _aggregate(rows):
        by_account = defaultdict(lambda: Decimal("0"))
        by_period = defaultdict(lambda: Decimal("0"))
        for account_id, amount, txn_date in rows:
            by_account[account_id] += amount
            if group_by in ("day", "month"):
                by_period[_bucket_key(txn_date, group_by)] += amount
        return by_account, by_period

    income_by_account, income_by_period = _aggregate(income_rows)
    expense_by_account, expense_by_period = _aggregate(expense_rows)

    def _account_rows(by_account):
        rows = [
            {
                "account_id": acct_id,
                "account_name": accounts.get(acct_id, "Uncategorized") if acct_id else "Uncategorized",
                "total": str(total),
            }
            for acct_id, total in by_account.items()
        ]
        rows.sort(key=lambda r: r["account_name"])
        return rows

    income_total = sum(income_by_account.values(), Decimal("0"))
    expense_total = sum(expense_by_account.values(), Decimal("0"))

    result = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "group_by": group_by,
        "income": _account_rows(income_by_account),
        "income_total": str(income_total),
        "expenses": _account_rows(expense_by_account),
        "expenses_total": str(expense_total),
        "net_income": str(income_total - expense_total),
    }

    if group_by in ("day", "month"):
        all_keys = sorted(set(income_by_period) | set(expense_by_period))
        result["periods"] = [
            {
                "period": key,
                "income": str(income_by_period.get(key, Decimal("0"))),
                "expenses": str(expense_by_period.get(key, Decimal("0"))),
                "net_income": str(income_by_period.get(key, Decimal("0")) - expense_by_period.get(key, Decimal("0"))),
            }
            for key in all_keys
        ]

    return result


def income_report(tenant_id, start, end, group_by="day"):
    rows = (
        db.session.query(Invoice.issue_date, Invoice.subtotal, Invoice.tax_total, Invoice.total)
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.is_deleted == False,  # noqa: E712
            Invoice.status.in_(AR_RECOGNIZED_STATUSES),
            Invoice.issue_date >= start,
            Invoice.issue_date <= end,
        )
        .all()
    )

    periods = defaultdict(lambda: {"subtotal": Decimal("0"), "tax": Decimal("0"), "total": Decimal("0"), "invoice_count": 0})
    for issue_date, subtotal, tax_total, total in rows:
        p = periods[_bucket_key(issue_date, group_by)]
        p["subtotal"] += subtotal
        p["tax"] += tax_total
        p["total"] += total
        p["invoice_count"] += 1

    period_rows = [
        {
            "period": key,
            "subtotal": str(v["subtotal"]),
            "tax": str(v["tax"]),
            "total": str(v["total"]),
            "invoice_count": v["invoice_count"],
        }
        for key, v in sorted(periods.items())
    ]

    grand_subtotal = sum((v["subtotal"] for v in periods.values()), Decimal("0"))
    grand_tax = sum((v["tax"] for v in periods.values()), Decimal("0"))
    grand_total = sum((v["total"] for v in periods.values()), Decimal("0"))

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "group_by": group_by,
        "periods": period_rows,
        "totals": {
            "subtotal": str(grand_subtotal),
            "tax": str(grand_tax),
            "total": str(grand_total),
            "invoice_count": sum(v["invoice_count"] for v in periods.values()),
        },
    }


def sales_tax_report(tenant_id, start, end, group_by="none"):
    rows = (
        db.session.query(
            Invoice.tax_rate_id, Invoice.tax_rate_pct, Invoice.subtotal,
            Invoice.tax_total, Invoice.total, Invoice.issue_date,
        )
        .filter(
            Invoice.tenant_id == tenant_id,
            Invoice.is_deleted == False,  # noqa: E712
            Invoice.status.in_(AR_RECOGNIZED_STATUSES),
            Invoice.issue_date >= start,
            Invoice.issue_date <= end,
        )
        .all()
    )

    tax_rates = {t.id: t for t in TaxRate.query.filter_by(tenant_id=tenant_id).all()}

    by_rate = defaultdict(lambda: {"taxable_sales": Decimal("0"), "tax_collected": Decimal("0"), "total_sales": Decimal("0")})
    by_period = defaultdict(lambda: {"taxable_sales": Decimal("0"), "tax_collected": Decimal("0")})

    for tax_rate_id, tax_rate_pct, subtotal, tax_total, total, issue_date in rows:
        if tax_rate_id and tax_rate_id in tax_rates:
            key = tax_rate_id
        elif tax_rate_pct and tax_rate_pct > 0:
            key = f"adhoc:{tax_rate_pct}"
        else:
            key = "none"
        bucket = by_rate[key]
        bucket["taxable_sales"] += subtotal
        bucket["tax_collected"] += tax_total
        bucket["total_sales"] += total

        if group_by in ("day", "month"):
            p = by_period[_bucket_key(issue_date, group_by)]
            p["taxable_sales"] += subtotal
            p["tax_collected"] += tax_total

    def _label(key):
        if key == "none":
            return "No Tax"
        if key.startswith("adhoc:"):
            pct = Decimal(key.split(":", 1)[1])
            return f"{(pct * 100).normalize()}% (no jurisdiction set)"
        rate = tax_rates[key]
        return f"{rate.name} ({rate.jurisdiction})" if rate.jurisdiction else rate.name

    rate_rows = [
        {
            "key": key,
            "label": _label(key),
            "taxable_sales": str(v["taxable_sales"]),
            "tax_collected": str(v["tax_collected"]),
            "total_sales": str(v["total_sales"]),
        }
        for key, v in by_rate.items()
    ]
    rate_rows.sort(key=lambda r: r["label"])

    result = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "group_by": group_by,
        "by_rate": rate_rows,
        "totals": {
            "taxable_sales": str(sum((v["taxable_sales"] for v in by_rate.values()), Decimal("0"))),
            "tax_collected": str(sum((v["tax_collected"] for v in by_rate.values()), Decimal("0"))),
            "total_sales": str(sum((v["total_sales"] for v in by_rate.values()), Decimal("0"))),
        },
    }

    if group_by in ("day", "month"):
        result["periods"] = [
            {"period": key, "taxable_sales": str(v["taxable_sales"]), "tax_collected": str(v["tax_collected"])}
            for key, v in sorted(by_period.items())
        ]

    return result


def aging_receivables(tenant_id, as_of, ranges, issue_start=None, issue_end=None):
    """Standard AR aging report. `ranges` (e.g. [30, 60, 90]) defines bucket
    edges in days-past-due; a custom list produces custom buckets. Invoices
    can additionally be scoped to a custom issue-date window."""
    ranges = sorted(ranges)
    labels = ["Current"]
    for i, r in enumerate(ranges):
        lower = ranges[i - 1] + 1 if i > 0 else 1
        labels.append(f"{lower}-{r}")
    labels.append(f"{ranges[-1] + 1}+")

    def _bucket_for(days_overdue):
        if days_overdue <= 0:
            return "Current"
        for i, r in enumerate(ranges):
            if days_overdue <= r:
                lower = ranges[i - 1] + 1 if i > 0 else 1
                return f"{lower}-{r}"
        return f"{ranges[-1] + 1}+"

    q = Invoice.query.filter(
        Invoice.tenant_id == tenant_id,
        Invoice.is_deleted == False,  # noqa: E712
        Invoice.status.in_(AR_OPEN_STATUSES),
        Invoice.balance_due > 0,
    )
    if issue_start:
        q = q.filter(Invoice.issue_date >= issue_start)
    if issue_end:
        q = q.filter(Invoice.issue_date <= issue_end)
    invoices = q.all()

    customers = {c.id: c.display_name for c in Customer.query.filter_by(tenant_id=tenant_id).all()}

    by_customer = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    totals = defaultdict(lambda: Decimal("0"))
    detail = []

    for inv in invoices:
        days_overdue = (as_of - inv.due_date).days
        bucket = _bucket_for(days_overdue)
        by_customer[inv.customer_id][bucket] += inv.balance_due
        totals[bucket] += inv.balance_due
        detail.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "customer_name": customers.get(inv.customer_id, "Unknown"),
            "due_date": inv.due_date.isoformat(),
            "days_overdue": days_overdue,
            "bucket": bucket,
            "balance_due": str(inv.balance_due),
        })

    rows = []
    for customer_id, buckets in by_customer.items():
        row_total = sum(buckets.values(), Decimal("0"))
        rows.append({
            "customer_id": customer_id,
            "customer_name": customers.get(customer_id, "Unknown"),
            "amounts": {label: str(buckets.get(label, Decimal("0"))) for label in labels},
            "total": str(row_total),
        })
    rows.sort(key=lambda r: r["customer_name"])

    return {
        "as_of": as_of.isoformat(),
        "buckets": labels,
        "rows": rows,
        "totals": {label: str(totals.get(label, Decimal("0"))) for label in labels},
        "grand_total": str(sum(totals.values(), Decimal("0"))),
        "detail": detail,
    }
