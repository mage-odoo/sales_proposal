# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.fields import Command
from odoo.http import request

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.payment import utils as payment_utils
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
        print(values)
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
            ('state', 'in', ['send', 'confirm', 'draft'])
        ]

    @http.route(['/my/proposal', '/my/proposal/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_proposal(self, **kwargs):
        values = self._prepare_sale_proposal_portal_rendering_values(
            proposal_page=True, **kwargs)
        print(values)
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
            print("Always called portal_proposal_page ", report_type)
            return self._show_report(model=order_sudo, report_type=report_type, report_ref='sales_proposal.sale_proposal_report_pdf_report', download=download)
        print("portal_proposal_page called in portal py")
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
        print(order_sudo.proposal_line_ids)
        return request.render("sales_proposal.sale_proposal_portal_template", values)
