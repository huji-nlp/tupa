from collections import OrderedDict


class SubModel(object):
    def __init__(self, params=None, save_path=()):
        self.params = OrderedDict() if params is None else params  # string (param identifier) -> parameter
        self.save_path = save_path

    def save_sub_model(self, d, *args):
        self.get_sub_dict(d).update(args + (("param_keys", list(self.params.keys())),))

    def load_sub_model(self, d, *args):
        d = self.get_sub_dict(d)
        self.params.clear()
        self.params.update(zip(d["param_keys"], args))
        return d

    def get_sub_dict(self, d):
        for element in self.save_path:
            d = d.setdefault(element, OrderedDict())
        return d
