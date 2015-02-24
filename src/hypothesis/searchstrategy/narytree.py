from __future__ import division, print_function, absolute_import, \
    unicode_literals

from collections import namedtuple

import hypothesis.params as params
from hypothesis.searchstrategy import SearchStrategy, BadData, check_data_type
from hypothesis.internal.compat import hrange
from hypothesis.internal.utils.distributions import geometric
from hypothesis.strategytable import StrategyTable


NAryTree = namedtuple('NAryTree', (
    'branch_labels',
    'leaf_values',
    'branch_keys',
))

Leaf = namedtuple('Leaf', (
    'value',
))

Branch = namedtuple('Branch', (
    'label',
    'keyed_children',
))


class NAryTreeStrategy(SearchStrategy):

    def __init__(self, strategy_table, descriptor):
        self.descriptor = descriptor
        self.leaf_strategy = strategy_table.strategy(descriptor.leaf_values)
        self.branch_key_strategy = strategy_table.strategy(
            descriptor.branch_keys)
        self.branch_label_strategy = strategy_table.strategy(
            descriptor.branch_labels)
        self.parameter = params.CompositeParameter(
            leaf_parameter=self.leaf_strategy.parameter,
            branch_key_parameter=self.branch_key_strategy.parameter,
            branch_label_parameter=self.branch_label_strategy.parameter,

            branch_factor=params.UniformFloatParameter(0.6, 0.99),
        )

    def produce_template(self, random, pv):
        n_children = geometric(random, pv.branch_factor)
        if not n_children:
            return Leaf(self.leaf_strategy.produce_template(
                random, pv.leaf_parameter
            ))
        else:
            children = [
                (self.branch_key_strategy.produce_template(
                    random, pv.branch_key_parameter),
                 self.produce_template(random, pv))
                for _ in hrange(n_children)]
            label = self.branch_label_strategy.produce_template(
                random, pv.branch_label_parameter
            )
            return Branch(
                label=label, keyed_children=children
            )

    def reify(self, template):
        if isinstance(template, Leaf):
            return Leaf(
                self.leaf_strategy.reify(template.value)
            )
        else:
            assert isinstance(template, Branch)
            return Branch(
                label=self.branch_label_strategy.reify(template.label),
                keyed_children=[
                    (
                        self.branch_key_strategy.reify(k),
                        self.reify(v))
                    for k, v in template.keyed_children
                ])

    def simplify(self, template):
        if isinstance(template, Branch):
            for k, v in template.keyed_children:
                yield v
        else:
            for v in self.leaf_strategy.simplify(template.value):
                yield Leaf(v)

    def to_basic(self, template):
        if isinstance(template, Leaf):
            return [self.leaf_strategy.to_basic(template.value)]
        else:
            assert isinstance(template, Branch)
            return [
                self.branch_label_strategy.to_basic(template.label)
                [self.branch_key_strategy.to_basic(k),
                 self.to_basic(v)]
                for k, v in template.keyed_children
            ]

    def from_basic(self, data):
        check_data_type(list, data)
        if not (1 <= len(data) <= 2):
            raise BadData(
                "Expected list of length 1 or 2 but got %r" % (data,))

        if len(data) == 1:
            return Leaf(self.leaf_strategy.from_basic(data[0]))
        else:
            assert len(data) == 2
            return Branch(
                label=self.branch_label_strategy.from_basic(data[0]),
                keyed_children=[
                    (self.branch_key_strategy.from_basic(k),
                     self.from_basic(v))
                    for k, v in data[1]])


StrategyTable.default().define_specification_for_instances(
    NAryTree, NAryTreeStrategy
)