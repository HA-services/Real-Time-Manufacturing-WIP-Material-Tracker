# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import api, fields, models

from .wip_component import component_query
from .wip_scrap import scrap_query

OPEN_STATES = ("confirmed", "progress", "to_close")



class AxsyncWipProduction(models.Model):
    """One row per Manufacturing Order. Read-only SQL view; nothing is stored."""
    _name = 'axsync.wip.production'
    _description = 'AXSync WIP - Manufacturing Order Analysis'
    _auto = False
    _order = 'date_deadline asc, id desc'
    _rec_name = 'production_id'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('progress', 'In Progress'),
        ('to_close', 'To Close'), ('done', 'Done'), ('cancel', 'Cancelled')],
        string='State', readonly=True)
    reservation_state = fields.Selection([
        ('confirmed', 'Waiting'), ('assigned', 'Ready'), ('waiting', 'Waiting Another Operation')],
        string='Material Readiness', readonly=True)
    date_start = fields.Datetime('Start', readonly=True)
    date_deadline = fields.Datetime('Deadline', readonly=True)
    date_finished = fields.Datetime('End', readonly=True)
    product_qty = fields.Float('Quantity to Produce', readonly=True)
    produced_qty = fields.Float('Quantity Produced', readonly=True,
                                help="Quantity of the finished product in finished stock moves.")
    progress = fields.Float('Progress (%)', readonly=True, group_operator='avg',
                            help="Produced quantity divided by quantity to produce, capped at 100.")
    component_count = fields.Integer('Components', readonly=True)
    shortage_count = fields.Integer('Components Short', readonly=True)
    has_shortage = fields.Boolean('Has Shortage', readonly=True)
    planned_value = fields.Monetary('Planned Material Value', readonly=True,
                                    help="Demanded component quantity valued at standard cost.")
    consumed_value = fields.Monetary('Consumed Material Value', readonly=True,
                                     help="Component quantity consumed (picked or done) valued at standard cost.")
    wip_value = fields.Monetary('WIP Material Value', readonly=True,
                                help="Consumed material value of orders that are not yet done. "
                                     "Operational estimate at standard cost, not an accounting valuation.")
    variance_value = fields.Monetary('Material Variance Value', readonly=True,
                                     help="Consumed minus planned value on finished component moves.")
    scrap_count = fields.Integer('Scrap Records', readonly=True)
    scrap_value = fields.Monetary('Scrap Value', readonly=True)
    workorder_count = fields.Integer('Work Orders', readonly=True)
    workorder_done_count = fields.Integer('Work Orders Done', readonly=True)
    is_open = fields.Boolean('Open', readonly=True)
    is_delayed = fields.Boolean('Delayed', readonly=True,
                                help="Deadline has passed and the order is not done or cancelled.")

    def _select_extra(self):
        return ''

    def _join_extra(self):
        return ''

    def init(self):
        self.env.cr.execute('DROP VIEW IF EXISTS %s CASCADE' % self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT mo.id AS id,
                       mo.id AS production_id,
                       mo.product_id,
                       mo.company_id,
                       mo.user_id,
                       mo.state,
                       mo.reservation_state,
                       mo.date_start,
                       mo.date_deadline,
                       mo.date_finished,
                       mo.product_qty,
                       COALESCE(fin.qty, 0.0) AS produced_qty,
                       CASE WHEN mo.product_qty > 0
                            THEN LEAST(COALESCE(fin.qty, 0.0) / mo.product_qty, 1.0) * 100.0
                            ELSE 0.0 END AS progress,
                       COALESCE(comp.component_count, 0) AS component_count,
                       COALESCE(comp.shortage_count, 0) AS shortage_count,
                       COALESCE(comp.shortage_count, 0) > 0 AS has_shortage,
                       COALESCE(comp.planned_value, 0.0) AS planned_value,
                       COALESCE(comp.consumed_value, 0.0) AS consumed_value,
                       CASE WHEN mo.state IN ('confirmed','progress','to_close')
                            THEN COALESCE(comp.consumed_value, 0.0) ELSE 0.0 END AS wip_value,
                       COALESCE(comp.variance_value, 0.0) AS variance_value,
                       COALESCE(scr.scrap_count, 0) AS scrap_count,
                       COALESCE(scr.scrap_value, 0.0) AS scrap_value,
                       COALESCE(wo.wo_count, 0) AS workorder_count,
                       COALESCE(wo.wo_done, 0) AS workorder_done_count,
                       mo.state IN ('confirmed','progress','to_close') AS is_open,
                       (mo.state IN ('confirmed','progress','to_close')
                        AND mo.date_deadline IS NOT NULL
                        AND mo.date_deadline < (NOW() AT TIME ZONE 'UTC')) AS is_delayed
                       %s
                  FROM mrp_production mo
                  LEFT JOIN (
                        SELECT sm.production_id, SUM(sm.quantity) AS qty
                          FROM stock_move sm
                         WHERE sm.production_id IS NOT NULL AND sm.state = 'done'
                         GROUP BY sm.production_id
                  ) fin ON fin.production_id = mo.id
                  LEFT JOIN (
                        SELECT c.production_id,
                               COUNT(*) AS component_count,
                               COUNT(*) FILTER (WHERE c.shortage_qty > 0) AS shortage_count,
                               SUM(c.planned_qty * c.cost) AS planned_value,
                               SUM(c.consumed_qty * c.cost) AS consumed_value,
                               SUM(c.variance_qty * c.cost) AS variance_value
                          FROM (%s) c
                         GROUP BY c.production_id
                  ) comp ON comp.production_id = mo.id
                  LEFT JOIN (
                        SELECT s.production_id, COUNT(*) AS scrap_count, SUM(s.scrap_value) AS scrap_value
                          FROM (%s) s
                         GROUP BY s.production_id
                  ) scr ON scr.production_id = mo.id
                  LEFT JOIN (
                        SELECT w.production_id, COUNT(*) AS wo_count,
                               COUNT(*) FILTER (WHERE w.state = 'done') AS wo_done
                          FROM mrp_workorder w GROUP BY w.production_id
                  ) wo ON wo.production_id = mo.id
                  %s
            )
        """ % (self._table, self._select_extra(), component_query(), scrap_query(), self._join_extra()))

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @api.model
    def _dashboard_tiles(self, days):
        """Return the KPI tiles. Each tile carries the model and domain used to drill down."""
        since = fields.Datetime.now() - timedelta(days=days) if days else False
        prod = 'axsync.wip.production'
        open_dom = [('is_open', '=', True)]
        tiles = [
            {'key': 'open', 'label': 'Open manufacturing orders', 'model': prod,
             'domain': open_dom, 'value': self.search_count(open_dom), 'tone': 'primary'},
            {'key': 'progress', 'label': 'In progress', 'model': prod,
             'domain': [('state', '=', 'progress')],
             'value': self.search_count([('state', '=', 'progress')]), 'tone': 'info'},
            {'key': 'delayed', 'label': 'Delayed orders', 'model': prod,
             'domain': [('is_delayed', '=', True)],
             'value': self.search_count([('is_delayed', '=', True)]), 'tone': 'danger'},
            {'key': 'shortage', 'label': 'Orders with material shortage', 'model': prod,
             'domain': open_dom + [('has_shortage', '=', True)],
             'value': self.search_count(open_dom + [('has_shortage', '=', True)]), 'tone': 'warning'},
        ]
        wip = self.read_group(open_dom, ['wip_value:sum'], [])
        tiles.append({'key': 'wip', 'label': 'WIP material value', 'model': prod,
                      'domain': open_dom, 'value': wip[0]['wip_value'] if wip else 0.0,
                      'monetary': True, 'tone': 'success'})
        scrap_dom = [('scrap_date', '>=', since)] if since else []
        scrap = self.env['axsync.wip.scrap'].read_group(scrap_dom, ['scrap_value:sum'], [])
        tiles.append({'key': 'scrap', 'label': 'Scrap value in period', 'model': 'axsync.wip.scrap',
                      'domain': scrap_dom, 'value': scrap[0]['scrap_value'] if scrap else 0.0,
                      'monetary': True, 'tone': 'secondary'})
        return tiles

    @api.model
    def get_dashboard_data(self, days=30):
        days = int(days or 0)
        tiles = self._dashboard_tiles(days)
        delayed = self.search([('is_delayed', '=', True)], order='date_deadline asc', limit=8)
        short = self.env['axsync.wip.component'].search(
            [('shortage_qty', '>', 0), ('is_open', '=', True)], order='shortage_value desc', limit=8)
        company = self.env.company
        return {
            'tiles': tiles,
            'days': days,
            'currency': {'symbol': company.currency_id.symbol,
                         'position': company.currency_id.position},
            'delayed': [{'id': r.production_id.id, 'name': r.production_id.name,
                         'product': r.product_id.display_name,
                         'deadline': fields.Datetime.to_string(r.date_deadline) if r.date_deadline else '',
                         'progress': round(r.progress, 1)} for r in delayed],
            'shortages': [{'id': r.production_id.id, 'name': r.production_id.name,
                           'product': r.product_id.display_name,
                           'short': round(r.shortage_qty, 3),
                           'uom': r.product_uom_id.name} for r in short],
        }
