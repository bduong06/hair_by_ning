from odoo import http
from odoo.http import request

class InvoiceShortenerController(http.Controller):

    # auth="public" opens the route to the world without requiring a standard login screen first
    @http.route('/inv/<int:invoice_id>', type='http', auth='public', website=True)
    def redirect_to_secure_invoice(self, invoice_id, **kw):
        # 1. Fetch the invoice record securely using sudo() to bypass standard access rights
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        
        if invoice.exists() and invoice.move_type == 'out_invoice':
            # 2. Retrieve Odoo's native secure portal share URL (which includes the access token)
            secure_portal_url = invoice.get_portal_url()
            
            # 3. Securely redirect the browser straight to the layout screen
            return request.redirect(secure_portal_url)
        
        # Fallback if the invoice doesn't exist
        return request.render('website.404')