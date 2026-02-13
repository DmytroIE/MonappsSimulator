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
