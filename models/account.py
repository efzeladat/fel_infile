    # -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

from datetime import datetime
import base64
from lxml import etree
from signxml import XMLSigner
import requests

import logging

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    uuid_fel = fields.Char('Firma FEL', copy=False)
    pdf_fel = fields.Char('PDF FEL', copy=False)

    def invoice_validate(self):
        detalles = []
        subtotal = 0
        for factura in self:
            if factura.journal_id.usuario_fel and not factura.uuid_fel:
                attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")

                NSMAP = {
                    "ds": "http://www.w3.org/2000/09/xmldsig#",
                    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "dte": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "n1": "http://www.altova.com/samplexml/other-namespace",
                }

                DTE_NS = "{http://www.sat.gob.gt/dte/fel/0.1.0}"
                DS_NS = "{http://www.w3.org/2000/09/xmldsig#}"

                GTDocumento = etree.Element(DTE_NS+"GTDocumento", {attr_qname: "http://www.sat.gob.gt/dte/fel/0.1.0"}, Version="0.4", nsmap=NSMAP)
                SAT = etree.SubElement(GTDocumento, DTE_NS+"SAT", ClaseDocumento="dte")
                DTE = etree.SubElement(SAT, DTE_NS+"DTE", ID="DatosCertificados")
                DatosEmision = etree.SubElement(DTE, DTE_NS+"DatosEmision", ID="DatosEmision")

                DatosGenerales = etree.SubElement(DatosEmision, DTE_NS+"DatosGenerales", CodigoMoneda="GTQ", FechaHoraEmision=factura.date_invoice+"T00:30:00", NumeroAcceso=str(100000000+factura.id), Tipo=factura.journal_id.tipo_documento_fel)

                Emisor = etree.SubElement(DatosEmision, DTE_NS+"Emisor", AfiliacionIVA="GEN", CodigoEstablecimiento=factura.journal_id.codigo_establecimiento_fel, CorreoEmisor="", NITEmisor=factura.company_id.vat, NombreComercial=factura.company_id.name, NombreEmisor=factura.company_id.name)
                DireccionEmisor = etree.SubElement(Emisor, DTE_NS+"DireccionEmisor")
                Direccion = etree.SubElement(DireccionEmisor, DTE_NS+"Direccion")
                Direccion.text = factura.company_id.street or ''
                CodigoPostal = etree.SubElement(DireccionEmisor, DTE_NS+"CodigoPostal")
                CodigoPostal.text = factura.company_id.zip or ''
                Municipio = etree.SubElement(DireccionEmisor, DTE_NS+"Municipio")
                Municipio.text = factura.company_id.city or ''
                Departamento = etree.SubElement(DireccionEmisor, DTE_NS+"Departamento")
                Departamento.text = factura.company_id.state_id.name if factura.company_id.state_id else ''
                Pais = etree.SubElement(DireccionEmisor, DTE_NS+"Pais")
                Pais.text = factura.company_id.country_id.code or 'GT'

                Receptor = etree.SubElement(DatosEmision, DTE_NS+"Receptor", CorreoReceptor=factura.partner_id.email, IDReceptor=factura.partner_id.vat, NombreReceptor=factura.partner_id.name)
                DireccionReceptor = etree.SubElement(Receptor, DTE_NS+"DireccionReceptor")
                Direccion = etree.SubElement(DireccionReceptor, DTE_NS+"Direccion")
                Direccion.text = factura.partner_id.street or ''
                CodigoPostal = etree.SubElement(DireccionReceptor, DTE_NS+"CodigoPostal")
                CodigoPostal.text = factura.partner_id.zip or '01001'
                Municipio = etree.SubElement(DireccionReceptor, DTE_NS+"Municipio")
                Municipio.text = factura.partner_id.city or ''
                Departamento = etree.SubElement(DireccionReceptor, DTE_NS+"Departamento")
                Departamento.text = factura.partner_id.state_id.name if factura.partner_id.state_id else ''
                Pais = etree.SubElement(DireccionReceptor, DTE_NS+"Pais")
                Pais.text = factura.partner_id.country_id.code or 'GT'

                Frases = etree.SubElement(DatosEmision, DTE_NS+"Frases")
                ElementFrases = etree.fromstring(factura.company_id.frases_fel)
                Frases.append(ElementFrases)
                #Frase = etree.SubElement(Frases, DTE_NS+"Frase", CodigoEscenario="1", TipoFrase="1")

                Items = etree.SubElement(DatosEmision, DTE_NS+"Items")

                linea_num = 0
                gran_subtotal = 0
                gran_total = 0
                gran_total_impuestos = 0
                for linea in factura.invoice_line_ids:

                    linea_num += 1

                    tipo_producto = "B"
                    if linea.product_id.type != 'product':
                        tipo_producto = "S"
                    precio_unitario = linea.price_unit * (100-linea.discount) / 100
                    precio_unitario_base = linea.price_subtotal / linea.quantity
                    total_linea = precio_unitario * linea.quantity
                    total_linea_base = precio_unitario_base * linea.quantity
                    total_impuestos = total_linea - total_linea_base

                    Item = etree.SubElement(Items, DTE_NS+"Item", BienOServicio=tipo_producto, NumeroLinea=str(linea_num))
                    Cantidad = etree.SubElement(Item, DTE_NS+"Cantidad")
                    Cantidad.text = str(linea.quantity)
                    UnidadMedida = etree.SubElement(Item, DTE_NS+"UnidadMedida")
                    UnidadMedida.text = "UNI"
                    Descripcion = etree.SubElement(Item, DTE_NS+"Descripcion")
                    Descripcion.text = linea.name
                    PrecioUnitario = etree.SubElement(Item, DTE_NS+"PrecioUnitario")
                    PrecioUnitario.text = str(precio_unitario)
                    Precio = etree.SubElement(Item, DTE_NS+"Precio")
                    Precio.text = str(total_linea)
                    Descuento = etree.SubElement(Item, DTE_NS+"Descuento")
                    Descuento.text = str(0)
                    Impuestos = etree.SubElement(Item, DTE_NS+"Impuestos")
                    Impuesto = etree.SubElement(Impuestos, DTE_NS+"Impuesto")
                    NombreCorto = etree.SubElement(Impuesto, DTE_NS+"NombreCorto")
                    NombreCorto.text = "IVA"
                    CodigoUnidadGravable = etree.SubElement(Impuesto, DTE_NS+"CodigoUnidadGravable")
                    CodigoUnidadGravable.text = "1"
                    MontoGravable = etree.SubElement(Impuesto, DTE_NS+"MontoGravable")
                    MontoGravable.text = str(float_round(total_linea_base, precision_digits=2))
                    MontoImpuesto = etree.SubElement(Impuesto, DTE_NS+"MontoImpuesto")
                    MontoImpuesto.text = str(float_round(total_impuestos, precision_digits=2))
                    Total = etree.SubElement(Item, DTE_NS+"Total")
                    Total.text = str(float_round(total_linea, precision_digits=2))

                    gran_total += float_round(total_linea, precision_digits=2)
                    gran_subtotal += float_round(total_linea_base, precision_digits=2)
                    gran_total_impuestos += float_round(total_impuestos, precision_digits=2)

                Totales = etree.SubElement(DatosEmision, DTE_NS+"Totales")
                TotalImpuestos = etree.SubElement(Totales, DTE_NS+"TotalImpuestos")
                TotalImpuesto = etree.SubElement(TotalImpuestos, DTE_NS+"TotalImpuesto", NombreCorto="IVA", TotalMontoImpuesto=str(gran_total_impuestos))
                GranTotal = etree.SubElement(Totales, DTE_NS+"GranTotal")
                GranTotal.text = str(gran_total)

                # Adenda = etree.SubElement(DTE, DTE_NS+"Adenda")

                xmls = etree.tostring(GTDocumento)
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls)

                # cert = open("/home/odoo/100056865-cert.pem").read().encode('ascii')
                # key = open("/home/odoo/100056865.key").read().encode('ascii')
                #
                # signer = XMLSigner(c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315#WithComments')
                # signed_root = signer.sign(GTDocumento, key=key, cert=cert)
                #
                # signed_text = etree.tostring(signed_root, xml_declaration=True, encoding="UTF-8")
                # logging.warn(signed_text)
                #
                # signed_text_b64 = base64.b64encode(signed_text)
                # logging.warn(signed_text_b64)

                headers = { "Content-Type": "application/json" }
                data = {
                    "llave": factura.journal_id.token_firma_fel,
                    "archivo": xmls_base64,
                    "codigo": factura.company_id.vat,
                    "alias": factura.journal_id.usuario_fel,
                    "es_anulacion": "N"
                }
                r = requests.post('https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml', json=data, headers=headers)
                firma_json = r.json()
                if firma_json["resultado"]:
                    logging.warn(base64.b64decode(firma_json["archivo"]))

                    headers = {
                        "USUARIO": factura.journal_id.usuario_fel,
                        "LLAVE": factura.journal_id.clave_fel,
                        "IDENTIFICADOR": 100000000+factura.id,
                        "Content-Type": "application/json",
                    }
                    data = {
                        "nit_emisor": factura.company_id.vat,
                        "correo_copia": factura.company_id.email,
                        "xml_dte": firma_json["archivo"]
                    }
                    r = requests.post("https://certificador.feel.com.gt/fel/certificacion/dte/", json=data, headers=headers)
                    logging.warn(r.json())
                    certificacion_json = r.json()
                    if certificacion_json["resultado"]:
                        factura.uuid_fel = certificacion_json["uuid"]
                        factura.name = certificacion_json["serie"]+"-"+certificacion_json["numero"]
                        factura.pdf_fel =" https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="+certificacion_json["uuid"]

                        # return super(AccountInvoice,self).invoice_validate()

class AccountJournal(models.Model):
    _inherit = "account.journal"

    usuario_fel = fields.Char('Usuario FEL', copy=False)
    clave_fel = fields.Char('Clave FEL', copy=False)
    token_firma_fel = fields.Char('Token Firma FEL', copy=False)
    codigo_establecimiento_fel = fields.Char('Codigo Establecimiento FEL', copy=False)
    tipo_documento_fel = fields.Selection([('FACT', 'FACT'), ('FCAM', 'FCAM'), ('FPEQ', 'FPEQ'), ('FCAP', 'FCAP'), ('FESP', 'FESP'), ('NABN', 'NABN'), ('RDON', 'RDON'), ('RECI', 'RECI'), ('NDEB', 'NDEB'), ('NCRE', 'NCRE')], 'Tipo de Documento FEL', copy=False)

class ResCompany(models.Model):
    _inherit = "res.company"

    frases_fel = fields.Text('Frases FEL')
