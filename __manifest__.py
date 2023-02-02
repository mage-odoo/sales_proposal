{
    'name': 'Sales Proposal',
    'version': '16.0.1.0',
    'category': 'Sales',
    'author': ' Odoo PS',
    'summary': 'Sales Proposal',
    'description': """To Add Functional Specification For Sales Menu""",
    'depends': [
        'sale_management'
    ],
    'data': [
        'security/ir.model.access.csv',

        'report/sale_proposal_report.xml',
        'report/ir_actions_report_templates.xml',

        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',

        'views/sale_portal_templates.xml',
        'views/sale_proposal_view.xml',
        'views/sale.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            '/sales_proposal/static/src/js/proposal.js',
        ],
    }
}
