def get_pres_from_sat_temp(t: float):
    """
    The function returns the approximate pressure in barg derived from the saturation temperature\n
    If the temperature is less than 100 C, the function returns 0\n
    Valid from 100 to 250*C

    :param t: saturation temperature
    :type t: float
    """
    if t < 100:
        return 0
    return 0.00000850 * t * t * t - 0.00242997 * t * t + 0.27983645 * t - 12.1839
