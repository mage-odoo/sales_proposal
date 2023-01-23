{
    'name': 'Sales Proposal',
    'version': '1.0.0',
    'category': 'Sales',
    'author': ' Odoo S.A.',
    'summary': 'Sales Proposal',
    'description': """To Add Functional Specification For Sales Menu""",
    'depends': [
        'sale_management'
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/ir_sequence_data.xml',

        'views/sale_order_views.xml',
        'views/sale.xml',

        'report/ir_actions_report_templates.xml',
        'report/sale_proposal_report.xml',

    ],
    'demo': [],
    'sequence': -300,
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
