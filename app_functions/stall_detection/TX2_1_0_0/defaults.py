from app_functions.helpers.automatas.status_type1 import CondInitDict

default_delta_temp = 10
default_temp_in_threshold = 50
default_cs_delay_trans_counts = 3
default_temp_diff_error_threshold = 0.2


default_undef_cid = CondInitDict(
    total_occs=30 * 24 * 60,
    ok_cond="==",
    num_of_ok_occs=0,
    warn_cond="==",
    num_of_warn_occs=0,
    undef_cond=">=",
    num_of_undef_occs=30 * 24 * 60,
)

default_ok_from_warn_cid = CondInitDict(
    total_occs=30 * 24 * 60,
    num_of_undef_occs=0,
    undef_cond=">=",
    num_of_ok_occs=15 * 24 * 60,
    ok_cond=">=",
    num_of_warn_occs=0,
    warn_cond="==",
)

default_warn_cid = CondInitDict(
    total_occs=5 * 24 * 60,
    ok_cond=">=",
    num_of_ok_occs=0,
    warn_cond=">=",
    num_of_warn_occs=1 * 24 * 60,
    undef_cond=">=",
    num_of_undef_occs=0,
)

default_ok_from_undef_cid = CondInitDict(
    total_occs=1 * 24 * 60,
    num_of_undef_occs=0,
    undef_cond=">=",
    num_of_ok_occs=12 * 60,
    ok_cond=">=",
    num_of_warn_occs=0,
    warn_cond="==",
)
