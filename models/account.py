# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

from datetime import datetime
import base64
from lxml import etree
import requests
import re

#from import XMLSigner

import logging

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    pdf_fel = fields.Char('PDF FEL', copy=False)

    def invoice_validate(self):
        detalles = []
        subtotal = 0
        for factura in self:
            dte = factura.dte_documento()
            logging.warn(dte)
            if dte:
                xmls = etree.tostring(dte, encoding="UTF-8")
                xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls)

                headers = { "Content-Type": "application/json" }
                data = {
                    "llave": factura.journal_id.token_firma_fel,
                    "archivo": xmls_base64.decode("utf-8"),
                    "codigo": factura.company_id.vat.replace('-',''),
                    "alias": factura.journal_id.usuario_fel,
                }
                r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                logging.warn(r.text)
                firma_json = r.json()
                if firma_json["resultado"]:

                    headers = {
                        "USUARIO": factura.journal_id.usuario_fel,
                        "LLAVE": factura.journal_id.clave_fel,
                        "IDENTIFICADOR": factura.journal_id.code+str(factura.id),
                        "Content-Type": "application/json",
                    }
                    data = {
                        "nit_emisor": factura.company_id.vat.replace('-',''),
                        "correo_copia": factura.company_id.email,
                        "xml_dte": firma_json["archivo"]
                    }
                    r = requests.post("https://certificador.feel.com.gt/fel/certificacion/v2/dte/", json=data, headers=headers)
                    logging.warn(r.json())
                    certificacion_json = r.json()
                    if certificacion_json["resultado"]:
                        factura.firma_fel = certificacion_json["uuid"]
                        factura.name = str(certificacion_json["serie"])+"-"+str(certificacion_json["numero"])
                        factura.serie_fel = certificacion_json["serie"]
                        factura.numero_fel = certificacion_json["numero"]
                        factura.pdf_fel = "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="+certificacion_json["uuid"]
                    else:
                        raise UserError(str(certificacion_json["descripcion_errores"]))
                else:
                    raise UserError(r.text)

        return super(AccountInvoice, self).invoice_validate()

    @api.multi
    def action_cancel(self):
        result = super(AccountInvoice, self).action_cancel()
        if result:
            for factura in self:
                dte = factura.dte_documento()
                if dte:
                    xmls = etree.tostring(dte, encoding="UTF-8")
                    xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                    xmls_base64 = base64.b64encode(xmls)
                    logging.warn(xmls)

                    headers = { "Content-Type": "application/json" }
                    data = {
                        "llave": factura.journal_id.token_firma_fel,
                        "archivo": xmls_base64.decode("utf-8"),
                        "codigo": factura.company_id.vat.replace('-',''),
                        "alias": factura.journal_id.usuario_fel,
                    }
                    r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                    logging.warn(r.text)
                    firma_json = r.json()
                    if firma_json["resultado"]:

                        headers = {
                            "USUARIO": factura.journal_id.usuario_fel,
                            "LLAVE": factura.journal_id.clave_fel,
                            "IDENTIFICADOR": factura.journal_id.code+str(factura.id),
                            "Content-Type": "application/json",
                        }
                        data = {
                            "nit_emisor": factura.company_id.vat.replace('-',''),
                            "correo_copia": factura.company_id.email,
                            "xml_dte": firma_json["archivo"]
                        }
                        r = requests.post("https://certificador.feel.com.gt/fel/anulacion/v2/dte/", json=data, headers=headers)
                        logging.warn(r.text)
                        certificacion_json = r.json()
                        if not certificacion_json["resultado"]:
                            raise UserError(str(certificacion_json["descripcion_errores"]))
                    else:
                        raise UserError(r.text)

    @api.multi
    def action_invoice_draft(self):
        for factura in self:
            if factura.journal_id.usuario_fel and factura.firma_fel:
                raise UserError("La factura ya fue enviada, por lo que ya no puede ser modificada")
            else:
                return super(AccountInvoice, self).action_invoice_draft()

class AccountJournal(models.Model):
    _inherit = "account.journal"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    token_firma_fel = fields.Char('Token Firma FEL', copy=False)