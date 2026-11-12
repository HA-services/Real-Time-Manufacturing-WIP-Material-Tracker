# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from .sql_utils import cost_sql


def scrap_query():
    return """
                SELECT x.*, x.cost AS unit_cost, x.scrap_qty * x.cost AS scrap_value
                  FROM (
                    SELECT s.id AS id,
                           s.id AS scrap_id,
                           s.production_id,
                           s.workorder_id,
                           mo.product_id AS finished_product_id,
                           s.product_id,
                           pt.uom_id AS product_uom_id,
                           s.company_id,
                           s.date_done AS scrap_date,
                           s.scrap_qty / NULLIF(su.factor, 0) * pu.factor AS scrap_qty,
                           %(cost)s AS cost
                      FROM stock_scrap s
                      JOIN mrp_production mo ON mo.id = s.production_id
                      JOIN product_product pp ON pp.id = s.product_id
                      JOIN product_template pt ON pt.id = pp.product_tmpl_id
                      JOIN uom_uom su ON su.id = s.product_uom_id
                      JOIN uom_uom pu ON pu.id = pt.uom_id
                     WHERE s.state = 'done'
                  ) x
    """ % {'cost': cost_sql('s.product_id', 's.company_id')}


class AxsyncWipScrap(models.Model):
    """One row per validated scrap record linked to a Manufacturing Order."""
    _name = 'axsync.wip.scrap'
    _description = 'AXSync WIP - Scrap Analysis'
    _auto = False
    _order = 'scrap_date desc, id desc'
    _rec_name = 'product_id'

    scrap_id = fields.Many2one('stock.scrap', string='Scrap', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', readonly=True)
    finished_product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    product_id = fields.Many2one('product.product', string='Scrapped Product', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    scrap_date = fields.Datetime('Scrap Date', readonly=True)
    scrap_qty = fields.Float('Scrapped Quantity', readonly=True, digits='Product Unit of Measure',
                             help="Quantity in the product's own unit.")
    unit_cost = fields.Float('Standard Cost', readonly=True, digits='Product Price')
    scrap_value = fields.Monetary('Scrap Value', readonly=True)

    def init(self):
        self.env.cr.execute('DROP VIEW IF EXISTS %s CASCADE' % self._table)
        self.env.cr.execute('CREATE OR REPLACE VIEW %s AS (%s)' % (self._table, scrap_query()))
