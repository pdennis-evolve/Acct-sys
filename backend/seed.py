"""Seeds a super-admin account plus a demo tenant with an owner/admin user
and a starter chart of accounts. Safe to re-run -- skips anything that
already exists."""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import Tenant, User, SuperAdmin, Account, CompanySettings, TaxRate, ALL_MODULES

app = create_app()


def seed():
    with app.app_context():
        admin_email = os.environ.get("SUPERADMIN_BOOTSTRAP_EMAIL")
        admin_password = os.environ.get("SUPERADMIN_BOOTSTRAP_PASSWORD")
        if admin_email and admin_password:
            if not SuperAdmin.query.filter_by(email=admin_email).first():
                sa = SuperAdmin(email=admin_email, full_name="ETG Super Admin")
                sa.set_password(admin_password)
                db.session.add(sa)
                print(f"Created super-admin: {admin_email}")
            else:
                print(f"Super-admin already exists: {admin_email}")

        demo = Tenant.query.filter_by(slug="demo").first()
        if not demo:
            demo = Tenant(
                name="Demo Company",
                slug="demo",
                modules={m: True for m in ALL_MODULES},
                seat_limit=10,
                license_status="active",
                plan_notes="Seed/demo tenant for local development.",
            )
            db.session.add(demo)
            db.session.flush()
            print("Created demo tenant (slug=demo)")

            owner = User(
                tenant_id=demo.id,
                email="owner@demo.com",
                full_name="Demo Owner",
                role="owner_admin",
            )
            owner.set_password("Demo123!")
            db.session.add(owner)

            settings = CompanySettings(tenant_id=demo.id, company_name="Demo Company")
            db.session.add(settings)

            print("Created demo owner user: owner@demo.com / Demo123!")
        else:
            print("Demo tenant already exists (slug=demo)")

        # Top up an existing demo tenant with any starter accounts/rates
        # added since it was first created -- keeps re-runs idempotent
        # instead of only seeding fully-fresh tenants.
        existing_codes = {a.code for a in Account.query.filter_by(tenant_id=demo.id).all()}
        starter_accounts = [
            ("1000", "Cash and Bank", "asset"),
            ("1200", "Accounts Receivable", "asset"),
            ("2000", "Accounts Payable", "liability"),
            ("3000", "Owner's Equity", "equity"),
            ("4000", "Sales Revenue", "income"),
            ("4100", "Service Revenue", "income"),
            ("5000", "General Expenses", "expense"),
            ("5100", "Cost of Goods Sold", "expense"),
            ("5200", "Rent Expense", "expense"),
            ("5300", "Utilities Expense", "expense"),
            ("5400", "Office Supplies Expense", "expense"),
        ]
        for code, name, type_ in starter_accounts:
            if code not in existing_codes:
                db.session.add(Account(tenant_id=demo.id, code=code, name=name, type=type_))
                print(f"Added missing starter account {code} {name}")

        if not TaxRate.query.filter_by(tenant_id=demo.id).first():
            db.session.add(TaxRate(
                tenant_id=demo.id, name="State Sales Tax", rate="0.0700",
                jurisdiction="Demo State", is_default=True,
            ))
            print("Added default tax rate")

        db.session.commit()


if __name__ == "__main__":
    seed()
