from odoo import models, fields, api, _
from odoo.tools import html_keep_url, is_html_empty
from odoo.addons.portal.controllers.mail import _message_post_helper


class SaleProposal(models.Model):
    _name = 'sale.proposal'
    _description = 'Sales Proposal'
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']

    # === FIELDS ===#
    name = fields.Char(
        readonly=True,
        required=True,
        index=True,
        copy=False,
        default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company',
        string='company',
        required=True,
        default=lambda self: self.env.company)
    date_order = fields.Datetime(
        string='Proposal Date',
        required=True,
        default=fields.Datetime.now)
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer')
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist')
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
        compute='_compute_payment_term_id',
        store=True,
        readonly=False, precompute=True,
        check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Proposal Template')
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('send', "Send"),
            ('confirm', "Confirm"),
            ('cancel', "Cancel"),
        ],
        string="Status", required=True,
        copy=False, tracking=True,
        default='draft')
    validity_date = fields.Date(
        string="Expiration",
        store=True, readonly=False, copy=False)
    note = fields.Html(
        string="Terms and conditions",
        compute='_compute_note',
        store=True, readonly=False, precompute=True)
    proposal_line_ids = fields.One2many(
        comodel_name='sale.proposal.line',
        inverse_name='proposal_id',
        string="Proposal Lines",
        copy=True)
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Salesperson",
        compute='_compute_user_id',
        store=True, readonly=False, precompute=True, index=True,
        tracking=True)
    team_id = fields.Many2one(
        comodel_name='crm.team',
        string="Sales Team",
        compute='_compute_team_id',
        store=True, readonly=False, precompute=True, ondelete="set null",
        change_default=True, check_company=True,  # Unrequired company
        tracking=True)
    require_signature = fields.Boolean(
        string="Online Signature",
        compute='_compute_require_signature',
        store=True, readonly=False, precompute=True,
        help="Request a online signature")
    require_payment = fields.Boolean(
        string="Online Payment",
        compute='_compute_require_payment',
        store=True, readonly=False, precompute=True)
    client_proposal_ref = fields.Char(
        string="Customer Reference", copy=False, store=True, readonly=False, compute='_compute_client_proposal_ref')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        compute='_compute_fiscal_position_id',
        store=True, readonly=False, precompute=True, check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular."
        "The default value comes from the customer.",
        domain="[('company_id', '=', company_id)]")
    tag_ids = fields.Many2many(
        comodel_name='crm.tag',
        relation='sale_proposal_tag_rel',
        column1='order_id', column2='tag_id',
        string="Tags")
    origin = fields.Char(
        string="Source Document",
        help="Reference of the document that generated this sales proposal request")
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null')
    source_id = fields.Many2one(ondelete='set null')
    signature = fields.Image(
        string="Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char(
        string="Signed By", copy=False)
    signed_on = fields.Datetime(
        string="Signed On", copy=False)
    amount_total = fields.Monetary(
        'Amount Total', default="0.0",
        currency_field='currency_id', store=True,
        compute='_compute_amounts')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    tax_totals = fields.Binary(
        compute='_compute_tax_totals',
        exportable=False)
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        store=True,
        compute='_compute_amounts',
        tracking=True)
    amount_tax = fields.Monetary(
        string="Taxes",
        store=True,
        compute='_compute_amounts')

    @api.depends('partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        cache = {}
        for proposal in self:
            if not proposal.partner_id:
                proposal.fiscal_position_id = False
                continue
            key = (proposal.company_id.id, proposal.partner_id.id)
            if key not in cache:
                cache[key] = self.env['account.fiscal.position'].with_company(
                    proposal.company_id
                )._get_fiscal_position(proposal.partner_id)
            proposal.fiscal_position_id = cache[key]

    @api.depends('partner_id')
    def _compute_client_proposal_ref(self):
        for proposal in self:
            proposal.client_proposal_ref = proposal.partner_id.ref

    @api.depends('company_id')
    def _compute_require_signature(self):
        for proposal in self:
            proposal.require_signature = proposal.company_id.portal_confirmation_sign

    @api.depends('company_id')
    def _compute_require_payment(self):
        for proposal in self:
            proposal.require_payment = proposal.company_id.portal_confirmation_pay

    @api.depends('proposal_line_ids.price_subtotal')
    def _compute_amounts(self):
        for proposal in self:
            proposal.amount_total = sum(
                proposal.proposal_line_ids.mapped('price_subtotal'))

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('proposal_line_ids.tax_id', 'proposal_line_ids.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for proposal in self:
            proposal_line = proposal.proposal_line_ids
            proposal.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in proposal_line],
                proposal.currency_id or proposal.company_id.currency_id,
            )

    @api.depends('proposal_line_ids.price_subtotal', 'proposal_line_ids.price_tax', 'proposal_line_ids.price_total')
    def _compute_amounts(self):
        for proposal in self:
            proposal_line = proposal.proposal_line_ids
            proposal.amount_untaxed = sum(
                proposal_line.mapped('price_subtotal'))
            proposal.amount_total = sum(proposal_line.mapped('price_total'))
            proposal.amount_tax = sum(proposal_line.mapped('price_tax'))

    @api.depends('partner_id', 'user_id')
    def _compute_team_id(self):
        cached_teams = {}
        for proposal in self:
            default_team_id = self.env.context.get(
                'default_team_id', False) or proposal.team_id.id or proposal.partner_id.team_id.id
            user_id = proposal.user_id.id
            company_id = proposal.company_id.id
            key = (default_team_id, user_id, company_id)
            if key not in cached_teams:
                cached_teams[key] = self.env['crm.team'].with_context(
                    default_team_id=default_team_id
                )._get_default_team_id(
                    user_id=user_id, domain=[('company_id', 'in', [company_id, False])])
            proposal.team_id = cached_teams[key]

    @api.depends('partner_id')
    def _compute_user_id(self):
        for proposal in self:
            if not proposal.user_id:
                proposal.user_id = proposal.partner_id.user_id or proposal.partner_id.commercial_partner_id.user_id or self.env.user

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for proposal in self:
            proposal = proposal.with_company(proposal.company_id)
            proposal.payment_term_id = proposal.partner_id.property_payment_term_id

    @api.depends('partner_id')
    def _compute_note(self):
        use_invoice_terms = self.env['ir.config_parameter'].sudo(
        ).get_param('account.use_invoice_terms')
        if not use_invoice_terms:
            return
        for proposal in self:
            proposal = proposal.with_company(proposal.company_id)
            if proposal.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(proposal._get_note_url() + '/terms')
                proposal.note = _('Terms & Conditions: %s', baseurl)
            elif not is_html_empty(self.env.company.invoice_terms):
                proposal.note = proposal.with_context(
                    lang=proposal.partner_id.lang).env.company.invoice_terms

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.proposal', sequence_date=seq_date) or _("New")
        return super().create(vals_list)

    def action_send_proposal_mail(self):
        self.ensure_one()
        mail_template = self.env.ref(
            'sales_proposal.email_template_edi_sale_proposal')
        ctx = {
            'sale_proposal_id': self.id,
            'default_template_id': mail_template.id if mail_template else None,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    # portal.mixin override
    def _compute_access_url(self):
        super()._compute_access_url()
        for proposal in self:
            proposal.access_url = f'/my/proposal/{proposal.id}'

    def action_preview_sale_proposal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def action_sale_proposal_confirm(self):
        for proposal in self:
            proposal.state = 'confirm'
            proposal.date_order = fields.datetime.now()
        self.move_to_quotation()

    def action_sale_proposal_cancel(self):
        for proposal in self:
            proposal.state = 'cancel'

    def action_sale_proposal_draft(self):
        for proposal in self:
            proposal.state = 'draft'

    def _get_proposal_lines_to_report(self):
        _lines = False
        if self.proposal_line_ids:
            _lines = self.proposal_line_ids
        return _lines

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('sales_proposal.sale_proposal_action')

    def _has_to_be_confirm(self, include_draft=False):
        if include_draft:
            pass

    def _has_to_be_paid(self, include_draft=False):
        if include_draft:
            pass
        return True

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s_Proposal' % (self.name)

    def move_to_quotation(self):
        self.ensure_one()
        if self.state == 'confirm':
            order_id = self.env['sale.order'].sudo().create({
                'company_id': self.company_id.id,
                'date_order': self.date_order,
                'partner_id': self.partner_id.id,
                'user_id': self.user_id.id,
                'team_id': self.team_id.id,
                'client_order_ref': self.client_proposal_ref,
                'tag_ids': self.tag_ids.ids,
                'fiscal_position_id': self.fiscal_position_id.id,
                'origin': self.origin,
                'campaign_id': self.campaign_id.id,
                'medium_id': self.medium_id.id,
                'source_id': self.source_id.id,
                "amount_total": self.amount_total,
                "amount_untaxed": self.amount_untaxed,
                "amount_tax": self.amount_tax,
                "tax_totals": self.tax_totals,
                "payment_term_id": self.payment_term_id.id,
                "note": self.note,
                'sale_order_template_id': self.sale_order_template_id.id,
                'validity_date': self.validity_date,
                'state': 'draft'})
            print("clear Quatation")
            for line_ids in self.proposal_line_ids:
                self.env['sale.order.line'].sudo().create({
                    'name': line_ids.name,
                    'company_id': line_ids.company_id,
                    'order_id': order_id.id,
                    'sequence': line_ids.sequence,
                    'product_id': line_ids.product_id.id,
                    'price_unit':  line_ids.price_unit,
                    'product_uom_qty': line_ids.product_uom_qty,
                    'tax_id': line_ids.tax_id.ids,
                    'discount': line_ids.discount,
                    'currency_id': line_ids.currency_id.id,
                    'customer_lead': line_ids.customer_lead,
                    'price_subtotal': line_ids.price_subtotal,
                    'price_tax': line_ids.price_tax,
                    'price_total': line_ids.price_total,
                    'display_type': line_ids.display_type,
                    'currency_id': line_ids.currency_id.id
                })
            body = f'The Quotation is created: <a href=# data-oe-model=sale.order data-oe-id={order_id.id}>{order_id.name}</a>'
            self.message_post(body=body)
            return True
