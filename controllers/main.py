
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo.addons.auth_oauth.controllers.main import OAuthLogin, OAuthController, fragment_to_query_string
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.addons.auth_signup.models.res_users import SignupError
import logging
from odoo.http import request, Controller
import json
import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import BadRequest
from odoo import api, http, SUPERUSER_ID, _
from odoo.addons.web.controllers.utils import ensure_db, _get_login_redirect_url
from odoo.tools.misc import clean_context
# from odoo.addons.web.controllers.main import ensure_db, set_cookie_and_redirect, login_and_redirect
from odoo import registry as registry_get
from odoo.exceptions import AccessDenied
import requests
import jwt
import os
import base64

_logger = logging.getLogger(__name__)

class HBNOAuthController(OAuthController):
    @http.route('/hbn/auth_oauth/signin', type='json', auth='none')
    @fragment_to_query_string
    def json_signin(self, **kw):
        state = json.loads(kw['state'])
        dbname = state['d']
        if not http.db_filter([dbname]):
            return BadRequest()
        provider = state['p']
        ensure_db(db=dbname)
        request.update_context(**clean_context(state.get('c', {})))
        _logger.debug("OAuthController: start")

        try:

            _, login, key = request.env['res.users'].with_user(SUPERUSER_ID).auth_oauth(provider, kw) #type: ignore
            request.env.cr.commit()

            action = state.get('a')
            menu = state.get('m')
            redirect = werkzeug.urls.url_unquote_plus(state['r']) if state.get('r') else False #type: ignore
            url = '/odoo'
            if redirect:
                url = redirect
            elif action:
                url = '/odoo/action-%s' % action
            elif menu:
                url = '/odoo?menu_id=%s' % menu

            credential = {'login': login, 'password': key, 'type': 'password'}
            auth_info = request.session.authenticate(dbname, credential)

            return {
                'auth_info': auth_info
            }
        except AttributeError:  # TODO juc master: useless since ensure_db()
            # auth_signup is not installed
            _logger.error("auth_signup not installed on database %s: oauth sign up cancelled.", dbname)
            error = "auth_signup not installed"
        except AccessDenied:
            # oauth credentials not valid, user could be on a temporary session
            _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
            error =  "OAuth2: access denied"
        except Exception:
            # signup error
            _logger.exception("Exception during request handling")
            error = "Exception during request handling"

        return {
            'error': error
        }
