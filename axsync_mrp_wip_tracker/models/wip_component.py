# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from .sql_utils import cost_sql


def component_query():
    return """
                SELECT x.*,
                       x.planned_qty * x.cost AS planned_value,
                       x.consumed_qty * x.cost AS consumed_value,
                       x.shortage_qty * x.cost AS shortage_value,
                       x.variance_qty * x.cost AS variance_value,
                       x.cost AS unit_cost,
                       x.shortage_qty > 0 AS has_shortage,
                       x.variance_qty > 0 AS is_over_consumed
                  FROM (
                    SELECT sm.id AS id,
                           sm.id AS move_id,
                           sm.raw_material_production_id AS production_id,
                           mo.product_id AS finished_product_id,
                           sm.product_id,
                           pt.uom_id AS product_uom_id,
                           sm.company_id,
                           mo.state AS mo_state,
                           sm.state AS move_state,
                           mo.date_deadline,
                           mo.state IN ('confirmed','progress','to_close') AS is_open,
                           sm.product_qty AS planned_qty,
                           CASE WHEN sm.state = 'done' OR sm.picked THEN 0.0
                                ELSE sm.quantity * sm.product_qty / NULLIF(sm.product_uom_qty, 0) END AS reserved_qty,
                           CASE WHEN sm.state = 'done' OR sm.picked
                                THEN sm.quantity * sm.product_qty / NULLIF(sm.product_uom_qty, 0)
                                ELSE 0.0 END AS consumed_qty,
                           CASE WHEN mo.state IN ('confirmed','progress','to_close')
                                     AND sm.state NOT IN ('done','cancel','draft')
                                THEN GREATEST(sm.product_qty
                                              - COALESCE(sm.quantity * sm.product_qty / NULLIF(sm.product_uom_qty, 0), 0.0),
                                              0.0)
                                ELSE 0.0 END AS shortage_qty,
                           CASE WHEN sm.state = 'done'
                                THEN COALESCE(sm.quantity * sm.product_qty / NULLIF(sm.product_uom_qty, 0), 0.0)
                                     - sm.product_qty
                                ELSE 0.0 END AS variance_qty,
                           %(cost)s AS cost
                      FROM stock_move sm
                      JOIN mrp_production mo ON mo.id = sm.raw_material_production_id
                      JOIN product_product pp ON pp.id = sm.product_id
                      JOIN product_template pt ON pt.id = pp.product_tmpl_id
                     WHERE sm.state <> 'cancel'
                       AND COALESCE(sm.scrapped, FALSE) = FALSE
                  ) x
    """ % {'cost': cost_sql('sm.product_id', 'sm.company_id')}


class AxsyncWipComponent(models.Model):
    """One row per raw material (component) stock move of a Manufacturing Order."""
    _name = 'axsync.wip.component'
    _description = 'AXSync WIP - Component Consumption and Variance'
    _auto = False
    _order = 'production_id desc, id'
    _rec_name = 'product_id'

    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    finished_product_id = fields.Many2one('product.product', string='Finished Product', readonly=True)
    product_id = fields.Many2one('product.product', string='Component', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True,
                                     help="All quantities on this report are expressed in the product's own unit.")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    mo_state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('progress', 'In Progress'),
        ('to_close', 'To Close'), ('done', 'Done'), ('cancel', 'Cancelled')],
        string='MO State', readonly=True)
    move_state = fields.Selection([
        ('draft', 'New'), ('waiting', 'Waiting Another Move'), ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'), ('assigned', 'Available'),
        ('done', 'Done'), ('cancel', 'Cancelled')], string='Move State', readonly=True)
    date_deadline = fields.Datetime('MO Deadline', readonly=True)
    is_open = fields.Boolean('Open MO', readonly=True)
    planned_qty = fields.Float('Planned', readonly=True, digits='Product Unit of Measure')
    reserved_qty = fields.Float('Reserved', readonly=True, digits='Product Unit of Measure',
                                help="Quantity reserved but not yet picked or consumed.")
    consumed_qty = fields.Float('Consumed', readonly=True, digits='Product Unit of Measure',
                                help="Quantity picked or done on the component move.")
    shortage_qty = fields.Float('Shortage', readonly=True, digits='Product Unit of Measure',
                                help="Planned quantity not yet reserved or consumed, on orders that are open.")
    variance_qty = fields.Float('Variance', readonly=True, digits='Product Unit of Measure',
                                help="Consumed minus planned quantity, on component moves that are done.")
    unit_cost = fields.Float('Standard Cost', readonly=True, digits='Product Price')
    planned_value = fields.Monetary('Planned Value', readonly=True)
    consumed_value = fields.Monetary('Consumed Value', readonly=True)
    shortage_value = fields.Monetary('Shortage Value', readonly=True)
    variance_value = fields.Monetary('Variance Value', readonly=True)
    has_shortage = fields.Boolean('Has Shortage', readonly=True)
    is_over_consumed = fields.Boolean('Over-consumed', readonly=True)

    def init(self):
        self.env.cr.execute('DROP VIEW IF EXISTS %s CASCADE' % self._table)
        self.env.cr.execute('CREATE OR REPLACE VIEW %s AS (%s)' % (self._table, component_query()))
