import gi
from smartcard.util import toBytes
from smartcard.CardMonitoring import CardObserver, CardMonitor
from smartcard.CardType import ATRCardType

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Gio, GObject

LTEID_TOOL = "/home/tadas/local/bin/lteid-tool"

LTEID_CARD_TYPE = ATRCardType(
    toBytes("3b 9d 18 81 31 fc 35 80 31 c0 69 4d 54 43 4f 53 73 02 00 00 00"),
    mask=toBytes("ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff 00 00 00"),
)

class CardStatusCheck(GObject.GObject):
    STATUS_ERROR=-1
    STATUS_READY=0
    STATUS_NO_CAN=1
    STATUS_NOT_CONFIGURED=2
    STATUS_WRONG_CARD=3
    STATUS_NO_CARD=4

    __gsignals__ = {
        'status-code': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_INT, ))
    }

    def run(self):
        pid, idin, idout, iderr = GLib.spawn_async(
            [LTEID_TOOL, '--status'],
            flags=GLib.SPAWN_DO_NOT_REAP_CHILD, standard_output=True, standard_error=True
        )
        GLib.child_watch_add(pid, self.on_done)

    def on_done(self, _pid, retval, *_argv):
        status_code = retval / 256 if retval == 0 or retval > 255 else self.STATUS_ERROR
        self.emit("status-code", status_code)


class CanVerify(GObject.GObject):
    STATUS_FAIL=-1
    STATUS_SUCCESS=0

    __gsignals__ = {
        'verify-done': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_INT, ))
    }

    def __init__(self, can):
        super().__init__()
        self.can = can

    def run(self):
        pid, idin, idout, iderr = GLib.spawn_async(
            [LTEID_TOOL, '--verify-can', f"--can={self.can}"],
            flags=GLib.SPAWN_DO_NOT_REAP_CHILD, standard_output=True, standard_error=True
        )
        GLib.child_watch_add(pid, self.on_done)

    def on_done(self, _pid, retval, *_argv):
        status_code = 0 if retval == 0 else -1
        self.emit("verify-done", status_code)


class ToolboxApplication(Gtk.Application):
    def __init__(self):
        self._label_view = None
        self._label_view_label = None
        self._enter_can_view = None
        self._can_entry = None
        self._can_button = None
        self.window = None

        super().__init__(application_id="lt.yoyo.LithuanianEIDToolbox")
        GLib.set_application_name('Lithuanian eID')

        self.card_monitor = CardMonitor()

    def do_activate(self):
        self.window = Gtk.ApplicationWindow(
            application=self,
            title="Lithuanian eID Card",
            height_request=250, width_request=450
        )
        self.window.set_default_size(660, 200)
        self.window.set_child(self.label_view("Insert card into the card reader"))
        self.window.connect("destroy", self.on_close)
        self.window.present()

        self.card_monitor.addObserver(self)

    def update(self, _observable, handlers):
        (inserted_cards, removed_cards) = handlers

        for card in removed_cards:
            GLib.idle_add(self.on_card_removed, card.atr)

        # FIXME: this won't work with more than 1 reader + cards inserted into each
        for card in inserted_cards:
            if LTEID_CARD_TYPE.matches(card.atr):
                GLib.idle_add(self.on_lteid_inserted, card.atr)
            else:
                GLib.idle_add(self.on_unsupported_inserted, card.atr)

    def on_lteid_inserted(self, _atr):
        status_check = CardStatusCheck()
        status_check.connect('status-code', self.on_card_status_determined)
        status_check.run()

        self.window.set_child(self.label_view("Please wait…"))

    def on_card_status_determined(self, _sender, status_code):
        match status_code:
            case CardStatusCheck.STATUS_READY:
                self.window.set_child(self.label_view("Card is ready for use."))
            case CardStatusCheck.STATUS_NO_CAN:
                self.window.set_child(self.enter_can_view())
                self._can_entry.grab_focus()
            case CardStatusCheck.STATUS_NO_CARD:
                self.window.set_child(self.label_view("Insert card into the card reader"))
            case CardStatusCheck.STATUS_WRONG_CARD:
                self.window.set_child(self.label_view("Inserted card does not appear to be Lithuanian eID"))
            case _:
                self.window.set_child(self.label_view("Unknown error."))

    def on_unsupported_inserted(self, _atr):
        self.window.set_child(self.label_view("Inserted card does not appear to be Lithuanian eID"))

    def on_card_removed(self, _atr):
        self.window.set_child(self.label_view("Insert card into the card reader"))

    def on_close(self, _event):
        self.card_monitor.deleteObserver(self)
        self.quit()

    def label_view(self, label_text):
        if self._label_view:
            self._label_view_label.set_label(label_text)
            return self._label_view

        top_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            margin_top=10, margin_bottom=10, margin_start=10, margin_end=10,
            valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER
        )

        self._label_view_label = Gtk.Label(label=label_text)
        top_box.append(self._label_view_label)

        self._label_view = top_box

        return self._label_view

    def enter_can_view(self):
        if self._enter_can_view:
            return self._enter_can_view

        top_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            margin_top=10, margin_bottom=10, margin_start=10, margin_end=10,
            spacing=10
        )

        eid_illustration = Gtk.Picture(
            file=Gio.File.new_for_path('eid-front.png'),
            can_shrink=True, width_request=220
        )
        top_box.append(eid_illustration)

        right_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10, valign=Gtk.Align.CENTER
        )
        top_box.append(right_box)

        can_label = Gtk.Label(label="Enter the 6 digits from bottom right of the card:")
        right_box.append(can_label)

        can_entry_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10, halign=Gtk.Align.CENTER
        )

        self._can_entry = Gtk.Entry(max_length=6, halign=Gtk.Align.CENTER,
                                    max_width_chars=6, input_purpose=Gtk.InputPurpose.PIN)
        can_entry_box.append(self._can_entry)
        self._can_entry.connect("activate", self.on_can_verify)

        self._can_button = Gtk.Button(label="Continue")
        can_entry_box.append(self._can_button)
        self._can_button.connect("clicked", self.on_can_verify)

        right_box.append(can_entry_box)

        self._enter_can_view = top_box

        return self._enter_can_view

    def on_can_verify(self, _sender):
        can_verify = CanVerify(self._can_entry.get_text())
        can_verify.connect('verify-done', self.on_can_verify_done)
        can_verify.run()

        self.window.set_child(self.label_view("Please wait…"))

    def on_can_verify_done(self, _sender, status_code):
        if status_code == CanVerify.STATUS_SUCCESS:
            self.window.set_child(self.label_view("Card is ready for use."))
        else:
            self.window.set_child(self.enter_can_view())
            self._can_entry.grab_focus()

def run():
    app = ToolboxApplication()
    app.run()
