from odoo import models, fields, api, _


class SaleProposal(models.Model):
    _name = 'sale.proposal'
    _description = 'Sales Proposal Model same as sale order model'
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(readonly=True, required=True, index=True, copy=False,
                       default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', string='company', required=True, default=lambda self: self.env.company)
    date_order = fields.Datetime(
        string='Order Date', required=True, default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Customer')
    partner_address = fields.Char(
        'Partner Address', related='partner_id.contact_address_complete')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
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
        copy=False, tracking=3,
        default='draft')
    validity_date = fields.Date(
        string="Expiration",
        store=True, readonly=False, copy=False)
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
        tracking=2)
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
        help="Request a online signature and/or payment to the customer in order to confirm orders automatically.")
    require_payment = fields.Boolean(
        string="Online Payment",
        compute='_compute_require_payment',
        store=True, readonly=False, precompute=True)
    client_proposal_ref = fields.Char(string="Customer Reference", copy=False)
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        compute='_compute_fiscal_position_id',
        store=True, readonly=False, precompute=True, check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
        "The default value comes from the customer.",
        domain="[('company_id', '=', company_id)]")
    tag_ids = fields.Many2many(
        comodel_name='crm.tag',
        relation='sale_proposal_tag_rel', column1='order_id', column2='tag_id',
        string="Tags")
    commitment_date = fields.Datetime(
        string="Delivery Date", copy=False,
        help="This is the delivery date promised to the customer. "
        "If set, the delivery order will be scheduled based on "
        "this date rather than product lead times.")
    origin = fields.Char(
        string="Source Document",
        help="Reference of the document that generated this sales order request")
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
        'Amount Total', default="0.0", currency_field='currency_id', store=True, compute='_compute_amounts')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    @api.depends('partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue
            key = (order.company_id.id, order.partner_id.id)
            if key not in cache:
                cache[key] = self.env['account.fiscal.position'].with_company(
                    order.company_id
                )._get_fiscal_position(order.partner_id)
            order.fiscal_position_id = cache[key]

    @api.depends('company_id')
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = order.company_id.portal_confirmation_sign

    @api.depends('company_id')
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = order.company_id.portal_confirmation_pay

    @api.depends('proposal_line_ids.price_subtotal')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order.amount_total = sum(
                order.proposal_line_ids.mapped('price_subtotal'))

    # dose any method call other model comute method
    @api.depends('partner_id', 'user_id')
    def _compute_team_id(self):
        cached_teams = {}
        for order in self:
            default_team_id = self.env.context.get(
                'default_team_id', False) or order.team_id.id or order.partner_id.team_id.id
            user_id = order.user_id.id
            company_id = order.company_id.id
            key = (default_team_id, user_id, company_id)
            if key not in cached_teams:
                cached_teams[key] = self.env['crm.team'].with_context(
                    default_team_id=default_team_id
                )._get_default_team_id(
                    user_id=user_id, domain=[('company_id', 'in', [company_id, False])])
            order.team_id = cached_teams[key]

    @api.depends('partner_id')
    def _compute_user_id(self):
        for order in self:
            if not order.user_id:
                order.user_id = order.partner_id.user_id or order.partner_id.commercial_partner_id.user_id or self.env.user

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

    def send_proposal_mail(self):
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

    # def _compute_access_url(self):
    #     super()._compute_access_url()
    #     for order in self:
    #         print("_compute_access_url")
    #         print(order.id)
    #         order.access_url = f'/my/orders/{order.id}'

    # portal.mixin override
    def _compute_access_url(self):
        super()._compute_access_url()
        for proposal in self:
            proposal.access_url = f'/my/proposal/{proposal.id}'

    def action_preview_sale_proposal(self):
        self.ensure_one()
        print(self.get_portal_url())
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
        # report = 'sales_proposal.sale_proposal_report_pdf_report'
        # pdf_bin, unused_filetype = self.env['ir.actions.report'].with_context(
        #     snailmail_layout=not self.id, partner_invoice_id=self.id, partner_id=self.id, lang='en_US')._render_qweb_pdf(report, self.id)
        # print(pdf_bin)
        # print(unused_filetype)

    def sale_proposal_confirm(self):
        print("--------------confirm--------------")

    def sale_proposal_draft(self):
        for proposal in self:
            proposal.state = 'draft'

    def _get_proposal_lines_to_report(self):
        print("self value ", self)
        _lines = False
        if self.proposal_line_ids:
            _lines = self.proposal_line_ids
        # filtered(lambda line:and not line._get_downpayment_state())

        # def show_line(line):
        #     if not line.is_downpayment:
        #         return True
        #     elif line.display_type and down_payment_lines:
        #         return True  # Only show the down payment section if down payments were posted
        #     elif line in down_payment_lines:
        #         return True  # Only show posted down payments
        #     else:
        #         return False
        print("_get_proposal_lines_to_report from sale proposal", type(_lines))
        return _lines

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('sales_proposal.sale_proposal_action')

    def _has_to_be_confirm(self, include_draft=False):
        print(" _has_to_be_confirm called-----------------------------")
        if include_draft:
            pass

    def _has_to_be_paid(self, include_draft=False):
        print(" _has_to_be_paid called")
        if include_draft:
            pass
        return True

    '''use for downloaded file name'''

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s_Proposal' % (self.name)
