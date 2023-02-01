# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
from math import ceil
from odoo import fields, http,  _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        SaleProposal = request.env['sale.proposal']
        if 'proposal_count' in counters:
            values['proposal_count'] = SaleProposal.search_count(self._prepare_proposal_domain(partner)) \
                if SaleProposal.check_access_rights('read', raise_exception=False) else 0
        return values

    def _prepare_sale_proposal_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, proposal_page=False, **kwargs
    ):
        SaleProposal = request.env['sale.proposal']
        if not sortby:
            sortby = 'date'
        partner = request.env.user.partner_id
        values = self._prepare_portal_layout_values()  # don't know
        if proposal_page:
            url = "/my/proposal"
            domain = self._prepare_proposal_domain(partner)
        searchbar_sortings = self._get_sale_proposal_searchbar_sortings()
        sort_proposal = searchbar_sortings[sortby]['order']
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]
        pager_values = portal_pager(
            url=url,
            total=SaleProposal.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin,
                      'date_end': date_end, 'sortby': sortby},
        )
        orders = SaleProposal.search(
            domain, order=sort_proposal, limit=self._items_per_page, offset=pager_values['offset'])
        values.update({
            'date': date_begin,
            'proposals': orders.sudo() if proposal_page else SaleProposal,
            'orders': orders.sudo() if not proposal_page else SaleProposal,
            'page_name': 'proposal',
            'pager': pager_values,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return values

    def _prepare_proposal_domain(self, partner):
        return [
            ('message_partner_ids', 'child_of', [
                partner.commercial_partner_id.id]),
            ('state', 'in', ['send'])
        ]

    @http.route(['/my/proposal', '/my/proposal/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_proposal(self, **kwargs):
        values = self._prepare_sale_proposal_portal_rendering_values(
            proposal_page=True, **kwargs)
        return request.render("sales_proposal.portal_my_proposals", values)

    def _get_sale_proposal_searchbar_sortings(self):
        return {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }

    @http.route(['/my/proposal/<int:order_id>'], type='http', auth="public", website=True)
    def portal_proposal_page(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='sales_proposal.sale_proposal_report_pdf_report', download=download)
        backend_url = f'/web#model={order_sudo._name}'\
            f'&id={order_sudo.id}'\
            f'&action={order_sudo._get_portal_return_action().id}'\
            f'&view_type=form'
        values = {
            'sale_proposal': order_sudo,
            'message': message,
            'report_type': 'html',
            'backend_url': backend_url,
            'res_company': order_sudo.company_id,  # Used to display correct company logo
        }
        return request.render("sales_proposal.sale_proposal_portal_template", values)

    @http.route(['/my/proposal/<int:order_id>/update'], type='json', auth="public", website=True)
    def portal_update_page(self, order_id, access_token=None, data=None, **kw):
        try:
            order_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
            if data['field'] in ['product_uom_qty', 'price_unit']:
                order_line_sudo = order_sudo.proposal_line_ids.filtered(
                    lambda lines: lines.id == int(data['line_id']))
                if (data['field'] == 'product_uom_qty' and int(data['value']) == 0):
                    data['value'] = 1
                order_line_sudo.write(
                    {data['field']: float(ceil(data['value']))})
        except (AccessError, MissingError):
            print("Missing or AccessError on /my/proposal/%s/update" % (order_id))

    @http.route(['/my/proposal/<int:order_id>/reject'], type='json', auth="public", website=True)
    def portal_reject_page(self, order_id, access_token=None, data=None, **kw):
        if data['proposal_id']:
            proposal_id = request.env['sale.proposal'].browse(
                int(data['proposal_id']))
            proposal_id.write({'state': 'cancel'})

    @http.route(['/my/proposal/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_accept__page(self, order_id, access_token=None, name=None, signature=None):
        access_token = access_token or request.httprequest.args.get(
            'access_token')
        try:
            order_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}
        try:
            order_sudo.write({
                'state': 'confirm',
                'date_order': fields.datetime.now(),
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'sales_proposal.sale_proposal_report_pdf_report', [order_sudo.id])[0]

        _message_post_helper(
            'sale.proposal',
            order_sudo.id,
            _('Proposal signed by %s', name),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            token=access_token,
        )
        order_sudo.move_to_quotation()
        query_string = "&message=sign_ok"
        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string)
        }
