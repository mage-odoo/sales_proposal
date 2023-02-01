from odoo import models, fields, api, _
from collections import defaultdict


class SaleProposalLine(models.Model):
    _name = 'sale.proposal.line'
    _description = 'Sales Proposal'

    name = fields.Text(string="Description",
                       compute='_compute_name', required=True, store=True, precompute=True)
    company_id = fields.Many2one(
        'res.company', string='company', required=True, default=lambda self: self.env.company)
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product Variant')
    sequence = fields.Integer(string="Sequence", default=10)
    product_templaet_id = fields.Many2one(
        related='product_id.product_tmpl_id', string="Product")
    customer_lead = fields.Float('Lead Time')
    proposal_id = fields.Many2one(
        comodel_name='sale.proposal', ondelete='cascade',  string='Proposal')
    price_unit = fields.Float(
        'Unit Price', compute='_compute_price_unit', store=True, tracking=True)
    product_uom_qty = fields.Float('Quantity', default="1.0", tracking=True)
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        # compute='_compute_tax_id',
        store=True, readonly=False,
        context={'active_test': False})
    discount = fields.Float(
        string="Discount (%)",
        compute='_compute_discount',
        digits='Discount',
        store=True, readonly=False, default="0.0")
    price_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True, tracking=True)
    price_tax = fields.Float(
        string="Total Tax",
        compute='_compute_amount',
        store=True)
    price_total = fields.Monetary(
        string="Total",
        compute='_compute_amount',
        store=True)

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.name

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line.product_id.list_price

    @api.depends('product_id', 'product_uom_qty')
    def _compute_discount(self):
        for line in self:
            if not (
                line.proposal_id.pricelist_id
                and line.proposal_id.pricelist_id.discount_policy == 'without_discount'
            ):
                continue

            line.discount = 0.0

            if not line.pricelist_item_id:
                # No pricelist rule was found for the product
                # therefore, the pricelist didn't apply any discount/change
                # to the existing sales price.
                continue

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
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

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
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

    @api.depends('product_id', 'product_uom_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            price_subtotal = line.product_uom_qty*line.price_unit
            line.update({'price_subtotal': price_subtotal})

    @api.model
    def create(self, vals_list):
        print("create called")
        return super().create(vals_list)
