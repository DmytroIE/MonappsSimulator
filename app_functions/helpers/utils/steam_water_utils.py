from math import sqrt


def get_pres_from_sat_temp(t: float):
    """
    The function returns the approximate pressure in barg derived from the saturation temperature.\n
    If the temperature is less than 100 C, the function returns 0.\n
    Valid from 100 to 250*C

    :param t: saturation temperature
    :type t: float
    """
    if t < 100:
        return 0
    return 0.00000850 * t * t * t - 0.00242997 * t * t + 0.27983645 * t - 12.1839


def get_water_density_from_sat_temp(t: float):
    """
    The function calculates the density of water in kg/m^3 derived from the saturation temperature.\n
    For temperatures less than 100 C, the function returns the density value at atmospheric pressure.\n
    Based on the data from the table from here
    https://www.engineeringtoolbox.com/water-density-specific-weight-d_595.html\n
    Valid from 10 to 260*C

    :param t: saturation temperature
    :type t: float
    """
    return -0.00254013 * t * t - 0.1814289 * t + 1002.46842215


def calc_bdn_amount(temp: float, valve_open: bool, kv: float, time: int, backpres_coef: float = 0.9) -> float:
    """
    The function calculates the blowdown amount in kg over the 'time' period based on the saturation temperature,
    valve status and valve coefficient (kv) using the orifice flow formula.
    """
    bdn_pres = get_pres_from_sat_temp(temp)
    density = get_water_density_from_sat_temp(temp)
    # backpres_coef is a coefficient that accounts for backpressure in the blowdown line
    return sqrt(1000 / density * bdn_pres * backpres_coef) * density * kv * time / 3600000 * (1 if valve_open else 0)
