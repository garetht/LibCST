# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict
from typing import Callable

from libcst._parser._types.config import PartialParserConfig
from libcst.testing.utils import UnitTest, data_provider


class TestConfig(UnitTest):
    @data_provider(
        {
            "empty": (lambda: PartialParserConfig(),),
            "python_version_a": (lambda: PartialParserConfig(python_version="3.7"),),
            "python_version_b": (lambda: PartialParserConfig(python_version="3.7.1"),),
            "encoding": (lambda: PartialParserConfig(encoding="latin-1"),),
            "default_indent": (lambda: PartialParserConfig(default_indent="\t    "),),
            "default_newline": (lambda: PartialParserConfig(default_newline="\r\n"),),
        }
    )
    def test_valid_partial_parser_config(
        self, factory: Callable[[], PartialParserConfig]
    ) -> None:
        self.assertIsInstance(factory(), PartialParserConfig)

    @data_provider(
        {
            "python_version": (
                lambda: PartialParserConfig(python_version="3.7.1.0"),
                "The given version is not in the right format",
            ),
            "python_version_unsupported": (
                lambda: PartialParserConfig(python_version="3.6"),
                "LibCST can only parse code using Python 3.7's grammar.",
            ),
            "encoding": (
                lambda: PartialParserConfig(encoding="utf-42"),
                "not a supported encoding",
            ),
            "default_indent": (
                lambda: PartialParserConfig(default_indent="badinput"),
                "invalid value for default_indent",
            ),
            "default_newline": (
                lambda: PartialParserConfig(default_newline="\n\r"),
                "invalid value for default_newline",
            ),
        }
    )
    def test_invalid_partial_parser_config(
        self, factory: Callable[[], PartialParserConfig], expected_re: str
    ) -> None:
        with self.assertRaisesRegex(ValueError, expected_re):
            factory()
