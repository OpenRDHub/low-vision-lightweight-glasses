"""轻量 DI 容器 - 手写工厂。

模块不自行实例化具体实现，均通过注入获取。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class Container:
    """轻量依赖注入容器。"""

    _factories: dict[type, Callable[[], Any]] = field(default_factory=dict)
    _instances: dict[type, Any] = field(default_factory=dict)

    def register_factory(self, interface: type[T], factory: Callable[[], T]) -> None:
        """注册工厂。"""
        self._factories[interface] = factory

    def register_instance(self, interface: type[T], instance: T) -> None:
        """注册单例实例。"""
        self._instances[interface] = instance

    def resolve(self, interface: type[T]) -> T:
        """解析依赖。

        优先返回已注册实例，否则用工厂创建并缓存。
        """
        if interface in self._instances:
            return self._instances[interface]  # type: ignore[no-any-return]

        if interface in self._factories:
            instance = self._factories[interface]()
            self._instances[interface] = instance
            return instance  # type: ignore[no-any-return]

        raise KeyError(f"未注册依赖: {interface}")

    def is_registered(self, interface: type) -> bool:
        return interface in self._factories or interface in self._instances

    def clear(self) -> None:
        """清除所有注册（用于测试）。"""
        self._factories.clear()
        self._instances.clear()