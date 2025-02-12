
import numba
import numpy as np
from numpy import log, exp, log1p, expm1
from sharrow.maths import piece, hard_sigmoid
from .extra_funcs import *
from .extra_vars import *

@numba.jit(cache=True, error_model='numpy', boundscheck=False, nopython=True, fastmath=True)
def taxi_wait_time_PEAK(
    _args, 
    _inputs, 
    _outputs,
    __ozone__taxi_wait_pk
):
    return __ozone__taxi_wait_pk[_args[0],]
