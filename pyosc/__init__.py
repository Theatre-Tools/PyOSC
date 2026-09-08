from oscparser import (
    OSCRGBA,
    OSCArg,
    OSCArray,
    OSCAtomic,
    OSCBlob,
    OSCBundle,
    OSCChar,
    OSCDouble,
    OSCFalse,
    OSCFloat,
    OSCFraming,
    OSCImpulse,
    OSCInt,
    OSCInt64,
    OSCMessage,
    OSCMidi,
    OSCNil,
    OSCString,
    OSCSymbol,
    OSCTimeTag,
    OSCTransport,
    OSCTrue,
)


class OSCArgTypes:
    OSCAtomic = OSCAtomic
    OSCInt = OSCInt
    OSCInt64 = OSCInt64
    OSCFloat = OSCFloat
    OSCDouble = OSCDouble
    OSCString = OSCString
    OSCSymbol = OSCSymbol
    OSCChar = OSCChar
    OSCMidi = OSCMidi
    OSCRGBA = OSCRGBA
    OSCImpulse = OSCImpulse
    OSCNil = OSCNil
    OSCTrue = OSCTrue
    OSCFalse = OSCFalse
    OSCBlob = OSCBlob
    OSCArray = OSCArray


from pyosc.exceptions import Exceptions
from pyosc.peer import Peer
from pyosc.transport import Bind, ConnectionRole, Remote

__all__ = [
    "Bind",
    "ConnectionRole",
    "Exceptions",
    "OSCArg",
    "OSCArgTypes",
    "OSCBundle",
    "OSCFraming",
    "OSCMessage",
    "OSCTimeTag",
    "OSCTransport",
    "Peer",
    "Remote",
]
