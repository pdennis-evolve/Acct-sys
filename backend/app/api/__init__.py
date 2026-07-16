def register_blueprints(app):
    from app.api.auth import bp as auth_bp
    from app.api.super_admin import bp as super_admin_bp
    from app.api.users import bp as users_bp
    from app.api.settings import bp as settings_bp
    from app.api.accounts import bp as accounts_bp
    from app.api.tax_rates import bp as tax_rates_bp
    from app.api.customers import bp as customers_bp
    from app.api.invoices import bp as invoices_bp
    from app.api.payments import bp as payments_bp
    from app.api.cash_accounts import bp as cash_accounts_bp
    from app.api.vendors import bp as vendors_bp
    from app.api.bills import bp as bills_bp
    from app.api.purchase_orders import bp as purchase_orders_bp
    from app.api.vendor_payments import bp as vendor_payments_bp
    from app.api.reports import bp as reports_bp
    from app.api.locations import bp as locations_bp
    from app.api.items import bp as items_bp
    from app.api.work_orders import bp as work_orders_bp
    from app.api.vehicles import bp as vehicles_bp
    from app.api.drivers import bp as drivers_bp
    from app.api.loads import bp as loads_bp
    from app.api.shipments import bp as shipments_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(super_admin_bp, url_prefix="/api/admin")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(accounts_bp, url_prefix="/api/accounts")
    app.register_blueprint(tax_rates_bp, url_prefix="/api/tax-rates")
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(cash_accounts_bp, url_prefix="/api/cash-accounts")
    app.register_blueprint(vendors_bp, url_prefix="/api/vendors")
    app.register_blueprint(bills_bp, url_prefix="/api/bills")
    app.register_blueprint(purchase_orders_bp, url_prefix="/api/purchase-orders")
    app.register_blueprint(vendor_payments_bp, url_prefix="/api/vendor-payments")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(locations_bp, url_prefix="/api/locations")
    app.register_blueprint(items_bp, url_prefix="/api/items")
    app.register_blueprint(work_orders_bp, url_prefix="/api/work-orders")
    app.register_blueprint(vehicles_bp, url_prefix="/api/vehicles")
    app.register_blueprint(drivers_bp, url_prefix="/api/drivers")
    app.register_blueprint(loads_bp, url_prefix="/api/loads")
    app.register_blueprint(shipments_bp, url_prefix="/api/shipments")
