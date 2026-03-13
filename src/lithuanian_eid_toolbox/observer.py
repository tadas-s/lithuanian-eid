import signal
import sys

from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.CardType import ATRCardType
from smartcard.util import toHexString, toBytes

class Observer(CardObserver):
    def update(self, observable, handlers):
        lteid_card_type = ATRCardType(
            toBytes("3b 9d 18 81 31 fc 35 80 31 c0 69 4d 54 43 4f 53 73 02 00 00 00"),
            mask=toBytes("ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff 00 00 00"),
        )

        (addedcards, removedcards) = handlers

        for card in addedcards:
            print("+Inserted: ", toHexString(card.atr))
            if lteid_card_type.matches(card.atr):
                print("ATR matches Lithuanian eID card")

        for card in removedcards:
            print("-Removed: ", toHexString(card.atr))


def sigint_handler(_signal, _frame):
    print("Terminating card observer.")
    sys.exit(0)

def run():
    print("Starting card observer.")
    signal.signal(signal.SIGINT, sigint_handler)

    cardmonitor = CardMonitor()
    cardobserver = Observer()
    cardmonitor.addObserver(cardobserver)

    signal.pause()

    cardmonitor.deleteObserver(cardobserver)
