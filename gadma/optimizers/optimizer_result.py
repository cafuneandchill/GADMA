import scipy
import numpy as np
import copy

class OptimizerResult(object):
    """
    Class for keeping optimizers result.
    It is based on SciPy.optimize.OptimizeResult but have more information.

    :param x: The solution of the optimization. The best value during run.
    :param y: The value of objective function on x.
    :param success: Whether or not the optimizer exited successfully.
    :type success: bool
    :param status: Termination status of the optimizer. Its value depends on
                   the underlying solver. Refer to message for details.
    :type status: int
    :param message: Description of the cause of the termination.
    :type message: str
    :param X: All solutions that were used in run.
    :param Y: Values of objective function on X.
    :param n_eval: Number of evaluations of the objective functions performed
                   by the optimizer.
    :type n_eval: int
    :param n_iter: Number of iterations performed by the optimizer.
    :type n_iter: int
    :param X_out: Solutions that optimizer decides to show as important at
                  the end.
                  For example, it could be solutions of the last iteration.
                  The most usefull usage is to restart optimizer or run new
                  optimizer with passing it via X_init.
    :param Y_out: Values of objective function on X_out.

    """
    def __init__(self, x, y, success: bool, status: int, message: str,
                 X, Y, n_eval: int, n_iter:int, X_out=[], Y_out=[]):
        self.x = np.array(x, dtype=object)
        self.y = y
        self.success = success
        self.status = status
        self.message = message
        self.X = copy.deepcopy(X)
        self.Y = Y
        self.n_eval = n_eval
        self.n_iter = n_iter
        self.X_out = copy.deepcopy(X_out)
        self.Y_out = Y_out

    @staticmethod
    def from_SciPy_OptimizeResult(scipy_result: scipy.optimize.OptimizeResult):
        """
        Create OptimizerResult from instance of SciPy.optimize.OptimizeResult.
        Please, note that some attributes will be empty.
        """
        return OptimizerResult(x=scipy_result.x,
                               y=scipy_result.fun,
                               success=scipy_result.success,
                               status=scipy_result.status,
                               message=scipy_result.message,
                               X=[],
                               Y=[],
                               n_eval=scipy_result.nfev,
                               n_iter=scipy_result.nit,
                               X_out=[scipy_result.x],
                               Y_out=[scipy_result.fun])

    def __repr__(self):
        string = f"  status: {self.status}\n"\
                 f" success: {self.success}\n"\
                 f" message: {self.message}\n"\
                 f"       x: {self.x}\n"\
                 f"       y: {self.y}\n"\
                 f"  n_eval: {self.n_eval}\n"\
                 f"  n_iter: {self.n_iter}\n"
        return string
