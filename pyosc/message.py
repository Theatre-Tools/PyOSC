from oscparser import OSCMessage
from oscparser.types import OSCArg, OSCArray, OSCFalse, OSCFloat, OSCInt, OSCString, OSCTrue


class Message:
    """Abstractified the OSCMessage for easier use within the Peer class
     - ``address``: The OSC Address of the message
    - ``args``: A tuple of OSCArgs contained within the message

        This class will then convert them to OSCArgs internally
    """

    def __init__(self, address: str, args: list = []):
        self.address = address
        self.args = args

    def to_message(self) -> OSCMessage:
        """Used by the module to get a OSCMessage object to send to the peer

        Returns:
            OSCMessage: Returns an OSC message
        """
        self.newargs = []
        for arg in self.args:
            ## If it is a native python type, convert it to an OSCArg
            if not isinstance(arg, OSCArg):
                if not isinstance(arg, list):
                    self.newargs.append(  # type: ignore
                        self.to_arg(arg),
                    )
                else:
                    self.newargs.append(self._convert_array_recursive(arg))
            else:
                self.newargs += (arg,)

        return OSCMessage(
            address=self.address,
            args=tuple(
                self.newargs,
            ),
        )

    def _convert_array_recursive(self, array: list) -> OSCArray:
        """Recursively converts a list (potentially with nested lists) to an OSCArray

        Args:
            array: The list to convert, may contain nested lists

        Returns:
            OSCArray: An OSCArray with items recursively converted
        """
        converted_items = []
        for item in array:
            if isinstance(item, OSCArg):
                converted_items.append(item)
            elif isinstance(item, list):
                converted_items.append(self._convert_array_recursive(item))
            else:
                converted_items.append(self.to_arg(item))
        return OSCArray(items=tuple(converted_items))

    @staticmethod
    def _from_array_recursive(osc_array: OSCArray) -> list:
        """Recursively converts an OSCArray (potentially with nested arrays) to a native Python list

        Args:
            osc_array: The OSCArray to convert, may contain nested OSCArrays

        Returns:
            list: A native Python list with items recursively converted
        """
        result = []
        for item in osc_array.items:
            if isinstance(item, OSCArray):
                result.append(Message._from_array_recursive(item))
            else:
                result.append(Message.from_arg(item))
        return result

    @staticmethod
    def to_arg(arg):
        try:
            if isinstance(arg, OSCArray):
                return Message._from_array_recursive(arg)
            if isinstance(arg, int):
                return OSCInt(value=arg)
            elif isinstance(arg, str):
                return OSCString(value=arg)
            elif isinstance(arg, bool):
                if arg:
                    return OSCTrue()
                else:
                    return OSCFalse()
            elif isinstance(arg, float):
                return OSCFloat(value=arg)
        except Exception as e:
            raise e

    @staticmethod
    def from_arg(arg: OSCArg):
        """Converts an OSCArg to a native python type"""
        if isinstance(arg, OSCInt):
            return arg.value
        elif isinstance(arg, OSCString):
            return arg.value
        elif isinstance(arg, OSCFloat):
            return arg.value
        elif isinstance(arg, OSCTrue):
            return True
        elif isinstance(arg, OSCFalse):
            return False
        elif isinstance(arg, OSCArray):
            array = []
            for item in arg.items:
                # Recursively handle nested arrays
                array.append(Message.from_arg(item))
            return array

    @staticmethod
    def from_message(message: OSCMessage):
        """Converts an OSCMessage to a Message object, does the inverse of to_message"""

        ## take in the args, and convert them from OSCArgs to native python types
        args = []
        for arg in message.args:
            args.append(Message.from_arg(arg))
        return Message(address=message.address, args=args)

