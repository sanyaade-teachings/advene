#
# This file is part of Advene.
#
# Advene is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Advene is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

# Advene finder, a la MacOS X

# Advene part
from advene.gui.views.tree import DetailedTreeModel
from advene.gui.views import AdhocView
from advene.gui.views.annotationdisplay import AnnotationDisplay
from advene.gui.views.relationdisplay import RelationDisplay
from advene.model.schema import AnnotationType, RelationType
from advene.model.annotation import Annotation, Relation
from advene.model.view import View
from advene.model.resources import ResourceData
from advene.model.query import Query
import advene.gui.popup
import advene.util.helper as helper

from gettext import gettext as _

import gtk

name="Package finder view plugin"

def register(controller):
    controller.register_viewclass(Finder)

# Matching between element classes and the FinderColumn class
CLASS2COLUMN={}

class FinderColumn:
    """Abstract FinderColumn class.
    """
    def __init__(self, controller=None, node=None, callback=None, parent=None):
        self.controller=controller
        self.node=node
        self.callback=callback
        self.previous=parent
        self.next=None
        self.widget=self.build_widget()

    def close(self):
        """Close this column, and all following ones.
        """
        if self.next is not None:
            self.next.close()
        self.widget.destroy()
        if self.previous is not None:
            self.previous.next=None

    def get_name(self):
        if self.node is None:
            return "FIXME"
        return self.node[self.COLUMN_TITLE]
    name=property(fget=get_name, doc="Displayed name for the element")
            
    def update(self, node=None):
        self.node=node
        return True

    def get_name(self):
        if self.node is None:
            return "FIXME"
        return self.node[self.COLUMN_TITLE]
    name=property(fget=get_name, doc="Displayed name for the element")

    def build_widget(self):
        return gtk.Label("Generic finder column")

class ModelColumn(FinderColumn):
    COLUMN_TITLE=0
    COLUMN_NODE=1
    COLUMN_COLOR=2

    def get_valid_members(self, el):
        """Return the list of valid members for the element.
        """
        def title(c):
            el=c[DetailedTreeModel.COLUMN_ELEMENT]
            if isinstance(el, AnnotationType):
                return "(%d) %s" % (len(el.annotations), c[DetailedTreeModel.COLUMN_TITLE])
            elif isinstance(el, RelationType):
                return "(%d) %s" % (len(el.relations), c[DetailedTreeModel.COLUMN_TITLE])
            else:
                return c[DetailedTreeModel.COLUMN_TITLE]
            
        return [ (title(c),
                  c, 
                  c[DetailedTreeModel.COLUMN_COLOR]) for c in self.node.iterchildren() ]

    def get_liststore(self):
        ls=gtk.ListStore(str, object, str)
        if self.node is None:
            return ls
        for row in self.get_valid_members(self.node):
            ls.append(row)
        return ls

    def update(self, node=None):
        self.node=node
        self.liststore.clear()
        if self.node is None:
            return True
        self.label.set_label(self.name)
        for row in self.get_valid_members(node):
            self.liststore.append(row)

        if self.next is not None:
            # There is a next column. Should we still display it ?
            if not [ r 
                     for r in self.liststore
                     if r[self.COLUMN_NODE] == self.next.node ]:
                # The next node is no more in the current elements.
                self.next.close()
                self.next=None
        return True

    def on_column_activation(self, widget):
        # Delete all next columns
        cb=self.next
        if cb:
            cb.close()
        self.next=None
        return True

    def on_button_press(self, widget, event):
        if not event.button in (1, 3):
            return False
        x = int(event.x)
        y = int(event.y)
        node=None
        if not event.window is widget.get_bin_window():
            return False
        model = widget.get_model()
        t = widget.get_path_at_pos(x, y)
        if t is None:
            return False
        path, col, cx, cy = t
        it = model.get_iter(path)
        node = model.get_value(it, DetailedTreeModel.COLUMN_ELEMENT)
        widget.get_selection().select_path (path)
        if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            # Double-click: edit the element
            self.controller.gui.edit_element(node[DetailedTreeModel.COLUMN_ELEMENT])
            return True
        elif event.button == 3:
            menu = advene.gui.popup.Menu(node[DetailedTreeModel.COLUMN_ELEMENT], controller=self.controller)
            menu.popup()
            return True
        return False

    def on_changed_selection(self, selection, model):
        att=None
        if selection is not None:
            store, it = selection.get_selected()
            if it is not None:
                att = model.get_value (it, self.COLUMN_NODE)
        if att and self.callback:
            self.callback(self, att)
            return True
        return False

    def build_widget(self):
        vbox=gtk.VBox()

        self.label=gtk.Button(self.name)
        self.label.connect("clicked", self.on_column_activation)
        vbox.pack_start(self.label, expand=False)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_AUTOMATIC)
        vbox.add (sw)

        self.liststore = self.get_liststore()
        self.listview = gtk.TreeView(self.liststore)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Attributes", renderer, 
                                    text=self.COLUMN_TITLE, 
                                    cell_background=self.COLUMN_COLOR)
        column.set_widget(gtk.Label())
        self.listview.append_column(column)

        selection = self.listview.get_selection()
        selection.unselect_all()
        selection.connect('changed', self.on_changed_selection, self.liststore)
        self.listview.connect("button-press-event", self.on_button_press)


        sw.add_with_viewport(self.listview)

        vbox.show_all()
        return vbox

