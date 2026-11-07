from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import limiter
from helpers import _, local_path
from models import AdminUser

auth_bp = Blueprint('auth', __name__)

# Checked for unknown usernames so a failed login costs the same time either way.
_DUMMY_HASH = generate_password_hash('dummy-password')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10/minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = AdminUser.query.filter_by(username=username).first()
        ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
        if user and ok:
            login_user(user)
            return redirect(local_path(request.args.get('next')) or url_for('admin.dashboard'))
        flash(_('login_failed'), 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('main.index'))
