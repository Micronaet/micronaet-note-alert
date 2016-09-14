# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class NoteDepartment(orm.Model):
    """ Model name: NoteType
    """    
    _name = 'note.department'
    _description = 'Note department'
    
    _columns = {
        'name': fields.char('Department', size=64, required=True),
        'note': fields.text('Note') ,
        }

class NoteType(orm.Model):
    """ Model name: NoteType
    """    
    _name = 'note.type'
    _description = 'Note type'
    
    _columns = {
        'name': fields.char(
            'Name', size=64, required=True),
        'note': fields.text('Note'),
        'department_ids': fields.many2many(
            'note.department', 'type_department_note_rel', 
            'type_id', 'department_id', 
            'Department'), 
        }

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _name = 'note.note'
    _description = 'Note'
    
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'description': fields.text('Description'),
        'overridable': fields.boolean('Overridable'),
        'type_id': fields.many2one('note.type', 'Type'), 
        'product_id': fields.many2one('product.product', 'Product'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'order_id': fields.many2one('sale.order', 'Order'),
        }

class NoteProductReport(orm.Model):
    """ Model name: NoteProductReport
    """    
    _name = 'note.product.report'
    _description = 'Note product report'

    _columns = {
        'name': fields.char('Report name', size=64, required=True),
        'note': fields.text('Note') ,
        }
    
class NoteProductReportLine(orm.Model):
    """ Model name: NoteProductReportLine
    """    
    _name = 'note.product.report.line'
    _description = 'Note product report'
    
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'sequence': fields.integer('Sequence')), 
        'report_id': fields.many2one('note.product.report', 'Report'),
        'type_id': fields.many2one('note.type', 'Type'),        
        }

class NoteProductReport(orm.Model):
    """ Model name: NoteProductReport
    """    
    _inherit = 'note.product.report'
    
    _columns = {
        'line_ids': fields.one2many(
            'note.product.report.line', 'report_id', 'Detail'), 
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
