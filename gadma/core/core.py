from ..cli import arg_parser
from ..utils import parallel_wrap, StdAndFileLogger

from .draw_and_generate_code import print_runs_summary
from .core_run import CoreRun

from functools import partial
import numpy as np
import os
import sys

from datetime import datetime
import operator
import multiprocessing
import signal
from multiprocessing import Manager, Pool
import math
import warnings



def job(index, shared_dict, settings):
    obj = CoreRun(index, shared_dict, settings)
    if settings.initial_structure is not None:
        obj.run_with_increase()
    else:
        obj.run_without_increase()


def worker_init():
    """Graceful way to interrupt all processes by Ctrl+C."""
    # ignore the SIGINT in sub process
    def sig_int(signal_num, frame):
        pass

    signal.signal(signal.SIGINT, sig_int)


def main():
    settings_storage, args = arg_parser.get_settings()

    # Form output directory
    log_file = os.path.join(settings_storage.output_directory, 'GADMA.log')
    params_file = os.path.join(settings_storage.output_directory,
                              'params_file')
    extra_params_file = os.path.join(settings_storage.output_directory,
                              'extra_params_file')

    # Change output stream both to stdout and log file
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.stdout = StdAndFileLogger(log_file)
    sys.stderr = StdAndFileLogger(log_file)

    print("--Successful arguments parsing--")

    # Data reading
    print("Data reading")
    data = settings_storage.read_data()
    print("--Successful data reading--")

    # Save parameters
    settings_storage.to_files(params_file, extra_params_file)
    if not args.test:
        print(f"Parameters of launch are saved in output directory: "
              f"{params_file}")
        print(f"All output is saved in output directory: {log_file}")

    print("--Start pipeline--")

    # Change output stream both to stdout and log file
    sys.stdout = saved_stdout
    sys.stdout = StdAndFileLogger(log_file, settings_storage.silence)

    # Create shared dictionary
    m = Manager()
    shared_dict = m.dict()

    # Start pool of processes
    start_time = datetime.now()

    # For debug
#    run_pipeline_with_increase(0, None, model, data, settings_storage.engine,
#              settings_storage.final_structure, global_optimizer,
#              local_optimizer, {}, common_kwargs, None, os.path.join(settings_storage.output_directory, '0'))
#
    pool = Pool(processes=settings_storage.number_of_processes,
                initializer=worker_init)
    try:
        pool_map = pool.map_async(
            partial(parallel_wrap, job),
            [(i + 1, shared_dict, settings_storage)
             for i in range(settings_storage.number_of_repeats)])
        pool.close()

        precision = 1 - int(math.log(settings_storage.eps, 10))

        # graceful way to interrupt all processes by Ctrl+C
        min_counter = 0
        while True:
            try:
                multiple_results = pool_map.get(60)
#                    60 * settings_storage.time_to_print_summary)
                break
            # catch TimeoutError and get again
            except multiprocessing.TimeoutError as ex:
                print_runs_summary(
                    start_time, shared_dict, settings_storage, None, 
                    precision, None)
            except Exception as e:
                pool.terminate()
                raise RuntimeError(str(e))
        print_runs_summary(start_time, shared_dict, settings_storage, None, 
                precision, None)

        sys.stdout = StdAndFileLogger(log_file)

        print('\n--Finish pipeline--\n')
        if args.test:
            print('--Test passed correctly--')
        if settings_storage.theta0 is None:
            print("\nYou didn't specify theta at the beginning. If you want change it and rescale parameters, please see tutorial.\n")
#        if params.resume_dir is not None and (params.initial_structure != params.final_structure).any():
#            print('\nYou have resumed from another launch. Please, check best AIC model, as information about it was lost.\n')

        print('Thank you for using GADMA!')

    except KeyboardInterrupt as e:
        pool.terminate()
        raise KeyboardInterrupt(e)

if __name__ == '__main__':
    main()
