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
    # infile_response_ids = fields.Many2one('InvoiceResponse', string='Respuestas Infile')
    
    def _post(self, soft=True):
        if self.certificar2():
            return super(AccountMove, self)._post(soft)

    def post(self):
        if self.certificar2():
            return super(AccountMove, self).post()

    def certificar2(self):
        # for factura in self:
            # if factura.requiere_certificacion():
        self.ensure_one()

        # dte = self.env.ref('fel_infile.ejemplo')._render()
        self['company_id']['postal_code'] = 98713
        if self.invoice_line_ids.product_uom_id.name == 'Unidades':
            uom = 'UND'

        dte = self.env.ref('fel_infile.dte_fact_template')._render({
            'move': self,
            'fecha_hora_emision': self.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'bien_servicio': 'B',
            'uom_display': uom,
        })

        # dte = factura.dte_documento() Documento Edi
        # logging.warn(dte)
        dte = unescape(dte.decode('utf-8')).replace(r'&', '&amp;')

        logging.info(dte)

        data = dte

        headers = {
            'UsuarioApi': 'GBILSTE',
            'LlaveApi': '3F4664818CB5EE4C250E78443C6616B6',
            'UsuarioFirma': 'GBILSTE',
            'LlaveFirma': '656fb5fafafd6987e4f87e9577b811f7',
            'identificador': 'prueba-1'
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

        # return_data = self.env['fel_gt_extra.l10n_gt_infile_response'].create({
        #     'result':  invoice.result,
        #     'date_transaction':  invoice.date_transaction,
        #     'origin':  invoice.origin,
        #     'description':  invoice.description,
        #     'emition_control':  invoice.emition_control,
        #     'infile_alert':  invoice.infile_alert,
        #     'infile_alert_description':  invoice.infile_alert_description,
        #     'sat_alert':  invoice.sat_alert,
        #     'sat_alert_description':  invoice.sat_alert_description,
        #     'errors':  invoice.errors,
        #     'error_description':  invoice.error_description,
        #     'aditional_information':  invoice.aditional_information,
        #     'uuid':  invoice.uuid,
        #     'serie':  invoice.serie,
        #     'number':  invoice.number,
        #     'xml_certificado':  invoice.xml_certificado
        # })

        return True

    # def certificar(self):
    #     for factura in self:
    #         if factura.requiere_certificacion():
    #             self.ensure_one()
    #
    #             if factura.error_pre_validacion():
    #                 return False
    #
    #             dte = factura.dte_documento()
    #             logging.warn(dte)
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
    #                 r = requests.post('https://certificador.feel.com.gt/fel/certificacion/v2/dte/', json=data, headers=headers)
    #                 logging.warn(r.json())
    #                 certificacion_json = r.json()
    #                 if certificacion_json['resultado']:
    #                     factura.firma_fel = certificacion_json['uuid']
    #                     factura.ref = str(certificacion_json['serie'])+'-'+str(certificacion_json['numero'])
    #                     factura.serie_fel = certificacion_json['serie']
    #                     factura.numero_fel = certificacion_json['numero']
    #                     factura.documento_xml_fel = xmls_base64
    #                     factura.resultado_xml_fel = certificacion_json['xml_certificado']
    #                     factura.pdf_fel = 'https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid='+certificacion_json['uuid']
    #                     factura.certificador_fel = 'infile'
    #                 else:
    #                     factura.error_certificador(str(certificacion_json['descripcion_errores']))
    #                     return False
    #
    #             else:
    #                 factura.error_certificador(r.text)
    #                 return False
    #
    #     return True
        
    def button_cancel(self):
        result = super(AccountMove, self).button_cancel()
        for factura in self:
            if factura.requiere_certificacion() and factura.firma_fel:
                dte = factura.dte_anulacion()
                
                xmls = etree.tostring(dte, encoding='UTF-8')
                xmls = xmls.decode('utf-8').replace('&amp;', '&').encode('utf-8')
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls)

                headers = { 'Content-Type': 'application/json' }
                data = {
                    'llave': factura.company_id.token_firma_fel,
                    'archivo': xmls_base64.decode('utf-8'),
                    'codigo': factura.company_id.vat.replace('-',''),
                    'alias': factura.company_id.usuario_fel,
                }
                r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                logging.warn(r.text)
                firma_json = r.json()
                if firma_json['resultado']:

                    headers = {
                        'USUARIO': factura.company_id.usuario_fel,
                        'LLAVE': factura.company_id.clave_fel,
                        'IDENTIFICADOR': factura.journal_id.code+str(factura.id),
                        'Content-Type': 'application/json',
                    }
                    data = {
                        'nit_emisor': factura.company_id.vat.replace('-',''),
                        'correo_copia': factura.company_id.email,
                        'xml_dte': firma_json['archivo']
                    }
                    r = requests.post('https://certificador.feel.com.gt/fel/anulacion/v2/dte/', json=data, headers=headers)
                    logging.warn(r.text)
                    certificacion_json = r.json()
                    if not certificacion_json['resultado']:
                        raise UserError(str(certificacion_json['descripcion_errores']))
                else:
                    raise UserError(r.text)

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



