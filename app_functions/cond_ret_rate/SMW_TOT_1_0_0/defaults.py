from app_functions.helpers.automatas.status_type1 import CondInitDict

default_crr_warning_threshold = 60.0
default_window_length_coef = 2.0
default_min_window_length_coef = 1.2
default_min_steam_gen_value = 1000


default_undef_cid = CondInitDict(
    total_occs=20,
    ok_cond="==",
    num_of_ok_occs=0,
    warn_cond="==",
    num_of_warn_occs=0,
    undef_cond=">=",
    num_of_undef_occs=0,
)

default_ok_from_warn_cid = CondInitDict(
    total_occs=18,
    ok_cond=">=",
    num_of_ok_occs=12,
    warn_cond="==",
    num_of_warn_occs=0,
    undef_cond=">=",
    num_of_undef_occs=0,
)

default_warn_cid = CondInitDict(
    total_occs=10,
    ok_cond=">=",
    num_of_ok_occs=0,
    warn_cond=">=",
    num_of_warn_occs=8,
    undef_cond=">=",
    num_of_undef_occs=0,
)

default_ok_from_undef_cid = CondInitDict(
    total_occs=3,
    ok_cond=">=",
    num_of_ok_occs=2,
    warn_cond="==",
    num_of_warn_occs=0,
    undef_cond=">=",
    num_of_undef_occs=0,
)