class AnnotationColumn(FinderColumn):
    def update(self, node=None):
        self.node=node
        self.view.set_annotation(node[DetailedTreeModel.COLUMN_ELEMENT])
        return True

    def build_widget(self):
        self.view=AnnotationDisplay(controller=self.controller, annotation=self.node[DetailedTreeModel.COLUMN_ELEMENT])
        return self.view.widget
CLASS2COLUMN[Annotation]=AnnotationColumn

class RelationColumn(FinderColumn):
    def update(self, node=None):
        self.node=node
        self.view.set_relation(node[DetailedTreeModel.COLUMN_ELEMENT])
        return True

    def build_widget(self):
        self.view=RelationDisplay(controller=self.controller, relation=self.node[DetailedTreeModel.COLUMN_ELEMENT])
        return self.view.widget
CLASS2COLUMN[Relation]=RelationColumn

class ViewColumn(FinderColumn):
    def __init__(self, controller=None, node=None, callback=None, parent=None):
        FinderColumn.__init__(self, controller, node, callback, parent)
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]
        self.update(node)

    def update(self, node=None):
        self.node=node
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]

        self.label['title'].set_markup(_("View <b>%(title)s</b>\nId: %(id)s") % {
                'title': self.controller.get_title(self.element),
                'id': self.element.id })
        
        t=helper.get_view_type(self.element)
        self.label['activate'].set_sensitive(True)
        if t == 'static':
            self.label['activate'].set_label(_("Open in webbrowser"))
            self.label['info'].set_markup(_("View applied to %s\n") % self.element.matchFilter['class'])
            if not self.element.matchFilter['class'] in ('package', '*'):
                self.label['activate'].set_sensitive(False)
        elif t == 'dynamic':
            self.label['info'].set_text('')
            self.label['activate'].set_label(_("Activate"))
        elif t == 'adhoc':
            self.label['info'].set_text('')
            self.label['activate'].set_label(_("Open in GUI"))
        else:
            self.label['activate'].set_label(_("Unknown type of view??"))
            self.label['activate'].set_sensitive(False)
        return True

    def activate(self, *p):
        """Action to be executed.
        """
        t=helper.get_view_type(self.element)
        if t == 'static':
            c=self.controller.build_context()
            url=c.evaluateValue('here/view/%s/absolute_url' % self.element.id)
            self.controller.open_url(url)
        elif t == 'dynamic':
            self.controller.activate_stbv(self.element)
        elif t == 'adhoc':
            self.controller.gui.open_adhoc_view(self.element, destination='east')
        return True

    def build_widget(self):
        vbox=gtk.VBox()
        self.label={}
        self.label['title']=gtk.Label()
        vbox.pack_start(self.label['title'], expand=False)
        self.label['info']=gtk.Label()
        vbox.pack_start(self.label['info'], expand=False)
        b=self.label['edit']=gtk.Button(_("Edit view"))
        b.connect('clicked', lambda w: self.controller.gui.edit_element(self.element))
        vbox.pack_start(b, expand=False)

        b=self.label['activate']=gtk.Button(_("Open view"))
        b.connect('clicked', self.activate)
        vbox.pack_start(b, expand=False)

        vbox.show_all()
        return vbox
