from .totalaizer_utils import add_value_to_totalizer

from .steam_water_utils import calc_bdn_amount, get_pres_from_sat_temp, get_water_density_from_sat_temp

steam_water = {
    "calc_bdn_amount": calc_bdn_amount,
    "get_pres_from_sat_temp": get_pres_from_sat_temp,
    "get_water_density_from_sat_temp": get_water_density_from_sat_temp,
}

tot_utils = {
    "totalize": add_value_to_totalizer
}
