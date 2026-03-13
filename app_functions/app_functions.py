from .monitoring import VER1_1_0_0 as MONITORING_VER1_1_0_0
from .fake_data_generation import VER1_1_0_0 as FAKE_DATA_GENERATOR_VER1_1_0_0
from .stall_detection import TX2_1_0_0 as STALL_DETECTION_TX2_1_0_0
from .cond_ret_rate import SMW_TOT_1_0_0 as CRR_SMW_TOT_1_0_0


app_function_map = {
    "monitoring": {
        "VER1 1.0.0": MONITORING_VER1_1_0_0,
    },
    "fake_data_generator": {
        "VER1 1.0.0": FAKE_DATA_GENERATOR_VER1_1_0_0,
    },
    "stall_detection": {
        "TX2 1.0.0": STALL_DETECTION_TX2_1_0_0,
    },
    "cond_ret_rate": {
        "SMW_TOT 1.0.0": CRR_SMW_TOT_1_0_0,
    },
}