CLASS2COLUMN[View]=ViewColumn

class QueryColumn(FinderColumn):
    def __init__(self, controller=None, node=None, callback=None, parent=None):
        FinderColumn.__init__(self, controller, node, callback, parent)
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]
        self.update(node)

    def update(self, node=None):
        self.node=node
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]

        self.label['title'].set_markup(_("%(type)s <b>%(title)s</b>\nId: %(id)s") % {
                'type': helper.get_type(self.element),
                'title': self.controller.get_title(self.element),
                'id': self.element.id })        
        return True

    def build_widget(self):
        vbox=gtk.VBox()
        self.label={}
        self.label['title']=gtk.Label()
        vbox.pack_start(self.label['title'], expand=False)
        b=self.label['edit']=gtk.Button(_("Edit query"))
        b.connect('clicked', lambda w: self.controller.gui.edit_element(self.element))
        vbox.pack_start(b, expand=False)
        vbox.show_all()
        return vbox
CLASS2COLUMN[Query]=QueryColumn

class ResourceColumn(FinderColumn):
    def __init__(self, controller=None, node=None, callback=None, parent=None):
        FinderColumn.__init__(self, controller, node, callback, parent)
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]
        self.update(node)

    def update(self, node=None):
        self.node=node
        self.element=self.node[DetailedTreeModel.COLUMN_ELEMENT]
        self.label['title'].set_markup(_("%(type)s <b>%(title)s</b>\nId: %(id)s") % {
                'type': helper.get_type(self.element),
                'title': self.controller.get_title(self.element),
                'id': self.element.id })        
        self.update_preview()
        return True

    def update_preview(self):
        self.preview.foreach(self.preview.remove)
        if self.element.mimetype.startswith('image/'):
            i=gtk.Image()
            pixbuf=gtk.gdk.pixbuf_new_from_file(self.element.file_)
            i.set_from_pixbuf(pixbuf)
            self.preview.add(i)
            i.show()
        return True

    def build_widget(self):
        vbox=gtk.VBox()
        self.label={}
        self.label['title']=gtk.Label()
        vbox.pack_start(self.label['title'], expand=False)
        b=self.label['edit']=gtk.Button(_("Edit resource"))
        b.connect('clicked', lambda w: self.controller.gui.edit_element(self.element))
        vbox.pack_start(b, expand=False)
        self.preview=gtk.VBox()
        vbox.add(self.preview)
        vbox.show_all()
        return vbox
CLASS2COLUMN[ResourceData]=ResourceColumn

