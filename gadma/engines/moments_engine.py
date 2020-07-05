from . import Engine, register_engine
from .dadi_moments_common import DadiOrMomentsEngine
from ..models import DemographicModel, CustomDemographicModel, Epoch, Split
from ..utils import DynamicVariable
from .. import SFSDataHolder, VCFDataHolder
import numpy as np


class MomentsEngine(DadiOrMomentsEngine):
    """
    Engine for using :py:mod:`moments` for demographic inference.

    Citation of :py:mod:`moments`:

    Jouganous, J., Long, W., Ragsdale, A. P., & Gravel, S. (2017).
    Inferring the joint demographic history of multiple populations:
    beyond the diffusion approximation. Genetics, 206(3), 1549-1567.
    """

    id = 'moments'  #:
    import moments as base_module
    supported_data = [SFSDataHolder, VCFDataHolder]  #:
    inner_data_type = base_module.Spectrum  #:
    default_dt_fac = 0.01  #:

    @staticmethod
    def _get_kwargs(event, var2value):
        """
        Builds kwargs for moments.Spectrum.integrate functions.

        :param event: build for this event
        :type event: event.Epoch
        :param var2value: dictionary {variable: value}, it is required because
            the dynamics values should be fixed.
        """
        ret_dict = {'tf': event.time_arg}
        if event.dyn_args is not None:
            ret_dict['Npop'] = list()
            for i in range(event.n_pop):
                dyn_arg = event.dyn_args[i]
                if var2value.get(dyn_arg, dyn_arg) == 'Sud':
                    ret_dict['Npop'].append(event.size_args[i])
                else:
                    ret_dict['Npop'].append('nu%d_func' % (i+1))
        else:
            ret_dict['Npop'] = event.size_args

        if event.mig_args is not None:
            ret_dict['m'] = np.zeros(shape=(event.n_pop, event.n_pop),
                                     dtype=object)
            for i in range(event.n_pop):
                for j in range(event.n_pop):
                    if i == j:
                        continue
                    ret_dict['m'][i, j] = event.mig_args[i][j]
        if event.sel_args is not None:
            ret_dict['h'] = event.sel_args
        return ret_dict

    def _moments_inner_func(self, values, ns, dt_fac=0.01):
        """
        Simulates expected SFS for proposed values of variables.

        :param values: values of variables
        :param ns: sample sizes of simulated SFS
        :param dt_fac: step size for numerical solution
        """
        var2value = self.model.var2value(values)
        if isinstance(self.model, CustomDemographicModel):
            vals = [var2value[var] for var in self.model.variables]
            return self.model.function(vals, ns)

        moments = self.base_module

        sts = moments.LinearSystem_1D.steady_state_1D(np.sum(ns))
        fs = moments.Spectrum(sts)

        ns_on_splits = [list(ns)]
        for ind, event in enumerate(reversed(self.model.events)):
            if isinstance(event, Split):
                p = event.pop_to_div
                ns_on_splits.append(ns_on_splits[-1][:-1])
                ns_on_splits[-1][p] += ns_on_splits[-2][-1]
        ns_on_splits = list(reversed(ns_on_splits))[1:]
        n_split = 0

        addit_values = {}
        for ind, event in enumerate(self.model.events):
            if isinstance(event, Epoch):
                if event.dyn_args is not None:
                    for i in range(event.n_pop):
                        dyn_arg = event.dyn_args[i]
                        value = var2value.get(dyn_arg, dyn_arg)
                        if value != 'Sud':
                            func = DynamicVariable.get_func_from_value(value)
                            y1 = var2value.get(event.init_size_args[i],
                                               event.init_size_args[i])
                            y2 = var2value.get(event.size_args[i],
                                               event.size_args[i])
                            x_diff = var2value.get(event.time_arg, event.time_arg)
                            addit_values['nu%d_func' % (i+1)] = func(
                                y1=y1,
                                y2=y2,
                                x_diff=x_diff)
                kwargs_with_vars = self._get_kwargs(event, var2value)
                kwargs = {}
                for x, y in kwargs_with_vars.items():
                    if isinstance(y, np.ndarray):  # migration
                        l_s = np.array(y, dtype=object)
                        for i in range(y.shape[0]):
                            for j in range(y.shape[1]):
                                yel = y[i][j]
                                l_s[i][j] = var2value.get(yel, yel)
                                l_s[i][j] = addit_values.get(l_s[i][j],
                                                                l_s[i][j])
                        kwargs[x] = l_s
                    elif isinstance(y, list):  # pop. sizes, selection, dynamics
                        l_args = list()
                        for y1 in y:
                            l_args.append(var2value.get(y1, y1))
                        kwargs[x] = lambda t: [addit_values[el](t)
                                     if el in addit_values else el
                                     for el in l_args]
                    else: # time
                        kwargs[x] = var2value.get(y, y)
                        kwargs[x] = addit_values.get(kwargs[x], kwargs[x])
                fs.integrate(dt_fac=dt_fac, **kwargs)
            elif isinstance(event, Split):
                ns_split = (ns_on_splits[n_split][event.pop_to_div],
                            ns_on_splits[n_split][-1])
                if event.n_pop == 1:
                    fs = moments.Manips.split_1D_to_2D(fs, *ns_split)
                else:
                    func_name = "split_%dD_to_%dD_%d" % (
                        event.n_pop, event.n_pop + 1, event.pop_to_div + 1)
                    fs = getattr(moments.Manips, func_name)(fs, *ns_split)
                n_split += 1
        return fs

    def draw_schematic_model_plot(self, values, save_file=None, 
                                  fig_title="Demographic Model from GADMA",
                                  nref=None, gen_time=1,
                                  gen_time_units="Generations"):
        """
        Draws schematic plot of the model with values.
        See moments manual for more information.

        :param values: Values of the model parameters, it could be list of
                       values or dictionary {variable name: value}.
        :type values: list or dict
        :param save_file: File to save picture. If None then picture will be
                          displayed to the screen.
        :type save_file: str
        :param fig_title: Title of the figure.
        :type fig_title: str
        :param nref: An ancestral population size. If None then parameters
                     will be drawn in genetic units.
        :type nref: int
        :param gen_type: Time of one generation.
        :type gen_type: float
        :param gen_time_units: Units of :param:`gen_type`. For example, it
                               could be Years, Generations, Thousand Years and
                               so on.
        """
        moments = self.base_module
        # From moments docs about ns:
        # List of sample sizes to be passed as the ns argument to model_func.
        # Actual values do not matter, as long as the dimensionality is correct.
        # So we take small size for fast drawing.
        ns = [4 for _ in range(len(self.data.sample_sizes))]
        plot_mod = moments.ModelPlot.generate_model(self._moments_inner_func,
                                                    values, ns)
        draw_scale = nref is not None
        show = save_file is None     
        if nref is not None:
            nref = int(nref)  
        moments.ModelPlot.plot_model(plot_mod,
                                     save_file = save_file,
                                     show=show,
                                     fig_title=fig_title,
                                     draw_scale=draw_scale,
                                     pop_labels=self.data.pop_ids,
                                     nref=nref,
                                     gen_time=gen_time,
                                     gen_time_units=gen_time_units,
                                     reverse_timeline=True)

    def simulate(self, values, ns, dt_fac=default_dt_fac):
        """
        Returns simulated expected SFS for :attr:`demographic_model` with
        values as parameters. 

        :param values: Values of demographic model parameters.
        :param ns: sample sizes of the simulated SFS.
        """
        moments = self.base_module
        model = self._moments_inner_func(values, ns, dt_fac)
        return model

    def get_theta(self, values, dt_fac=default_dt_fac):
        return super(MomentsEngine, self).get_theta(values, dt_fac)

    def evaluate(self, values, dt_fac=default_dt_fac):
        """
        Simulates SFS from values and evaluate log likelihood between
        simulated SFS and observed SFS.
        """
        return super(MomentsEngine, self).evaluate(values, dt_fac)

    def generate_code(self, values, filename=None, dt_fac=default_dt_fac):
        return super(MomentsEngine, self).generate_code(values, filename,
                                                        dt_fac)
register_engine(MomentsEngine)
