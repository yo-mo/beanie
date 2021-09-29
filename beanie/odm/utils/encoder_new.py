class Encoder:
    def __init__(self, obj):
        self.object = obj
        self.encoded_list = []
        self._go(self.object)

    def _go(self, obj):
        if hasattr(obj, "get_link"):
            self.encoded_list.append(obj)
            for _, o in obj._iter():
                self._go(o)