class Finder(AdhocView):
    view_name = _("Package finder")
    view_id = 'finder'
    tooltip=_("Column-based package finder")
    def __init__(self, controller=None, parameters=None):
        super(Finder, self).__init__(controller=controller)
        self.close_on_package_load = False
        self.contextual_actions = []
        
        self.package=controller.package
        self.controller=controller

        self.model=DetailedTreeModel(controller=controller, package=self.package)
        # 640 / 3
        self.column_width=210
        self.rootcolumn=None
        self.widget=self.build_widget()

    def refresh(self):
        c=self.rootcolumn
        c.update(c.node)
        while c.next is not None:
            c=c.next
            c.update(c.node)
        return True

    def update_element(self, element=None, event=None):
        if event.endswith('Create'):
            self.model.update_element(element, created=True)
            self.refresh()
        elif event.endswith('EditEnd'):
            self.model.update_element(element, created=False)
            self.refresh()
        elif event.endswith('Delete'):
            self.model.remove_element(element)
            cb=self.rootcolumn.next
            while cb is not None:
                if [ r 
                     for r in cb.liststore
                     if r[ModelColumn.COLUMN_NODE][DetailedTreeModel.COLUMN_ELEMENT] == element ]:
                    # The element is present in the list of
                    # children. Remove the next column if necessary
                    # and update the children list.
                    cb.update(node=cb.node)
                    if cb.next is not None and cb.next.node[DetailedTreeModel.COLUMN_ELEMENT] == element:
                        cb.next.close()

                cb=cb.next
            #self.update_model(element.rootPackage)
        else:
            return "Unknown event %s" % event
        return

    def update_annotation(self, annotation=None, event=None):
        """Update the annotation.
        """
        self.update_element(annotation, event)
        return

    def update_relation(self, relation=None, event=None):
        """Update the relation.
        """
        self.update_element(relation, event)
        return

    def update_view(self, view=None, event=None):
        self.update_element(view, event)
        return

    def update_query(self, query=None, event=None):
        self.update_element(query, event)
        return

    def update_schema(self, schema=None, event=None):
        self.update_element(schema, event)
        return

    def update_annotationtype(self, annotationtype=None, event=None):
        self.update_element(annotationtype, event)
        return

    def update_relationtype(self, relationtype=None, event=None):
        """Update the relationtype
        """
        self.update_element(relationtype, event)
        return

    def update_resource(self, resource=None, event=None):
        self.update_element(resource, event)
        return

    def update_model(self, package=None):
        if package is None:
            package = self.controller.package

        # Reset to the rootcolumn
        cb=self.rootcolumn.next
        while cb is not None:
            cb.widget.destroy()
            cb=cb.next
        self.rootcolumn.next=None

        self.package = package
        self.model=DetailedTreeModel(controller=self.controller, package=package)

        # Update the rootcolumn element
        self.rootcolumn.update(self.model[0])
        return True

    def clicked_callback(self, columnbrowser, node):
        if columnbrowser is None:
            # We selected  the rootcolumn. Delete the next ones
            cb=self.rootcolumn.next
            while cb is not None:
                cb.widget.destroy()
                cb=cb.next
            self.rootcolumn.next=None
        elif columnbrowser.next is None:
            t=type(node[DetailedTreeModel.COLUMN_ELEMENT])
            clazz=CLASS2COLUMN.get(t, ModelColumn)
            # Create a new columnbrowser
            col=clazz(controller=self.controller, 
                      node=node, 
                      callback=self.clicked_callback, 
                      parent=columnbrowser)
            col.widget.set_property("width-request", self.column_width)
            self.hbox.pack_start(col.widget, expand=False)
            columnbrowser.next=col
        else:
            # Delete all next+1 columns (we reuse the next one)
            cb=columnbrowser.next.next
            if cb is not None:
                cb.close()
            # Check if the column is still appropriate for the node
            clazz=CLASS2COLUMN.get(type(node[DetailedTreeModel.COLUMN_ELEMENT]), ModelColumn)
            if not isinstance(columnbrowser.next, clazz):
                # The column is not appropriate for the new node.
                # Close it and reopen it.
                columnbrowser.next.close()
                self.clicked_callback(columnbrowser, node)
            else:
                columnbrowser.next.update(node)

        # Scroll the columns
        adj=self.sw.get_hadjustment()
        adj.value = adj.upper - .1
        return True

    def scroll_event(self, widget=None, event=None):
        if event.state & gtk.gdk.CONTROL_MASK:
            a=widget.get_hadjustment()
            if event.direction == gtk.gdk.SCROLL_DOWN:
                val = a.value + a.step_increment
                if val > a.upper - a.page_size:
                    val = a.upper - a.page_size
                if val != a.value:
                    a.value = val
                    a.value_changed ()
                return True
            elif event.direction == gtk.gdk.SCROLL_UP:
                val = a.value - a.step_increment
                if val < a.lower:
                    val = a.lower
                if val != a.value:
                    a.value = val
                    a.value_changed ()
                return True
        return False

    def build_widget(self):
        vbox=gtk.VBox()

        self.sw=gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.sw.connect('scroll_event', self.scroll_event)
        vbox.add(self.sw)

        self.hbox = gtk.HBox()

        self.rootcolumn=ModelColumn(controller=self.controller,
                                     node=self.model[0],
                                     callback=self.clicked_callback,
                                     parent=None)
        self.rootcolumn.widget.set_property("width-request", self.column_width)
        self.hbox.pack_start(self.rootcolumn.widget, expand=False)

        self.sw.add_with_viewport(self.hbox)

        vbox.show_all()
        return vbox
