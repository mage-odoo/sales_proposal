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

    def _prepare_proposal_domain(self, partner):
        return [
            ('message_partner_ids', 'child_of',
             [partner.commercial_partner_id.id]),
            ('state', 'in', ['send'])
        ]

    def _get_sale_proposal_searchbar_sortings(self):
        return {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('amount_total'), 'order': 'amount_total desc'},
        }

    # my/home portal prepare value for sale proposal
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
        proposals = SaleProposal.search(
            domain, order=sort_proposal, limit=self._items_per_page, offset=pager_values['offset'])
        values = ({
            'date': date_begin,
            'proposals': proposals.sudo() if proposal_page else SaleProposal,
            'page_name': 'proposal',
            'pager': pager_values,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        print(values)
        return values

    @http.route(['/my/proposal', '/my/proposal/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_proposal(self, **kwargs):
        values = self._prepare_sale_proposal_portal_rendering_values(
            proposal_page=True, **kwargs)
        return request.render("sales_proposal.portal_my_proposals", values)

    @http.route(['/my/proposal/<int:order_id>'], type='http', auth="public", website=True)
    def portal_proposal_page(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            proposal_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=proposal_sudo, report_type=report_type, report_ref='sales_proposal.sale_proposal_report_pdf_report', download=download)
        backend_url = f'/web#model={proposal_sudo._name}'\
            f'&id={proposal_sudo.id}'\
            f'&action={proposal_sudo._get_portal_return_action().id}'\
            f'&view_type=form'
        values = {
            'sale_proposal': proposal_sudo,
            'message': message,
            'report_type': 'html',
            'backend_url': backend_url,
            'res_company': proposal_sudo.company_id,
        }
        return request.render("sales_proposal.sale_proposal_portal_template", values)

    @http.route(['/my/proposal/<int:order_id>/update'], type='json', auth="public", website=True)
    def portal_update_page(self, order_id, access_token=None, data=None, **kw):
        try:
            proposal_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
            if data['field'] in ['product_uom_qty', 'price_unit']:
                order_line_sudo = proposal_sudo.proposal_line_ids.filtered(
                    lambda lines: lines.id == int(data['line_id']))
                data['value'] = 1 if (data['field'] == 'product_uom_qty' and int(
                    data['value']) <= 0) else data['value']
                data['value'] = 0 if (data['field'] == 'price_unit' and int(
                    data['value']) < 0) else data['value']
                order_line_sudo.write(
                    {data['field']: float(ceil(data['value']))})
            field_name = ' Quantity ' if data['field'] == 'product_uom_qty' else ' Unit Price '
            body = f'''
            <div class = 'o_TrackingValue d-flex align-items-center flex-wrap mb-1' role = 'group'>
            <span class = 'o_TrackingValue_oldValue me-1 px-1 text-muted fw-bold'> {data['oldvalue']}
            <i class = 'o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600' title = 'Changed' role = 'img' aria-label = 'Changed'></i >
            <span value="" class = 'o_TrackingValue_newValue me-1 fw-bold text-info'> {float(data['value'])} 
            <span class = 'o_TrackingValue_fieldName ms-1 fst-italic text-muted'> ({field_name})
            </div>
            '''
            proposal_sudo.message_post(
                body=body)
        except (AccessError, MissingError):
            print("Missing or AccessError on /my/proposal/%s/update" % (order_id))

    @ http.route(['/my/proposal/<int:order_id>/reject'], type='http', auth="public", website=True)
    def portal_reject_page(self, order_id, access_token=None, name=None):
        print("reject method called")
        access_token = access_token or request.httprequest.args.get(
            'access_token')
        try:
            proposal_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}
        try:
            proposal_sudo.write({'state': 'cancel'})
            print(proposal_sudo)
        except (TypeError):
            print("%s data not deletede " % (proposal_sudo))
        message = "&message=rejected"
        return request.redirect(proposal_sudo.get_portal_url(query_string=message))

    @ http.route(['/my/proposal/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_accept__page(self, order_id, access_token=None, name=None, signature=None):
        access_token = access_token or request.httprequest.args.get(
            'access_token')
        try:
            proposal_sudo = self._document_check_access(
                'sale.proposal', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}
        try:
            proposal_sudo.write({
                'state': 'confirm',
                'date_order': fields.datetime.now(),
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'sales_proposal.sale_proposal_report_pdf_report', [proposal_sudo.id])[0]

        _message_post_helper(
            'sale.proposal',
            proposal_sudo.id,
            _('Proposal signed by %s', name),
            attachments=[('%s.pdf' % proposal_sudo.name, pdf)],
            token=access_token,
        )
        proposal_sudo.move_to_quotation()
        query_string = "&message=sign_ok"
        return {
            'force_refresh': True,
            'redirect_url': proposal_sudo.get_portal_url(query_string=query_string)
        }
