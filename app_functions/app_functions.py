from .monitoring import monitoring_1_0_0
from .fake_data_generator import fake_data_generator_1_0_0
from .stall_detection import TX2_1_0_0
from .cond_ret_rate import SMW_TOT_1_0_0


app_function_map = {
    "monitoring": {
        "1.0.0": monitoring_1_0_0,
    },
    "fake_data_generator": {
        "1.0.0": fake_data_generator_1_0_0,
    },
    "stall_detection": {
        "TX2 1.0.0": TX2_1_0_0,
    },
    "cond_ret_rate": {
        "SMW_TOT 1.0.0": SMW_TOT_1_0_0,
    },
}
