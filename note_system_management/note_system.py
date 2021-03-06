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
    _order = 'sequence,name'
    
    _columns = {
        'sequence': fields.integer('Sequence'),
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

    # Parameters:
    _extension = 'png'
    _root_path = 'note_image_default'
    
    # -------------------------------------------------------------------------
    # Functional field:
    # -------------------------------------------------------------------------
    def _set_note_default_image(self, cr, uid, item_id, name, value, fnct_inv_arg=None, 
            context=None):
        ''' Write image as stored file when insert
        '''
        company_pool = self.pool.get('res.company')
        image_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        filename = os.path.join(
            image_folder, '%s.%s' % (item_id, self._extension))

        image_file = open(filename, 'wb')
        if value:
            image_file.write(base64.decodestring(value))
        image_file.close()        
        return True
    
    def _get_note_default_image(self, cr, uid, ids, field, args, context=None):
        ''' Use base folder for get ID.png filename from filesystem
        '''
        company_pool = self.pool.get('res.company')        
        image_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        res = {}
        for image in self.browse(cr, uid, ids, context=context):
            filename = os.path.join(
                image_folder, '%s.%s' % (image.id, self._extension))
            try:
                f = open(filename , 'rb')
                res[image.id] = base64.encodestring(f.read())
                f.close()
            except:
                res[image.id] = ''
        return res

    _columns = {
        'name': fields.char('Image', size=64, required=True),
        'note': fields.text('Note'),
        'type_id': fields.many2one('note.type', 'Type'),
        'image': fields.function(_get_note_default_image, 
            fnct_inv=_set_note_default_image, string='Image',
            type='binary', method=True),
        }       

class NoteNote(orm.Model):
    """ Model name: NoteNote
    """    
    _name = 'note.note'
    _description = 'Note'
    _order = 'date' # change for pack parent?
    
    # Parameters:
    _extension = 'png'
    _root_path = 'note_image'
    
    # -------------------------------------------------------------------------
    # Functional field:
    # -------------------------------------------------------------------------
    def _set_note_image(self, cr, uid, item_id, name, value, fnct_inv_arg=None, 
            context=None):
        ''' Write image as stored file when insert
        '''
        company_pool = self.pool.get('res.company')
        note_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        filename = os.path.join(
            note_folder, '%s.%s' % (item_id, self._extension))
        image_file = open(filename, 'wb')
        if value:
            image_file.write(base64.decodestring(value))
        image_file.close()        
        return True
    
    def _get_note_image(self, cr, uid, ids, field, args, context=None):
        ''' Use base folder for get ID.png filename from filesystem
        '''
        company_pool = self.pool.get('res.company')        
        note_folder = os.path.expanduser(company_pool.get_base_local_folder(
            cr, uid, subfolder=self._root_path, context=context))

        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            note_type = note.type_id
            linked_image = note_type.linked_image
            if note.image_id: # Static image
                res[note.id] = note.image_id.image                
            elif linked_image: # Linked category image
                res[note.id] = note.__getattribute__(
                    note_type.linked_object).__getattribute__(
                    note_type.linked_image_field)
            else: # Stored note file
                filename = os.path.join(
                    note_folder, '%s.%s' % (note.id, self._extension))
                try:
                    f = open(filename , 'rb')
                    res[note.id] = base64.encodestring(f.read())
                    f.close()
                except:
                    res[note.id] = ''
        return res

    _columns = {        
        'name': fields.char('Title', size=64, required=True),
        'type_id': fields.many2one('note.type', 'Type', required=True), 
        'create_uid': fields.many2one(
            'res.users', 'Created By', readonly=True),
        'date': fields.datetime('Date', required=True),
        'deadline': fields.date('Deadline date'),
        'description': fields.text('Description'),
        'overridable': fields.boolean('Overridable'),
        
        # Image block:
        'image': fields.function(_get_note_image, fnct_inv=_set_note_image, 
            type='binary', method=True, string='Image'),
        'image_id': fields.many2one('note.image', 'Static image'), 
        
        # Linked object for part.
        'product_id': fields.many2one('product.product', 'Product'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'address_id': fields.many2one('res.partner', 'Partner address'), 
        #    domain=[('is_address', '=', True)]),
        'order_id': fields.many2one('sale.order', 'Order'),
        'line_id': fields.many2one('sale.order.line', 'Order line'),
        
        'layout': fields.selection([
            ('image', 'Image only'),
            ('image_text', 'Image and title'),
            ('complete', 'Complete'),
            #('label', 'Label'), # TODO manage label mode
            ], 'Layout')
        }
         
    _defaults = {
        'date': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        'layout': lambda *x: 'complete',
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

    # -------------------------------------------------------------------------
    # Utility:
    # -------------------------------------------------------------------------
    # Parent management:
    def get_config_parameter_note_list(self, cr, uid, context=None):
        ''' Read parameter: 
        '''    
        key = 'product.default.product.parent.note'
        config_pool = self.pool.get('ir.config_parameter')
        config_ids = config_pool.search(cr, uid, [
            ('key', '=', key)], context=context)
        if not config_ids:
            _logger.warning('Parameter not found: %s' % key)
            return []
        config_proxy = config_pool.browse(
            cr, uid, config_ids, context=context)[0]
        return eval(config_proxy.value)    
    
    # -------------------------------------------------------------------------
    #                               MATRIX
    # -------------------------------------------------------------------------
    # Generate matrix utility:
    def get_note_priority(self, product_id=False, partner_id=False, 
            address_id=False, order_id=False, line_id=False):
        ''' Generate a level for priority depent on importance and presence of
            data
            0 = low 7 = max priority
        '''
        # Only product:
        if product_id and not partner_id and not address_id and not order_id \
                and not line_id:
            return 0 # low level
            
        # Only partner:    
        if not product_id and partner_id and not address_id and not order_id \
                and not line_id:
            return 1
        
        # Product-Partner:    
        if product_id and partner_id and not address_id and not order_id \
                and not line_id:
            return 2
        
        # Address:    
        if not product_id and partner_id and address_id and not order_id \
                and not line_id:
            return 3
        
        # Product-Address    
        if product_id and partner_id and address_id and not order_id \
                and not line_id:
            return 4
        
        # Order:    
        if not product_id and partner_id and address_id and order_id \
                and not line_id:
            return 5
        
        # Product-Order:
        if product_id and partner_id and address_id and order_id \
                and not line_id:
            return 6
        
        # Order line:    
        if product_id and partner_id and address_id and order_id and line_id:
            return 7 # high level
        # TODO raise error!
            
                        
    def get_matrix(self, cr, uid, context=None):
        ''' Generate matrix
        '''
        # Generate matrix for arguments present:
        matrix = {}
        type_pool = self.pool.get('note.type')
        type_ids = type_pool.search(cr, uid, [], context=context)
        for item in type_pool.browse(cr, uid, type_ids, context=context):
            # create key=type, value: data for management (overrid., not over.)
            matrix[item] = [False, ]
        return matrix
    
    # Note system generator:
    def generate_note_matrix(self, cr, uid, product_id, partner_id=None, 
            order_id=None, context=None):
        ''' Generate matrix for note content in product passed 
            If present also partner note content
            And if present also for order_id passed
            matrix are for recursive calls
        '''
        note_pool = self.pool.get('note.note')
        
        # Search parent elements >> recursive
        product_proxy = self.browse(cr, uid, product_id, context=context)

        if product_proxy.note_parent_id:
            # Recursive call:
            matrix = self.generate_note_matrix(
                cr, uid, 
                product_id=product_proxy.note_parent_id.id, 
                partner_id=partner_id, 
                order_id=order_id,
                context=context,
                )
        else:        
            # Generate matrix last recursion:
            matrix = self.get_matrix(cr, uid, context=context)
            
        # Continue write current element:
        domain = [('product_id', '=', product_id)]
        if partner_id:
            domain = ['|'].expand(domain)
            domain.append(('partner_id', '=', partner_id))
            
        if order_id:
            domain = ['|'].expand(domain)
            domain.append(('order_id', '=', order_id))
            
        note_ids = note_pool.search(cr, uid, domain, context=context)
        
        # Populate matrix with current product:
        # TODO manage sort:
        for note in note_pool.browse(cr, uid, note_ids, context=context):
            if note.overridable:
                matrix[note.type_id][0] = note
            else:
                matrix[note.type_id].append(note)
        return matrix

    # -------------------------------------------------------------------------
    # Button:
    # -------------------------------------------------------------------------
    def assign_parent_note(self, cr, uid, ids, context=None):
        ''' Assign note depend on code format
        '''
        product_code_split = self.get_config_parameter_note_list(
            cr, uid, context=context)
        if not product_code_split:
            raise osv.except_osv(
                _('Error'), 
                _('Setup config paremeter not found!'))
            
        product_proxy = self.browse(cr, uid, ids, context=context)[0]
        default_code = product_proxy.default_code
        if not default_code:
            raise osv.except_osv(
                _('Error'), 
                _('No default code in product!'))

        product_ids = False        
        for to in product_code_split:  
            if len(default_code) <= to:
                continue
            partial = default_code[0:to].strip()
            product_ids = self.search(cr, uid, [
                ('default_code', '=', partial),
                ], context=context)
            if product_ids:
                break
                
        if not product_ids:
            raise osv.except_osv(
                _('Error'), 
                _('No parent product found!'))
                
        if len(product_ids) > 1:
            _logger.error('Found more parent product code!')
                        
        return self.write(cr, uid, ids, {
            'note_parent_id': product_ids[0],
            }, context=context)        
        
    def get_domain_note_event_filter(self, cr, uid, line, block='pr', 
            context=None):
        ''' Filter block management:
            pass line and get filter for particular block
            
            Possibilities:
            pr: product only
            pa: partner only
            ad: destination only
            or: order only
            pr-pa: product-partner
            pr-ad: product-destination
            pr-or: product-partner-order
            pr-de: product-partner-order-detail
            all: all note no filter
        '''
        # ---------------------------------------------------------------------
        # Filter product always present:
        # ---------------------------------------------------------------------
        product = line.product_id
        note_parent_id = product.note_parent_id.id
        if note_parent_id:
            domain = [('product_id', 'in', (product.id, note_parent_id))]
        else:    
            domain = [('product_id', '=', product.id)]

        # ---------------------------------------------------------------------
        # Start filter block cases:            
        # ---------------------------------------------------------------------
        # Check particular case:
        if block == 'ad' and not line.order_id.destination_partner_id:
            return False
        
        if block == 'pr': # Product block:
            domain.extend([                
                ('partner_id', '=', False),
                ('address_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pa': # Partner block:
            # Only partner filter:
            domain = [
                ('partner_id', '=', line.order_id.partner_id.id),
                ('product_id', '=', False),
                ('address_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ]
        elif block == 'ad': # Address:
            # Only partner filter:
            domain = [ 
                ('address_id', '=', line.order_id.destination_partner_id.id),
                ('product_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ]
        elif block == 'or':  # Order
            domain = [                
                ('product_id', '=', False),
                ('order_id', '=', line.order_id.id),
                ('line_id', '=', False),
                ]
        elif block == 'de':  # Detail
            domain = [                
                ('line_id', '=', line.id),
                ]             
        elif block == 'pr-pa':  # Product partner
            domain.extend([                
                ('partner_id', '=', line.order_id.partner_id.id),
                ('address_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pr-ad':  # Product address
            domain.extend([         
                ('address_id', '=', line.order_id.destination_partner_id.id),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pr-or':  # Product order
            domain.extend([                
                ('order_id', '=', line.order_id.id),
                ('line_id', '=', False),
                ])
        elif block == 'all':
            pass
        return domain
                
    def open_button_note_event(self, cr, uid, ids, block='pr', context=None):
        ''' Button utility for filter note, case:
            pr: product only
            pr-pa: product-partner
            pr-pa-or: product-partner-order
            pr-pa-or-de: product-partner-order-detail
            all: all note no filter
        '''
        product_proxy = self.browse(cr, uid, ids, context=context)[0]
        note_parent_id = product_proxy.note_parent_id.id
        if note_parent_id:
            domain = [('product_id', 'in', (ids[0], note_parent_id))]
        else:    
            domain = [('product_id', '=', ids[0])]
            
        if block == 'pr':
            name = _('Product note')
            domain.extend([                
                ('partner_id', '=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pr-pa':
            name = _('Product partner note')
            domain.extend([                
                ('partner_id', '!=', False),
                ('order_id', '=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pr-pa-or':
            name = _('Product order note')
            domain.extend([                
                ('order_id', '!=', False),
                ('line_id', '=', False),
                ])
        elif block == 'pr-pa-or-de':
            name = _('Product order detail')
            domain.extend([                
                ('line_id', '!=', False),
                ])
        elif block == 'all':
            name = _('All note')
        
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'note.note',
            #'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': domain,
            'context': {'default_product_id': ids[0]},
            'target': 'current', # 'new'
            'nodestroy': False,
            }
    
    # -------------------------------------------------------------------------
    # Button events:
    # -------------------------------------------------------------------------
    def open_product_note_only(self, cr, uid, ids, context=None):
        ''' Button for filter note for: product
        '''
        return self.open_button_note_event(
            cr, uid, ids, block='pr', context=context)
        
    #def open_partner_only(self, cr, uid, ids, context=None):
    #    ''' Button for filter note for: partner
    #    '''
    #    return True
        
    def open_product_partner_only(self, cr, uid, ids, context=None):
        ''' Button for filter note for: product-partner
        '''
        return self.open_button_note_event(
            cr, uid, ids, block='pr-pa', context=context)
        
    #def open_order_only(self, cr, uid, ids, context=None):
    #    ''' Button for filter note for: Order
    #    '''
    #    return True
        
    def open_product_partner_order_only(self, cr, uid, ids, context=None):
        ''' Button for filter note for: Product-Partner-Order
        '''
        return self.open_button_note_event(
            cr, uid, ids, block='pr-pa-or', context=context)
        
    def open_product_partner_order_detail_only(self, cr, uid, ids, 
            context=None):
        ''' Button for filter note for: Order detail
        '''
        return self.open_button_note_event(
            cr, uid, ids, block='pr-pa-or-de', context=context)
        
        
    def open_product_all(self, cr, uid, ids, context=None):
        ''' Button for filter note for:
        '''
        return self.open_button_note_event(
            cr, uid, ids, block='all', context=context)
            
    _columns = {
        'note_ids': fields.one2many('note.note', 'product_id', 'Note system'), 
        'note_parent_id': fields.many2one('product.product', 'Parent product',
            help='Parent product for get detault note elements'), 
        }

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'partner_id', 'Note system'), 
        'address_note_ids': fields.one2many('note.note', 'address_id', 
            'Note system (address)'), 
        }

class SaleOrder(orm.Model):
    """ Model name: SaleOrder
    """    
    _inherit = 'sale.order'
    
    _columns = {
        'note_ids': fields.one2many('note.note', 'order_id', 'Note system'), 
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
