# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict
import inspect
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Collection,
    Iterator,
    Mapping,
    Type,
    TypeVar,
    cast,
)


if TYPE_CHECKING:
    # Circular dependency for typing reasons only
    from libcst._nodes._base import CSTNode  # noqa: F401
    from libcst.metadata.base_provider import (  # noqa: F401
        BaseMetadataProvider,
        ProviderT,
    )
    from libcst.metadata.wrapper import MetadataWrapper  # noqa: F401


_T = TypeVar("_T")

_UNDEFINED_DEFAULT = object()


# TODO: this class should be an ABC but we're waiting on Pyre to fix a bug to
# add this functionality back
class MetadataDependent:
    """
    The low-level base class for all classes that declare required metadata
    dependencies. :class:`~libcst.CSTVisitor` and :class:`~libcst.CSTTransformer`
    extend this class.
    """

    # pyre-ignore[4]: Attribute `metadata` of class
    # `libcst.metadata.dependent.MetadataDependent` must have a type that
    # does not contain `Any`.
    #: A cached copy of metadata computed by :func:`~libcst.MetadataDependent.resolve`.
    #: Prefer using :func:`~libcst.MetadataDependent.get_metadata` over accessing
    #: this attribute directly.
    metadata: Mapping["ProviderT", Mapping["CSTNode", object]]

    #: The set of metadata depedencies declared by this class.
    METADATA_DEPENDENCIES: ClassVar[Collection["ProviderT"]] = ()

    def __init__(self) -> None:
        self.metadata = {}

    @classmethod
    def get_inherited_dependencies(cls) -> Collection["ProviderT"]:
        """
        Returns all metadata dependencies declared by classes in the MRO of ``cls``
        that subclass this class.

        Recursively searches the MRO of the subclass for metadata dependencies.
        """
        try:
            # pyre-fixme[16]: use a hidden attribute to cache the property
            return cls._INHERITED_METADATA_DEPENDENCIES_CACHE
        except AttributeError:
            dependencies = set()
            for c in inspect.getmro(cls):
                if issubclass(c, MetadataDependent):
                    dependencies.update(c.METADATA_DEPENDENCIES)
            cls._INHERITED_METADATA_DEPENDENCIES_CACHE = frozenset(dependencies)
            # pyre-fixme[16]: use a hidden attribute to cache the property
            return cls._INHERITED_METADATA_DEPENDENCIES_CACHE

    @contextmanager
    def resolve(self, wrapper: "MetadataWrapper") -> Iterator[None]:
        """
        Context manager that resolves all metadata dependencies declared by
        ``self`` (using :func:`~libcst.MetadataDependent.get_inherited_dependencies`)
        on ``wrapper`` and caches it on ``self`` for use with
        :func:`~libcst.MetadataDependent.get_metadata`.

        Upon exiting this context manager, the metadata cache on ``self`` is
        cleared.
        """
        self.metadata = wrapper.resolve_many(self.get_inherited_dependencies())
        yield
        self.metadata = {}

    def get_metadata(
        self,
        key: Type["BaseMetadataProvider[_T]"],
        node: "CSTNode",
        default: _T = _UNDEFINED_DEFAULT,
    ) -> _T:
        """
        Returns the metadata provided by the ``key`` if it is accessible from
        this vistor. Metadata is accessible in a subclass of this class if ``key``
        is declared as a dependency by any class in the MRO of this class.
        """
        if key not in self.get_inherited_dependencies():
            raise KeyError(
                f"{key.__name__} is not declared as a dependency from {type(self).__name__}"
            )

        if default is not _UNDEFINED_DEFAULT:
            return cast(_T, self.metadata[key].get(node, default))
        else:
            return cast(_T, self.metadata[key][node])
