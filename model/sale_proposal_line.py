from odoo import models, fields, api, _


class SaleProposalLine(models.Model):
    _name = 'sale.proposal.line'
    _description = 'Sales Proposal Line is same as sale order line'
    
    name = fields.Text(string="Description",
                        compute='_compute_name',required=True,)
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    sequence = fields.Integer(string="Sequence", default=10)
    product_templaet_id=fields.Many2one(related='product_id.product_tmpl_id')
    customer_lead = fields.Float('Lead Time')
    proposal_id = fields.Many2one(comodel_name='sale.proposal', string='Proposal')
    price_unit = fields.Float('Unit Price')
    product_uom_qty = fields.Float('Quantity')
    price_subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            line.name =  line.product_id.name#+" ["+line.proposal_id.state+" ]"