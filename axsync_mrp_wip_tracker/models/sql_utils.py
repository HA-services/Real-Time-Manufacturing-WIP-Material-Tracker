# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.

# Standard cost is a company-dependent field stored in ir_property in Odoo 17.
# Resolution order: company specific value, then the global default, then 0.
COST_SQL = """
    COALESCE(
        (SELECT p.value_float FROM ir_property p
          WHERE p.name = 'standard_price' AND p.res_id = 'product.product,' || {pid}
            AND p.company_id = {cid} LIMIT 1),
        (SELECT p.value_float FROM ir_property p
          WHERE p.name = 'standard_price' AND p.res_id = 'product.product,' || {pid}
            AND p.company_id IS NULL LIMIT 1),
        (SELECT p.value_float FROM ir_property p
          WHERE p.name = 'standard_price' AND p.res_id IS NULL
            AND p.company_id = {cid} LIMIT 1),
        0.0)
"""


def cost_sql(pid, cid):
    return COST_SQL.format(pid=pid, cid=cid)
