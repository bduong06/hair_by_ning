from odoo import http
from odoo.addons.account.controllers.portal import PortalAccount

class HbnPortalAccount(PortalAccount):
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=False)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        return super().portal_my_invoice_detail(invoice_id, access_token=access_token, report_type=report_type, download=download, **kw)