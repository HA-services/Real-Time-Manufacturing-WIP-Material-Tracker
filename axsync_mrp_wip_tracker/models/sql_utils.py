# -*- coding: utf-8 -*-
# Part of AXSync. See LICENSE file for full copyright and licensing details.

# In Odoo 18 the company-dependent standard cost is a JSONB column on product_product
# keyed by company id. A missing value is treated as zero.
COST_SQL = """
    COALESCE(
        (SELECT (pc.standard_price ->> ({cid})::text)::float
           FROM product_product pc WHERE pc.id = {pid}),
        0.0)
"""


def cost_sql(pid, cid):
    return COST_SQL.format(pid=pid, cid=cid)
