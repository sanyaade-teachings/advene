
# Advene: Annotate Digital Videos, Exchange on the NEt
# Copyright (C) 2008-2016 Olivier Aubert <contact@olivieraubert.net>
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
# along with Advene; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""Frame selector widget.

It depends on a Controller instance to be able to interact with the video player.
"""

from gi.repository import Gdk
from gi.repository import Gtk
import advene.core.config as config
from advene.gui.widget import TimestampRepresentation, GenericColorButtonWidget
from advene.gui.util import dialog
from gettext import gettext as _

class FrameSelector(object):
    """Frame selector interface.

    Given a timestamp, it displays a series of snapshots around
    the timestamp and allows to select the most appropriate
    one.
    """
    def __init__(self, controller, timestamp=0, callback=None, label=None, border_mode='left'):
        self.controller = controller
        self.timestamp = timestamp
        self.selected_value = timestamp
        self.callback = callback
        if label is None:
            label = _("Click on a frame to select its time.")
        self.label = label
        # border_mode is either 'left', 'right', 'both' or None
        self.border_mode = border_mode

        # Number of displayed timestamps
        self.count = 8
        self.frame_length = 1000 / config.data.preferences['default-fps']

        self.black_color = Gdk.color_parse('black')
        self.red_color = Gdk.color_parse('#ff6666')
        self.mouseover_color = Gdk.color_parse('#ff0000')

        # List of TimestampRepresentation widgets.
        # It is initialized in build_widget()
        self.frames = []
        self.widget = self.build_widget()

    def set_timestamp(self, timestamp):
        """Set the reference timestamp.

        It is the timestamp displayed in the label, and corresponds
        most of the time to the original timestamp (before adjustment).
        """
        self.timestamp = timestamp
        self.selected_value = timestamp
        self.update_timestamp(timestamp)

    def update_timestamp(self, timestamp, focus_index=None):
        """Set the center timestamp.

        If focus_index is not specified, the center timestamp will get
        the focus.

        @param timestamp: the center timestamp
        @type timestamp: long
        @param focus_index: the index of the child widget which should get the focus
        @type focus_index: int
        """
        t = timestamp - self.count / 2 * self.frame_length
        if t < 0:
            # Display from 0. But we have to take this into account
            # when handling focus_index
            index_offset = t / self.frame_length
            t = 0
        else:
            index_offset = 0

        matching_index = -1
        for (i, f) in enumerate(self.frames):
            f.value = t
            f.left_border.set_color(self.black_color)
            f.right_border.set_color(self.black_color)

            if t < self.timestamp:
                f.set_class('advene_previous_frame')
            else:
                if matching_index < 0:
                    matching_index = i

                if t == self.timestamp and self.border_mode == 'right':
                    f.set_class('advene_previous_frame')
                else:
                    f.set_class('advene_next_frame')

            t += self.frame_length

        if matching_index >= 0:
            f = self.frames[matching_index]
            if self.border_mode == 'left' or self.border_mode ==  'both':
                f.left_border.set_color(self.red_color)
            if self.border_mode == 'right' or self.border_mode ==  'both':
                f.right_border.set_color(self.red_color)

        # Handle focus
        if focus_index is None:
            focus_index = self.count / 2

        self.frames[focus_index + index_offset].grab_focus()
        return True

    def update_offset(self, offset, focus_index=None):
        """Update the timestamps to go forward/backward.
        """
        if offset < 0:
            ref=self.frames[0]
            start = max(ref.value + offset * self.frame_length, 0)
        else:
            ref=self.frames[offset]
            start = ref.value
        self.update_timestamp(start + self.count / 2 * self.frame_length, focus_index)
        return True

    def refresh_snapshots(self):
        """Update non-initialized snapshots.
        """
        ic=self.controller.package.imagecache
        for c in self.frames:
            if not ic.is_initialized(c.value):
                self.controller.update_snapshot(c.value)
        return True

    def handle_scroll_event(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP or event.direction == Gdk.ScrollDirection.LEFT:
            offset=-1
        elif event.direction == Gdk.ScrollDirection.DOWN or event.direction == Gdk.ScrollDirection.RIGHT:
            offset=+1
        self.update_offset(offset)
        return True

    def focus_index(self):
        """Return the index of the TimestampRepresentation which has the focus.
        """
        return self.frames.index(self.frames[0].get_parent().get_focus_child())

    def handle_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Left:
            i = self.focus_index()
            if i == 0:
                self.update_offset(-1, focus_index = 0)
            else:
                self.frames[i - 1].grab_focus()
            return True
        elif event.keyval == Gdk.KEY_Right:
            i = self.focus_index()
            if i == len(self.frames) -1:
                self.update_offset(+1, focus_index = -1)
            else:
                self.frames[i + 1].grab_focus()
            return True
        return False

    def get_value(self, title=None):
        if title is None:
            title = _("Select the appropriate snapshot")
        d = Gtk.Dialog(title=title,
                       parent=self.controller.gui.gui.win,
                       flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                       buttons=( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                 Gtk.STOCK_OK, Gtk.ResponseType.OK,
                                 ))

        def callback(v):
            d.response(Gtk.ResponseType.OK)
            return True
        self.callback = callback

        d.vbox.add(self.widget)

        buttons = Gtk.HBox()
        b=Gtk.Button(_("Refresh snapshots"))
        b.set_tooltip_text(_("Refresh missing snapshots"))
        b.connect("clicked", lambda b: self.refresh_snapshots())
        buttons.pack_start(b, False, True, 0)
        d.vbox.pack_start(buttons, False, True, 0)

        d.show_all()
        dialog.center_on_mouse(d)

        res = d.run()
        timestamp = self.timestamp
        if res == Gtk.ResponseType.OK:
            timestamp = self.selected_value
        d.destroy()
        return timestamp

    def select_time(self, button=None):
        """General callback.

        It updates self.selected_value then calls self.callback if defined.
        """
        if button is not None:
            self.selected_value = button.value
        if self.callback is not None:
            self.callback(self.selected_value)
        return True

    def build_widget(self):
        vb=Gtk.VBox()

        l = Gtk.Label(label=self.label)
        vb.pack_start(l, False, True, 0)

        hb=Gtk.HBox()

        eb = Gtk.EventBox()
        ar = Gtk.Arrow(Gtk.ArrowType.LEFT, Gtk.ShadowType.IN)
        ar.set_tooltip_text(_("Click to see more frames or scroll with the mouse wheel"))
        eb.connect('button-press-event', lambda b,e: self.update_offset(-1))
        eb.add(ar)
        hb.pack_start(eb, False, True, 0)

        r = None
        for i in xrange(self.count):

            border = GenericColorButtonWidget('border')
            border.default_size=(3, 110)
            border.local_color=self.black_color

            if r is not None:
                # Previous TimestampRepresentation -> right border
                r.right_border = border

            r = TimestampRepresentation(0, self.controller, width=100, visible_label=True,
                                        epsilon=(1000 / config.data.preferences['default-fps'] - 10))
            self.frames.append(r)
            r.connect("clicked", self.select_time)
            r.left_border = border

            def enter_bookmark(widget, event):
                if self.border_mode == 'left':
                    b=widget.left_border
                elif self.border_mode == 'right':
                    b=widget.right_border
                b.old_color = b.local_color
                b.set_color(self.mouseover_color)
                return False
            def leave_bookmark(widget, event):
                if self.border_mode == 'left':
                    b=widget.left_border
                elif self.border_mode == 'right':
                    b=widget.right_border
                b.set_color(b.old_color)
                return False
            if self.border_mode in ('left', 'right'):
                r.connect('enter-notify-event', enter_bookmark)
                r.connect('leave-notify-event', leave_bookmark)

            hb.pack_start(border, False, True, 0)
            hb.pack_start(r, False, True, 0)

        # Last right border
        border = GenericColorButtonWidget('border')
        border.default_size=(3, 110)
        border.local_color=self.black_color
        r.right_border = border
        hb.pack_start(border, False, True, 0)

        eb = Gtk.EventBox()
        ar = Gtk.Arrow(Gtk.ArrowType.RIGHT, Gtk.ShadowType.IN)
        ar.set_tooltip_text(_("Click to see more frames or scroll with the mouse wheel"))
        eb.connect('button-press-event', lambda b,e: self.update_offset(+1))
        eb.add(ar)
        hb.pack_start(eb, False, True, 0)

        hb.get_style_context().add_class('black_on_black')
        hb.connect('scroll-event', self.handle_scroll_event)
        hb.connect('key-press-event', self.handle_key_press)
        vb.add(hb)

        self.update_timestamp(self.timestamp)
        return vb
