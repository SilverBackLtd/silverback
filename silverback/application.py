import os
from time import time_ns
from typing import Callable, Union

from ape import accounts, networks
from ape.contracts import ContractEvent
from ape.logging import logger
from ape.managers.chain import BlockContainer
from fastapi import FastAPI as _BaseApp
from fastapi.types import DecoratedCallable

from .exceptions import ApeException, CircuitBreaker, Halt, SilverBackException

EXCEPTION_STRIKE_COUNT = os.environ.get("SILVERBACK_EXCEPTION_STRIKE_COUNT", 3)


class AppState(dict):
    def __getattr__(self, attr_name):
        try:
            return self.__getitem__(attr_name)

        except IndexError:
            raise AttributeError(f"{self.__class__.__name__} has no attribute '{attr_name}'")

    def __setattr__(self, attr_name, attr_val):
        self.__setitem__(attr_name, attr_val)


def add_execution_info(
    fn: Callable[[DecoratedCallable], DecoratedCallable]
) -> Callable[[DecoratedCallable], DecoratedCallable]:
    async def add_run_time(*args, **kwargs):
        start = time_ns()
        result = await fn(*args, **kwargs)
        return {"fn_runtime": time_ns() - start, **result}

    return add_run_time


class SilverBackApp(_BaseApp):
    def __init__(self, *args, **kwargs):
        """
        Create app
        """
        network_triple = os.environ.get(
            "SILVERBACK_NETWORK_CHOICE",
            networks.default_ecosystem.name,
        )
        self.network = networks.parse_network_choice(network_triple)
        self.network.__enter__()

        super().__init__(*args, **kwargs)

        # NOTE: Track ad-hoc state this way, it makes it easy to store things across methods
        self.state = AppState()

        if signer_alias := os.environ.get("SILVERBACK_SIGNER_ALIAS"):
            # NOTE: Will only have a signer if assigned one here (or in app)
            self.state.signer = accounts.load(signer_alias)

    def __getattr__(self, attr_name):
        return getattr(self.state, attr_name)

    def __setattr__(self, attr_name, attr_val):
        setattr(self.state, attr_name, attr_val)

    def _make_call(self, endpoint: str) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self.post(endpoint)

    def start(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """
        Code to execute on startup / restart after an error.
        """
        return self._make_call("/start")

    def exec(self, container: Union[BlockContainer, ContractEvent], **iterator_kwargs):

        if isinstance(container, BlockContainer):
            call_name = "/exec/block"

        elif isinstance(container, ContractEvent):
            call_name = f"/exec/{container.contract.address}/events/{container.abi.name}"

        else:
            raise  # Unsupported container type

        return self._make_call(call_name)

    def stop(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """
        Code to execute on normal shutdown.
        """
        return self._make_call("/stop")


class Runner:
    async def run(self):
        try:
            self.start()
            self.running = True
            self.exception_count = 0

        except ApeException as e:
            logger.error(f"Failed to start: {e}")

        while self.running:
            try:
                await self.exec()

            except CircuitBreaker as e:
                logger.error(f"Circuit breaker was tripped: {e}")
                break

            except SilverBackException as e:
                logger.warning(f"Other exception detected: {e}")

                if self.exception_count < EXCEPTION_STRIKE_COUNT:
                    logger.error("Exception strike count was tripped")
                    break

                self.exception_count += 1

        self.stop()
        self.network.__exit__()
        raise Halt()
