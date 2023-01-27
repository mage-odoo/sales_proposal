from odoo import models, fields, api, _


class SaleProposalLine(models.Model):
    _name = 'sale.proposal.line'
    _description = 'Sales Proposal'

    name = fields.Text(string="Description",
                       compute='_compute_name', required=True, store=True,)
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    sequence = fields.Integer(string="Sequence", default=10)
    product_templaet_id = fields.Many2one(related='product_id.product_tmpl_id')
    customer_lead = fields.Float('Lead Time')
    proposal_id = fields.Many2one(
        comodel_name='sale.proposal', string='Proposal')
    price_unit = fields.Float(
        'Unit Price', compute='_compute_price_unit', store=True)
    product_uom_qty = fields.Float('Quantity', default="1.0")
    price_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.name

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line.product_id.list_price

    @api.depends('product_id', 'product_uom_qty')
    def _compute_price_subtotal(self):
        for line in self:
            price_subtotal = line.product_uom_qty*line.price_unit
            line.update({'price_subtotal': price_subtotal})

    @api.model
    def create(self, vals_list):
        print("create called")
        return super().create(vals_list)
