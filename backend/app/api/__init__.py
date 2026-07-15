def register_blueprints(app):
    from app.api.auth import bp as auth_bp
    from app.api.super_admin import bp as super_admin_bp
    from app.api.users import bp as users_bp
    from app.api.settings import bp as settings_bp
    from app.api.accounts import bp as accounts_bp
    from app.api.customers import bp as customers_bp
    from app.api.invoices import bp as invoices_bp
    from app.api.payments import bp as payments_bp
    from app.api.cash_accounts import bp as cash_accounts_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(super_admin_bp, url_prefix="/api/admin")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(accounts_bp, url_prefix="/api/accounts")
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(cash_accounts_bp, url_prefix="/api/cash-accounts")
