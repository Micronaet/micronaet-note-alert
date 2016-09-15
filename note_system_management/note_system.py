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
import base64
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
    """ Model name: NoteDepartment
    """    
    _name = 'note.department'
    _description = 'Note department'
    
    _columns = {
        'name': fields.char('Department', size=64, required=True),
        'note': fields.text('Note'),
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
        'linked_image': fields.boolean('Linked image', 
            help='If checked use image from linked module, else store file'),
        'linked_object': fields.selection([
            ('product_id', 'Product'),
            ('partner_id', 'Partner'),
            ], 'Linked object', 
            help='For show image linked to object'),
        'linked_image_field': fields.char('Image field name', size=64, 
            help='Image field name of linked object'),            
        }

    _defaults = {
        'linked_object': lambda *x: 'product_id',
        }

class NoteImage(orm.Model):
    """ Model name: NoteImage
    """    
    # TODO
    _name = 'note.image'
    _description = 'Note image'
    
    _columns = {
        'name': fields.char('Image', size=64, required=True),
        'note': fields.text('Note'),
        'type_id': fields.many2one('note.type', 'Type'),
        }        

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _name = 'note.note'
    _description = 'Note'
    
    # -------------------------------------------------------------------------
    # Functional field:
    # -------------------------------------------------------------------------
    def _get_note_image(self, cr, uid, ids, field, args, context=None):
        ''' Use base folder for get ID.png filename from filesystem
        '''
        extension = 'png'

        note_folder = os.path.expanduser(
            self.pool.get('res.company').get_base_local_folder(
                cr, uid, subfolder='note_image', context=context))

        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            note_type = product.type_id
            linked_image = note_type.linked_image
            if linked_image:
                res[product.id] = product.__getattribute__(
                    note_type.linked_object).__getattribute__(
                    note_type.linked_image_field)
            else: # stored file
                filename = os.path.join(
                    note_folder, '%s.%s' % (product.id, extension))
                try:
                    f = open(filename , 'rb')
                    res[product.id] = base64.encodestring(f.read())
                    f.close()
                except:
                    res[product.id] = ''
        return res
    
    _columns = {        
        'name': fields.char('Title', size=64, required=True),
        'type_id': fields.many2one('note.type', 'Type', required=True), 
        'datetime': fields.date('Date'),
        'description': fields.text('Description'),
        'overridable': fields.boolean('Overridable'),
        
        # Image block:
        'image': fields.function(_get_note_image, type='binary', method=True),
        
        # Linked object for part.
        'product_id': fields.many2one('product.product', 'Product'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        }
        
    _default = {
        
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
    _order = 'sequence,id'
    
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'sequence': fields.integer('Sequence'), 
        'report_id': fields.many2one('note.product.report', 'Report'),
        'type_id': fields.many2one('note.type', 'Type', required=True),        
        }

class NoteProductReport(orm.Model):
    """ Model name: NoteProductReport
    """    
    _inherit = 'note.product.report'
    
    _columns = {
        'line_ids': fields.one2many(
            'note.product.report.line', 'report_id', 'Detail'), 
        }
    
class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """    
    _inherit = 'product.product'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'product_id', 'Note system'), 
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'partner_id', 'Note system'), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
