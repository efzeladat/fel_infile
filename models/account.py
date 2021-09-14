# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from html import unescape

import base64
from lxml import etree
import requests
import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    pdf_fel = fields.Char('PDF FEL', copy=False)
    establecimiento = fields.Selection([
        ('1', 'Grupo de Alimentos y Bebidas Bilste'),
        ('2', 'Magnolia'),
        ('3', 'Deposito San Arnoldo'),
        ('4', 'San Arnoldo 2'),
    ], required=True, string='Establecimiento')

    def _post(self, soft=True):
        if self.certificar2():
            return super(AccountMove, self)._post(soft)

    def post(self):
        if self.certificar2():
            return super(AccountMove, self).post()

    def certificar2(self):

        impuestos_totales = []
        self.ensure_one()

        if self.invoice_line_ids.product_uom_id.name == 'Unidades':
            uom = 'UND'

        for lines in self.invoice_line_ids:
            price_by_line = (lines.price_unit - lines.discount) * lines.quantity
            switcher = {
                1: 0.06,
                2: 0.075,
                3: 0.075,
                4: 0.075,
                5: 0.075,
                6: 0.085,
                7: 0.075,
                8: 0.075,
            }
            idb_tax_percentage = switcher.get(int(lines.product_id.codigo_unidad_gravable), 0)
            for taxes in lines.tax_ids:
                if taxes.name == 'IVA por Pagar' or taxes.name == 'IVA':
                    taxes.name = 'IVA'
                    lines.tax_iva = round(price_by_line - (price_by_line / round((1+taxes.amount/100), 2)), 2)
                else:
                    tmp_name = taxes.name.split(' - ')
                    taxes.name = tmp_name[0]
                    lines.tax_idb = round(lines.product_id.price_suggested * lines.quantity * idb_tax_percentage, 2)

        for taxx in self.amount_by_group:
            if taxx[0] == 'Impuestos':
                impuestos_totales.append(['BEBIDAS ALCOHOLICAS', taxx[1]])
            else:
                impuestos_totales.append(['IVA', taxx[1]])

        vat_company = self.company_id.vat.split('-')
        vat_company = vat_company[0] + vat_company[1]
        vat_partner = self.partner_id.vat.split('-')
        vat_partner = vat_partner[0] + vat_company[1]

        if self.invoice_payment_term_id.name == 'Pago inmediato':
            dte = self.env.ref('fel_infile.dte_fact_template')._render({
                'move': self,
                'tipo_doc': 'FACT',
                'fecha_hora_emision': self.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
                'bien_servicio': 'B',
                'uom_display': uom,
                'impuestos_totales': impuestos_totales,
                'vat_company': vat_company,
                'vat_partner': vat_partner
            })
        else:
            dte = self.env.ref('fel_infile.dte_fcam_template')._render({
                'move': self,
                'tipo_doc': 'FCAM',
                'fecha_hora_emision': self.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
                'bien_servicio': 'B',
                'uom_display': uom,
                'impuestos_totales': impuestos_totales,
                'vat_company': vat_company,
                'vat_partner': vat_partner
            })

        dte = unescape(dte.decode('utf-8')).replace(r'&', '&amp;').replace('\n', '').encode('utf-8')
        # dte = dte..replace(r'&', '&amp;')
        logging.info(dte)
        data = dte

        headers = {
            'UsuarioApi': 'GBILSTE',
            'LlaveApi': '3F4664818CB5EE4C250E78443C6616B6',
            'UsuarioFirma': 'GBILSTE',
            'LlaveFirma': '656fb5fafafd6987e4f87e9577b811f7',
            'identificador': 'prueba1',
        }
        r = requests.post('https://certificadorcloud.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=data,
                          headers=headers)
        invoice = r.json()
        logging.info(invoice)

        certificacion_json = r.json()
        if certificacion_json['resultado']:
            self.firma_fel = certificacion_json['uuid']
            self.ref = str(certificacion_json['serie'])+'-'+str(certificacion_json['numero'])
            self.serie_fel = certificacion_json['serie']
            self.numero_fel = certificacion_json['numero']
            self.documento_xml_fel = certificacion_json['xml_certificado']
            self.resultado_xml_fel = certificacion_json['xml_certificado']
            self.pdf_fel = False
            self.certificador_fel = 'infile'
        else:
            self.error_certificador(str(certificacion_json['descripcion_errores']))
            return False

        return True

    def _reverse_moves(self, default_values_list=None, cancel=False):
        impuestos_totales = []
        self.ensure_one()

        if self.invoice_line_ids.product_uom_id.name == 'Unidades':
            uom = 'UND'

        for lines in self.invoice_line_ids:
            price_by_line = (lines.price_unit - lines.discount) * lines.quantity
            switcher = {
                1: 0.06,
                2: 0.075,
                3: 0.075,
                4: 0.075,
                5: 0.075,
                6: 0.085,
                7: 0.075,
                8: 0.075,
            }
            idb_tax_percentage = switcher.get(int(lines.product_id.codigo_unidad_gravable), 0)
            for taxes in lines.tax_ids:
                if taxes.name == 'IVA por Pagar' or taxes.name == 'IVA':
                    taxes.name = 'IVA'
                    lines.tax_iva = round(price_by_line - (price_by_line / round((1+taxes.amount/100), 2)), 2)
                else:
                    tmp_name = taxes.name.split(' - ')
                    taxes.name = tmp_name[0]
                    lines.tax_idb = round(lines.product_id.price_suggested * lines.quantity * idb_tax_percentage, 2)

        for taxx in self.amount_by_group:
            if taxx[0] == 'Impuestos':
                impuestos_totales.append(['BEBIDAS ALCOHOLICAS', taxx[1]])
            else:
                impuestos_totales.append(['IVA', taxx[1]])

        vat_company = self.company_id.vat.split('-')
        vat_company = vat_company[0] + vat_company[1]
        vat_partner = self.partner_id.vat.split('-')
        vat_partner = vat_partner[0] + vat_company[1]

        dte = self.env.ref('fel_infile.dte_ncre_template')._render({
            'move': self,
            'tipo_doc': 'NCRE',
            'fecha_hora_emision': self.create_date.strftime('%Y-%m-%d'),
            'bien_servicio': 'B',
            'uom_display': uom,
            'impuestos_totales': impuestos_totales,
            'vat_company': vat_company,
            'vat_partner': vat_partner
        })

        dte = unescape(dte.decode('utf-8')).replace(r'&', '&amp;').replace('\n', '').encode('utf-8')
        # dte = dte..replace(r'&', '&amp;')
        logging.info(dte)
        data = dte

        headers = {
            'UsuarioApi': 'GBILSTE',
            'LlaveApi': '3F4664818CB5EE4C250E78443C6616B6',
            'UsuarioFirma': 'GBILSTE',
            'LlaveFirma': '656fb5fafafd6987e4f87e9577b811f7',
            'identificador': 'prueba1',
        }
        r = requests.post('https://certificadorcloud.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=data,
                          headers=headers)
        invoice = r.json()
        logging.info(invoice)

        certificacion_json = r.json()
        if certificacion_json['resultado']:
            self.firma_fel = certificacion_json['uuid']
            self.ref = str(certificacion_json['serie'])+'-'+str(certificacion_json['numero'])
            self.serie_fel = certificacion_json['serie']
            self.numero_fel = certificacion_json['numero']
            self.documento_xml_fel = certificacion_json['xml_certificado']
            self.resultado_xml_fel = certificacion_json['xml_certificado']
            self.pdf_fel = False
            self.certificador_fel = 'infile'
        else:
            self.error_certificador(str(certificacion_json['descripcion_errores']))
            return False

        return True

    # def button_cancel(self):
    #     result = super(AccountMove, self).button_cancel()
    #     for factura in self:
    #         if factura.requiere_certificacion() and factura.firma_fel:
    #             dte = factura.dte_anulacion()
    #
    #             xmls = etree.tostring(dte, encoding='UTF-8')
    #             xmls = xmls.decode('utf-8').replace('&amp;', '&').encode('utf-8')
    #             xmls_base64 = base64.b64encode(xmls)
    #             logging.warn(xmls)
    #
    #             headers = { 'Content-Type': 'application/json' }
    #             data = {
    #                 'llave': factura.company_id.token_firma_fel,
    #                 'archivo': xmls_base64.decode('utf-8'),
    #                 'codigo': factura.company_id.vat.replace('-',''),
    #                 'alias': factura.company_id.usuario_fel,
    #             }
    #             r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
    #             logging.warn(r.text)
    #             firma_json = r.json()
    #             if firma_json['resultado']:
    #
    #                 headers = {
    #                     'USUARIO': factura.company_id.usuario_fel,
    #                     'LLAVE': factura.company_id.clave_fel,
    #                     'IDENTIFICADOR': factura.journal_id.code+str(factura.id),
    #                     'Content-Type': 'application/json',
    #                 }
    #                 data = {
    #                     'nit_emisor': factura.company_id.vat.replace('-',''),
    #                     'correo_copia': factura.company_id.email,
    #                     'xml_dte': firma_json['archivo']
    #                 }
    #                 r = requests.post('https://certificador.feel.com.gt/fel/anulacion/v2/dte/', json=data, headers=headers)
    #                 logging.warn(r.text)
    #                 certificacion_json = r.json()
    #                 if not certificacion_json['resultado']:
    #                     raise UserError(str(certificacion_json['descripcion_errores']))
    #             else:
    #                 raise UserError(r.text)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

class ResCompany(models.Model):
    _inherit = 'res.company'

    user_api = fields.Char('Usuario API')
    key_api = fields.Char('Llave API')
    user_sing = fields.Char('Usuario Firma')
    key_sing = fields.Char('Llave Firma')
    office_ids = fields.One2many('res.office', 'id')
    postal_code = fields.Integer('Codigo Postal')

class ResOffice(models.Model):
    _name = 'res.office'
    _description = 'Office Model by Company'

    id = fields.Id()
    name = fields.Char()
    description = fields.Char()
    code = fields.Char()

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    tax_iva = fields.Float('iva')
    tax_idb = fields.Float('idb')
