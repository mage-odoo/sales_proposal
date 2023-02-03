from odoo import models, fields, api, _
from collections import defaultdict


class SaleProposalLine(models.Model):
    _name = 'sale.proposal.line'
    _description = 'Sales Proposal'

    # === FIELDS ===#
    name = fields.Text(
        string="Description",
        compute='_compute_name',
        required=True, store=True,
        readonly=False)
    company_id = fields.Many2one(
        'res.company',
        string='company',
        default=lambda self: self.env.company)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product Variant')
    sequence = fields.Integer(string="Sequence", default=10)
    product_templaet_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string="Product")
    customer_lead = fields.Float('Lead Time')
    proposal_id = fields.Many2one(
        comodel_name='sale.proposal',
        required=True, ondelete='cascade',
        string='Proposal')
    price_unit = fields.Float(
        'Unit Price',
        compute='_compute_price_unit',
        store=True,
        required=True,
        readonly=False)
    product_uom_qty = fields.Float(
        'Quantity',
        default="1.0",
        required=True,
        compute="_compute_product_uom_qty",
        store=True, readonly=False)
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        store=True, readonly=False)
    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        store=True, readonly=False, default="0.0")
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id)
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True)
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount',
        store=True)
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount',
        store=True)
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)

    @api.depends('display_type', 'product_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.name

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.display_type:
                line.price_unit = 0
                return
            line.price_unit = line.product_id.list_price

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.proposal_id.partner_id,
            currency=self.proposal_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )

    @ api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            line.product_uom_qty = line.product_uom_qty if line.product_uom_qty > 0 else 1
            line.discount = line.discount if line.discount >= 0 else 0
            line.price_unit = line.price_unit if line.price_unit >= 0 else 0
            if line.discount > 100:
                line.discount = 100
            tax_results = self.env['account.tax']._compute_taxes(
                [line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']
            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })
