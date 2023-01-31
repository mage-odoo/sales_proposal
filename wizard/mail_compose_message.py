from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        if self.model == 'sale.proposal':
            if self.env.context.get('sale_proposal_id'):
                self.env['sale.proposal'].browse(
                    self.env.context.get('sale_proposal_id')).update({'state': 'send'})
        return super()._action_send_mail(auto_commit=auto_commit)
