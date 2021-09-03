# -*- encoding: utf-8 -*-

{
    'name': 'FEL Infile',
    'version': '1.0',
    'category': 'Custom',
    'description': """ Integración con factura electrónica de Infile """,
    'author': 'aquíH',
    'website': 'http://aquih.com/',
    'depends': ['fel_gt', 'fel_gt_extra'],
    'data': [
        'views/account_view.xml',
        # 'template/invoice_template.xml',
        'template/dte_fact_template.xml',
        'template/dte_fact_exp_template.xml',
        'template/dte_fcam_template.xml',
        'template/dte_anul_template.xml',
        'template/dte_fesp_template.xml',
        'template/dte_ncre_template.xml',
        'template/dte_ndeb_template.xml',
        # 'template/ejemplo.xml',
    ],
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
