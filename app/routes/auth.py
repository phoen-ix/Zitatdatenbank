from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash

from models import AdminUser
from helpers import _
from extensions import limiter

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10/minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = AdminUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            # Prevent open redirect — only allow relative URLs
            if next_page and urlparse(next_page).netloc == '':
                return redirect(next_page)
            return redirect(url_for('admin.dashboard'))
        flash(_('login_failed'), 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))
