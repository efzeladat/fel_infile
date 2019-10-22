# -*- encoding: utf-8 -*-

{
    'name': 'FEL Infile',
    'version': '1.0',
    'category': 'Custom',
    'description': """ Integración con factura electrónica de Infile """,
    'author': 'Rodrigo Fernandez',
    'website': 'http://solucionesprisma.com/',
    'depends': ['account'],
    'data': [
        'views/account_view.xml',
    ],
    'external_dependencies': {
        'python': ['zeep']
    },
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
