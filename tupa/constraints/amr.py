import csv
import os
import re
from collections import defaultdict

from .validation import Constraints, Valid

PLACEHOLDER_PATTERN = re.compile(r"<[^>]*>")
INT_PATTERN = re.compile(r"[+-]?(\d+)")
PREFIXED_RELATION_ENUM = ("op", "snt")
PREFIXED_RELATION_PREP = "prep"
PREFIXED_RELATION_PATTERN = re.compile(r"(?:(op|snt)\d+|(prep)-\w+)(-of)?")
PREFIXED_RELATION_SUBSTITUTION = r"\1\2\3"

# Specific relations
POLARITY = "polarity"
NAME = "name"
OP = "op"
MODE = "mode"
ARG2 = "arg2"
VALUE = "value"
DAY = "day"
MONTH = "month"
YEAR = "year"
YEAR2 = "year2"
DECADE = "decade"
WEEKDAY = "weekday"
QUARTER = "quarter"
CENTURY = "century"
SEASON = "season"
TIMEZONE = "timezone"

# Specific node property values
MINUS = "-"
MODES = ("expressive", "imperative", "interrogative")
DATE_ENTITY = "date-entity"
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
SEASONS = ("winter", "fall", "spring", "summer")

# things to exclude from the graph because they are a separate task
EXTENSIONS = {
    "numbers": (),
    "urls": ("url-entity",),
}

NEGATIONS = {}
VERBALIZATION = defaultdict(dict)
ROLESETS = {}
CATEGORIES = {}


def read_resources():
    prev_dir = os.getcwd()
    if read_resources.done:
        return
    try:
        os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources"))
        with open("negations.txt", encoding="utf-8") as f:
            NEGATIONS.update(csv.reader(f, delimiter=" "))
        with open("rolesets.txt", encoding="utf-8") as f:
            ROLESETS.update((l[0], tuple(l[1:])) for l in csv.reader(f))
        lines = []
        with open("wordnet.txt", encoding="utf-8") as f:
            lines += [re.findall(r'(\S):(\S+)', l) for l in f if l]
        with open("morph-verbalization-v1.01.txt", encoding="utf-8") as f:
            lines += [re.findall(r'::DERIV\S*-(\S)\S+ "(\S+)"', l) for l in f if l and l[0] != "#"]
        for pairs in lines:
            for prefix, word in pairs:
                VERBALIZATION[word].update(pairs)
        with open("verbalization-list-v1.06.txt", encoding="utf-8") as f:
            lines = (re.findall(r"(\S+) TO *(\S+ :\S+)? (\S+-\d+) *(\S+)?", l)[0] for l in f if l and l[0] not in "#D")
            for word, category, verb, suffix in lines:
                VERBALIZATION[word]["V"] = verb
                if category or suffix:
                    CATEGORIES[word] = category.replace(" ", "") + suffix
        with open("have-org-role-91-roles-v1.06.txt", encoding="utf-8") as f:
            # noinspection PyTypeChecker
            CATEGORIES.update(l.split()[::-1] for l in f if l and l[0] not in "#")
        with open("have-rel-role-91-roles-v1.06.txt", encoding="utf-8") as f:
            CATEGORIES.update(re.findall(r"(\S+) (\S+(?: [^:#]\S)*)", l)[0][::-1] for l in f if l and l[0] not in "#")
    finally:
        os.chdir(prev_dir)
    read_resources.done = True


read_resources.done = False


def is_int_in_range(value, s=None, e=None):
    m = INT_PATTERN.match(value)
    if not m:
        return Valid(False, "%s is not numeric" % value)
    num = int(m.group(1))
    return Valid(s is None or num >= s, "%s < %s" % (num, s)) and Valid(e is None or num <= e, "%s > %s" % (num, e))


def is_valid_arg(value, *labs, is_parent=True, is_node_label=True):
    if value is None or PLACEHOLDER_PATTERN.search(value):  # Not labeled yet or not yet resolved properly
        return True
    valid = Valid(message="%s incompatible as %s of %s" % (value, "parent" if is_parent else "child", ", ".join(labs)))
    if is_parent:  # node is a parent of the edge
        if {DAY, MONTH, YEAR, YEAR2, DECADE, WEEKDAY, QUARTER, CENTURY, SEASON, TIMEZONE}.intersection(labs):
            return valid(value == DATE_ENTITY)
    elif is_node_label:
        if WEEKDAY in labs:  # :weekday  excl,a=date-entity,b=[monday|tuesday|wednesday|thursday|friday|saturday|sunday]
            return valid(value in WEEKDAYS)
        elif value in WEEKDAYS:
            return valid(WEEKDAY in labs)
        elif SEASON in labs:  # :season excl,a=date-entity,b=[winter|fall|spring|summer]+
            return valid(value in SEASONS)
        elif NAME in labs:
            return valid(value == NAME)
    # property value, i.e., constant
    elif value == MINUS:  # :polarity excl,b_isconst,b_const=-
        return valid({POLARITY, ARG2, VALUE}.issuperset(labs))
    elif POLARITY in labs:
        return valid(value == MINUS)
    elif MODE in labs:  # :mode excl,b_isconst,b_const=[interrogative|expressive|imperative]
        return valid(value in MODES)
    elif value in MODES:
        return valid(MODE in labs)
    elif DAY in labs:  # :day  a=date-entity,b_isconst,b_const=[...]
        return is_int_in_range(value, 1, 31)
    elif MONTH in labs:  # :month  a=date-entity,b_isconst,b_const=[1|2|3|4|5|6|7|8|9|10|11|12]
        return is_int_in_range(value, 1, 12)
    elif QUARTER in labs:  # :quarter  a=date-entity,b_isconst,b_const=[1|2|3|4]
        return is_int_in_range(value, 1, 4)
    elif {YEAR, YEAR2, DECADE, CENTURY}.intersection(labs):  # :year a=date-entity,b_isconst,b_const=[0-9]+
        return is_int_in_range(value)

    if not value or "-" not in value:
        return True  # What follows is a check for predicate arguments, only relevant for predicates
    args = [t for t in labs if t.startswith("arg") and (t.endswith("-of") != is_parent)]
    if not args:
        return True
    valid_args = ROLESETS.get(value, ())
    return not valid_args or valid(all(t.replace("-of", "").endswith(valid_args) for t in args),
                                   "valid args: " + ", ".join(valid_args))


class AmrConstraints(Constraints):
    def __init__(self, **kwargs):
        super().__init__(multigraph=True, require_implicit_childless=False, allow_orphan_terminals=True,
                         childless_incoming_trigger={POLARITY, CENTURY, DECADE, "polite", "li"}, **kwargs)

    def allow_action(self, action, history):
        return True

    def allow_edge(self, edge):  # Prevent multiple identical edges between the same pair of nodes
        return edge not in edge.parent.outgoing

    def allow_parent(self, node, lab):
        return not lab or is_valid_arg(node.label, lab)

    def allow_child(self, node, lab):
        return not lab or is_valid_arg(node.label, lab, is_parent=False)

    def allow_label(self, node, label):
        return not node.parents or \
               is_valid_arg(label, *node.outgoing_labs) and \
               is_valid_arg(label, *node.incoming_labs, is_parent=False)

    def allow_property_value(self, node, property_value):
        prop, value = property_value
        return is_valid_arg(value, prop, is_parent=False)