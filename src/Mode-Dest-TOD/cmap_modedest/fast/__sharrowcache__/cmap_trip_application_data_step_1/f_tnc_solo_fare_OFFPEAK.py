
import numba
import numpy as np
from numpy import log, exp, log1p, expm1
from sharrow.maths import piece, hard_sigmoid
from .extra_funcs import *
from .extra_vars import *

@numba.jit(cache=True, error_model='numpy', boundscheck=False, nopython=True, fastmath=True)
def tnc_solo_fare_OFFPEAK(
    _args, 
    _inputs, 
    _outputs,
    __auto_skims__md_dist, __auto_skims__md_time
):
    return tnc_cost(__auto_skims__md_time[_args[0], _args[1]], __auto_skims__md_dist[_args[0], _args[1]], _inputs[1], _inputs[0], tnc_solo_offpeak_struct)
