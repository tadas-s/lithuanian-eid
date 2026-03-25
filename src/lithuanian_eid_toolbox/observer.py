import signal
import sys
import uuid
from functools import partial

from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.CardType import ATRCardType
from smartcard.util import toHexString, toBytes
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio, GObject

LTEID_CARD_TYPE = ATRCardType(
    toBytes("3b 9d 18 81 31 fc 35 80 31 c0 69 4d 54 43 4f 53 73 02 00 00 00"),
    mask=toBytes("ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff 00 00 00"),
)

class ObserverApplication(Gio.Application, CardObserver):
    def __init__(self):
        self.card_monitor = None
        self.notification_id = None
        Gio.Application.__init__(self, application_id="lt.yoyo.LithuanianEIDObserver")
        CardObserver.__init__(self)

    def do_activate(self):
        print("do_activate")

        if not self.card_monitor:
            self.card_monitor = CardMonitor()
            self.card_monitor.addObserver(self)

        self.hold()

    def do_shutdown(self):
        print("Shutting down...")
        self.card_monitor.deleteObserver(self)

    def update(self, observable, handlers):
        (addedcards, removedcards) = handlers

        for card in addedcards:
            print("+Inserted: ", toHexString(card.atr))
            if LTEID_CARD_TYPE.matches(card.atr):
                print("ATR matches Lithuanian eID card")
                GLib.idle_add(self.on_lteid_inserted, card.atr)

        for card in removedcards:
            print("-Removed: ", toHexString(card.atr))
            GLib.idle_add(self.on_card_removed, card.atr)

    def on_lteid_inserted(self, _atr):
        notification = Gio.Notification.new("Lithuanian EID inserted")
        notification.set_body("Click to get started")

        if self.notification_id:
            self.withdraw_notification(self.notification_id)

        self.notification_id = str(uuid.uuid4())
        self.send_notification(self.notification_id, notification)

    def on_card_removed(self, _atr):
        if self.notification_id:
            self.withdraw_notification(self.notification_id)

def sigint_handler(application, _signal, _frame):
    print("!! Terminating card observer. !!")
    application.quit()

def run():
    print("Starting card observer.")

    cardobserver = ObserverApplication()

    signal.signal(signal.SIGINT, partial(sigint_handler, cardobserver))

    cardobserver.run()
