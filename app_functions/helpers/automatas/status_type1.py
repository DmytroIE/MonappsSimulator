from enum import IntEnum
from typing import Callable, Any
from pydantic import BaseModel, NonNegativeInt, PositiveInt, Field, model_validator
from common.constants import StatusTypes
from app_functions.helpers.utils.eval_cond import eval_cond, CondLiteral
from app_functions.helpers.utils.occ_cluster_list import OccurrenceClusterList


class AutomataStates(IntEnum):
    UNDEFINED = 0
    OK = 1
    WARNING = 2
    ERROR = 3


class CondInitDict(BaseModel):
    total_occs: PositiveInt = Field(
        title="""Total number of current state readings \
in the batch required for status evaluation"""
    )
    ok_cond: CondLiteral = Field(title="Condition")
    num_of_ok_occs: NonNegativeInt = Field(title="Number of 'OK current state' readings in the batch")
    warn_cond: CondLiteral = Field(title="Condition")
    num_of_warn_occs: NonNegativeInt = Field(title="Number of 'WARNING current state' readings in the batch")
    undef_cond: CondLiteral = Field(title="Condition")
    num_of_undef_occs: NonNegativeInt = Field(title="Number of 'UNDEFINED current state' readings in the batch")

    @model_validator(mode="after")
    def validate_occurrences_sum(self):
        if self.total_occs < (self.num_of_ok_occs + self.num_of_warn_occs + self.num_of_undef_occs):
            raise ValueError("num_of_ok_occs + num_of_warn_occs + num_of_undef_occs > total_occs")
        return self


class Condition:
    """
    The dict-like object that describes conditions for state transitions of the Type1 status automata.
    These conditions are based on numbers of occurrences of current state within an interval.
    Conditions are joint with logical "and" in the "match" method.
    """

    def __init__(self, init_dict: CondInitDict) -> None:
        super().__init__()
        self._int_dict = init_dict

    def match(self, occs: OccurrenceClusterList) -> bool:
        last_occs = occs.get_slice_with_last_n_occurrences(self._int_dict.total_occs)
        num_of_ok_occs = last_occs.count_occurrences_of_value(StatusTypes.OK)
        num_of_undef_occs = last_occs.count_occurrences_of_value(StatusTypes.UNDEFINED)
        num_of_warn_occs = last_occs.count_occurrences_of_value(StatusTypes.WARNING)
        return (
            eval_cond(num_of_ok_occs, self._int_dict.ok_cond, self._int_dict.num_of_ok_occs)
            and eval_cond(num_of_undef_occs, self._int_dict.undef_cond, self._int_dict.num_of_undef_occs)
            and eval_cond(num_of_warn_occs, self._int_dict.warn_cond, self._int_dict.num_of_warn_occs)
        )


class InternalState(BaseModel):
    state: AutomataStates
    prev_state: AutomataStates


class Automata:
    """
    This type is based on durations of such types of current state - UNDEFINED, OK, WARNING.
    The number of occurrences of current state is not used.
    """

    def __init__(
        self,
        init_state: InternalState | None,
        add_to_alarm_payload: Callable,
        undef_cid: CondInitDict,
        ok_from_undef_cid: CondInitDict,
        ok_from_warn_cid: CondInitDict,
        warn_cid: CondInitDict,
    ) -> None:
        if init_state is None:
            init_state = InternalState(
                state=AutomataStates.UNDEFINED,
                prev_state=AutomataStates.OK,
            )
        self._state = init_state.state
        self._prev_state = init_state.prev_state
        self._undef_cond = Condition(undef_cid)
        self._ok_from_undef_cond = Condition(ok_from_undef_cid)
        self._ok_from_warn_cond = Condition(ok_from_warn_cid)
        self._warn_cond = Condition(warn_cid)
        self._status = StatusTypes.UNDEFINED
        self._add_to_alarm_payload = add_to_alarm_payload

    def execute(self, all_occs: OccurrenceClusterList):
        while True:
            again = False
            match self._state:

                case AutomataStates.UNDEFINED:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._ok_from_undef_cond.match(all_occs):
                        # optimistic approach - we try to assign OK status as soon as possible
                        # if there are no warning conditions
                        self._state = AutomataStates.OK
                        again = True
                    elif self._warn_cond.match(all_occs):
                        self._state = AutomataStates.WARNING
                        again = True
                    else:
                        # permanent actions
                        self._status = StatusTypes.UNDEFINED

                case AutomataStates.OK:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._warn_cond.match(all_occs):
                        self._state = AutomataStates.WARNING
                        again = True
                    elif self._undef_cond.match(all_occs):
                        self._state = AutomataStates.UNDEFINED
                        again = True
                    else:
                        # permanent actions
                        self._status = StatusTypes.OK

                case AutomataStates.WARNING:
                    # entry actions
                    if self._prev_state != self._state:
                        # do something
                        self._prev_state = self._state

                    # transitions
                    if self._ok_from_warn_cond.match(all_occs):
                        self._state = AutomataStates.OK
                        again = True
                    elif self._undef_cond.match(all_occs):
                        self._state = AutomataStates.UNDEFINED
                        again = True
                    else:
                        # permanent actions
                        self._status = StatusTypes.WARNING
            if not again:
                break

    def get_status(self) -> StatusTypes:
        return self._status

    def get_state(self) -> AutomataStates:
        return self._state

    def get_internal_state_as_dict(self) -> dict[str, Any]:
        return {"state": self._state.value, "prev_state": self._prev_state.value}
