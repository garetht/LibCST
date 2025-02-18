# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict

from typing import Dict, Tuple, cast

import libcst as cst
from libcst import parse_module
from libcst._visitors import CSTTransformer
from libcst.metadata.expression_context_provider import (
    ExpressionContext,
    ExpressionContextProvider,
)
from libcst.metadata.wrapper import MetadataWrapper
from libcst.testing.utils import UnitTest


class DependentVisitor(CSTTransformer):
    METADATA_DEPENDENCIES = (ExpressionContextProvider,)

    def __init__(
        self,
        *,
        test: UnitTest,
        name_to_context: Dict[str, ExpressionContext] = {},
        attribute_to_context: Dict[str, ExpressionContext] = {},
        subscript_to_context: Dict[str, ExpressionContext] = {},
        starred_element_to_context: Dict[str, ExpressionContext] = {},
        tuple_to_context: Dict[Tuple[str, ...], ExpressionContext] = {},
        list_to_context: Dict[Tuple[str, ...], ExpressionContext] = {},
    ) -> None:
        self.test = test
        self.name_to_context = name_to_context
        self.attribute_to_context = attribute_to_context
        self.subscript_to_context = subscript_to_context
        self.starred_element_to_context = starred_element_to_context
        self.tuple_to_context = tuple_to_context
        self.list_to_context = list_to_context

    def visit_Name(self, node: cst.Name) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            self.name_to_context[node.value],
        )

    def visit_Attribute(self, node: cst.Attribute) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            self.attribute_to_context[node.attr.value],
        )

    def visit_Subscript(self, node: cst.Subscript) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            # to test it easier, assuming we only use a Name as Subscript value
            self.subscript_to_context[cast(cst.Name, node.value).value],
        )

    def visit_StarredElement(self, node: cst.StarredElement) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            # to test it easier, assuming we only use a Name as StarredElement value
            self.starred_element_to_context[cast(cst.Name, node.value).value],
        )

    def visit_Tuple(self, node: cst.Tuple) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            # to test it easier, assuming we only use Name as Tuple elements
            self.tuple_to_context[
                tuple(cast(cst.Name, e.value).value for e in node.elements)
            ],
        )

    def visit_List(self, node: cst.List) -> None:
        self.test.assertEqual(
            self.get_metadata(ExpressionContextProvider, node),
            # to test it easier, assuming we only use Name as List elements
            self.list_to_context[
                tuple(cast(cst.Name, e.value).value for e in node.elements)
            ],
        )

    def visit_Call(self, node: cst.Call) -> None:
        with self.test.assertRaises(KeyError):
            self.get_metadata(ExpressionContextProvider, node)


class ExpressionContextProviderTest(UnitTest):
    def test_simple_load(self) -> None:
        wrapper = MetadataWrapper(parse_module("a"))
        wrapper.visit(
            DependentVisitor(test=self, name_to_context={"a": ExpressionContext.LOAD})
        )

    def test_simple_assign(self) -> None:
        wrapper = MetadataWrapper(parse_module("a = b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.STORE,
                    "b": ExpressionContext.LOAD,
                },
            )
        )

    def test_assign_to_attribute(self) -> None:
        wrapper = MetadataWrapper(parse_module("a.b = c.d"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.LOAD,
                    "b": ExpressionContext.STORE,
                    "c": ExpressionContext.LOAD,
                    "d": ExpressionContext.LOAD,
                },
                attribute_to_context={
                    "b": ExpressionContext.STORE,
                    "d": ExpressionContext.LOAD,
                },
            )
        )

    def test_assign_with_subscript(self) -> None:
        wrapper = MetadataWrapper(parse_module("a[b] = c[d]"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.LOAD,
                    "b": ExpressionContext.LOAD,
                    "c": ExpressionContext.LOAD,
                    "d": ExpressionContext.LOAD,
                },
                subscript_to_context={
                    "a": ExpressionContext.STORE,
                    "c": ExpressionContext.LOAD,
                },
            )
        )

    def test_augassign(self) -> None:
        wrapper = MetadataWrapper(parse_module("a += b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.STORE,
                    "b": ExpressionContext.LOAD,
                },
            )
        )

    def test_annassign(self) -> None:
        wrapper = MetadataWrapper(parse_module("a: str = b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.STORE,
                    "b": ExpressionContext.LOAD,
                    "str": ExpressionContext.LOAD,
                },
            )
        )

    def test_starred_element_with_assign(self) -> None:
        wrapper = MetadataWrapper(parse_module("*a = b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.LOAD,
                    "b": ExpressionContext.LOAD,
                },
                starred_element_to_context={"a": ExpressionContext.STORE},
            )
        )

    def test_del_simple(self) -> None:
        wrapper = MetadataWrapper(parse_module("del a"))
        wrapper.visit(
            DependentVisitor(test=self, name_to_context={"a": ExpressionContext.DEL})
        )

    def test_del_with_subscript(self) -> None:
        wrapper = MetadataWrapper(parse_module("del a[b]"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.LOAD,
                    "b": ExpressionContext.LOAD,
                },
                subscript_to_context={"a": ExpressionContext.DEL},
            )
        )

    def test_del_with_tuple(self) -> None:
        wrapper = MetadataWrapper(parse_module("del a, b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.DEL,
                    "b": ExpressionContext.DEL,
                },
                tuple_to_context={("a", "b"): ExpressionContext.DEL},
            )
        )

    def test_tuple_with_assign(self) -> None:
        wrapper = MetadataWrapper(parse_module("a, = b"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.STORE,
                    "b": ExpressionContext.LOAD,
                },
                tuple_to_context={("a",): ExpressionContext.STORE},
            )
        )

    def test_list_with_assing(self) -> None:
        wrapper = MetadataWrapper(parse_module("[a] = [b]"))
        wrapper.visit(
            DependentVisitor(
                test=self,
                name_to_context={
                    "a": ExpressionContext.STORE,
                    "b": ExpressionContext.LOAD,
                },
                list_to_context={
                    ("a",): ExpressionContext.STORE,
                    ("b",): ExpressionContext.LOAD,
                },
            )
        )

    def test_invalid_type_for_context(self) -> None:
        wrapper = MetadataWrapper(parse_module("a()"))
        wrapper.visit(
            DependentVisitor(test=self, name_to_context={"a": ExpressionContext.LOAD})
        )
