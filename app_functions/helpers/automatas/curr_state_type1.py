from enum import IntEnum
from typing import Callable, Literal, Any
from pydantic import BaseModel, NonNegativeInt
from common.constants import CurrStateTypes, HealthGrades
from app_functions.helpers.utils.counters import OnDelayCounter, PlcLikeCounter


class AutomataStates(IntEnum):
    OFF = 0
    UNDEFINED = 1
    OK = 2
    WARNING = 3
    ERROR = 4


class InternalState(BaseModel):
    state: AutomataStates
    prev_state: AutomataStates
    err_counts: NonNegativeInt
    off_counts: NonNegativeInt
    ok_counts: NonNegativeInt
    warn_counts: NonNegativeInt


class Automata:
    """
    This class implements a finite state machine that shapes the current state value by considering
    the values of multiple flags - error, off, ok, and warning. The flags should be provided by
    the calling application that uses an instance of this class to determine the current state.

    It can have a few internal states: OFF, UNDEFINED, OK, WARNING, ERROR. Internal states are not
    100% equal to the current state values; they are rather aimed at organizing the internal logic.
    For instance, the ERROR internal state represents an error in input data and corresponds with
    the UNDEFINED current state value.

    The automata transitions between states based on counter thresholds for error, off, ok, and warning conditions.
    Each state can trigger entry actions, evaluate transitions, and execute permanent actions.

    Key features:
    - Multiple independent counters (error, off, ok, warning) track condition occurrences
    - State transitions occur when counter thresholds are exceeded
    - Supports alarm payload generation for error and warning states
    - Maintains internal state history for persistence and recovery
    - Uses a while loop and the "again" flag to handle multiple transitions in a single execution cycle
    - Provides methods to retrieve the current state, health status, and internal state as a dictionary
    """

    def __init__(
        self,
        init_state: InternalState | None,
        add_to_alarm_payload: Callable[[str, dict | None, int, Literal["e", "w", "i"]], None],
        error_msg: str,
        warning_msg: str,
        counter_type: type[PlcLikeCounter] = OnDelayCounter,
        count_thres: int = 3,
    ) -> None:
        if init_state is None:
            init_state = InternalState(
                state=AutomataStates.UNDEFINED,
                prev_state=AutomataStates.OFF,
                err_counts=0,
                off_counts=0,
                ok_counts=0,
                warn_counts=0,
            )

        self._state = init_state.state
        self._prev_state = init_state.prev_state
        err_counts = init_state.err_counts
        off_counts = init_state.off_counts
        ok_counts = init_state.ok_counts
        warn_counts = init_state.warn_counts
        self._err_counter = counter_type(err_counts, count_thres)
        self._off_counter = counter_type(off_counts, count_thres)
        self._ok_counter = counter_type(ok_counts, count_thres)
        self._warn_counter = counter_type(warn_counts, count_thres)
        self._curr_state = CurrStateTypes.UNDEFINED
        self._health_from_app = HealthGrades.UNDEFINED
        self._add_to_alarm_payload = add_to_alarm_payload
        self._error_msg = error_msg
        self._warning_msg = warning_msg

    def execute(self, rts: int, err_flag: bool, off_flag: bool, ok_flag: bool, warn_flag: bool):

        self._err_counter.tick(err_flag)
        self._off_counter.tick(off_flag)
        self._ok_counter.tick(ok_flag)
        self._warn_counter.tick(warn_flag)

        while True:
            again = False
            self._health_from_app = HealthGrades.UNDEFINED
            match self._state:
                case AutomataStates.OFF:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._err_counter.out:
                        self._state = AutomataStates.ERROR
                        again = True
                    elif not self._off_counter.out:
                        self._state = AutomataStates.UNDEFINED
                        again = True
                    else:
                        # permanent actions
                        self._curr_state = CurrStateTypes.UNDEFINED

                case AutomataStates.UNDEFINED:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._err_counter.out:
                        self._state = AutomataStates.ERROR
                        again = True
                    elif self._off_counter.out:
                        self._state = AutomataStates.OFF
                        again = True
                    elif self._warn_counter.out:
                        self._state = AutomataStates.WARNING
                        again = True
                    elif self._ok_counter.out:
                        self._state = AutomataStates.OK
                        again = True
                    else:
                        # permanent actions
                        self._curr_state = CurrStateTypes.UNDEFINED

                case AutomataStates.ERROR:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if not self._err_counter.out:
                        self._state = AutomataStates.UNDEFINED
                        again = True
                    else:
                        # permanent actions
                        self._health_from_app = HealthGrades.ERROR
                        self._add_to_alarm_payload(self._error_msg, None, rts, "e")
                        self._curr_state = CurrStateTypes.UNDEFINED

                case AutomataStates.OK:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._err_counter.out:
                        self._state = AutomataStates.ERROR
                        again = True
                    elif self._off_counter.out:
                        self._state = AutomataStates.OFF
                        again = True
                    elif self._warn_counter.out:
                        self._state = AutomataStates.WARNING
                        again = True
                    else:
                        # permanent actions
                        self._curr_state = CurrStateTypes.OK

                case AutomataStates.WARNING:
                    # entry actions
                    if self._prev_state != self._state:
                        self._prev_state = self._state

                    # transitions
                    if self._err_counter.out:
                        self._state = AutomataStates.ERROR
                        again = True
                    elif self._off_counter.out:
                        self._state = AutomataStates.OFF
                        again = True
                    elif self._ok_counter.out:
                        self._state = AutomataStates.OK
                        again = True
                    else:
                        # permanent actions
                        self._curr_state = CurrStateTypes.WARNING
                        self._add_to_alarm_payload(self._warning_msg, None, rts, "w")

            if not again:
                break

    def get_curr_state(self) -> CurrStateTypes:
        return self._curr_state

    def get_health_from_app(self) -> HealthGrades:
        return self._health_from_app

    def get_state(self) -> AutomataStates:
        return self._state

    def get_internal_state(self) -> InternalState:
        return InternalState(
            state=self._state,
            prev_state=self._prev_state,
            err_counts=self._err_counter.counts,
            off_counts=self._off_counter.counts,
            ok_counts=self._ok_counter.counts,
            warn_counts=self._warn_counter.counts,
        )

    def get_internal_state_as_dict(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "prev_state": self._prev_state.value,
            "err_counts": self._err_counter.counts,
            "off_counts": self._off_counter.counts,
            "ok_counts": self._ok_counter.counts,
            "warn_counts": self._warn_counter.counts,
        }
