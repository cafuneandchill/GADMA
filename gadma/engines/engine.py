from ..code_generator import id2printfunc
from ..data import DataHolder
_registered_engines = {}


def register_engine(engine):
    """
    Registers the specified engine of the demographic inference.

    :raises ValueError: if engine with the same ``id`` was already\
                        registered.
    """
    if engine.id in _registered_engines:
        raise ValueError(f"Engine of the demographic inference '{engine.id}'"
                         f" already registered.")
    _registered_engines[engine.id] = engine


def get_engine(id):
    """
    Returns the engine of the demographic inference with the specified id.

    :raises ValueError: if engine with such ``id`` was not registered.
    """
    if id not in _registered_engines:
        raise ValueError(f"Engine of the demographic inference '{id}'"
                         f" not registered")
    return _registered_engines[id]()


def all_engines():
    """
    Returns an iterator over all registered engines of the demographic
    inference.
    """
    for engine in _registered_engines.values():
        yield engine()


class Engine(object):
    """
    Abstract class representing an engine of the demographic inference.

    New engine should be inheritted from this class.
    Engine must have at least the ``id``, ``supported_models``,
    ``supported_data`` and ``inner_data`` attributes, and
    implementations of :func:`read_data`, :func:`get_pop_labels`,
    :func:`get_sample_sizes`, :func:`get_outgroup`, :func:`get_seq_len`
    and :func:`objective_function` functions of this abstract class.

    :cvar str id: the unique identifier of the engine.
    :cvar supported_models: list of supported :class:`Model` classes.
    :cvar supported_data: list of supported :class:`DataHolder` classes.
    :cvar inner_data_type: class of inner data that is used by engine.
    """
    id = ''
    supported_models = []
    supported_data = []
    inner_data_type = None

    def __init__(self, data=None, model=None):
        self.data = data
        self.model = model

    @staticmethod
    def read_data(data_holder):
        """
        Reads data from `data_holder.filename` in inner type.

        :param data_holder: Holder of data to read.
        :type data_holder: :class:`gadma.DataHolder`

        :returns: readed data
        :rtype: ``Engine.inner_data_type``
        """
        raise NotImplementedError

    def set_model(self, model):
        """
        Sets new model for the engine.

        :param model: new model.
        :type model: :class:`Model`

        :raises ValueError: when model is not supported by engine.
        """
        if model is None:
            self._model = None
            # in moments and dadi it is used to save thetas
            self.saved_add_info = {}  
            return
        if model.__class__ not in self.supported_models:
            raise ValueError(f"Model {model.__class__} is not supported "
                             f"by {self.id} engine.\nThe supported models"
                             f" are: {self.supported_models}.")
        self._model = model
        self.saved_add_info = {}

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self.set_model(model)

    def set_data(self, data):
        """
        Sets new data for the engine.

        :param data: new data.
        :type data: :class:`DataHolder` or ``inner_data_type``.

        :raises ValueError: when ``data`` is not supported by the engine.
        """
        if data is None:
            self.data_holder = None
            self.inner_data = None
            self.saved_add_info = {}
            return
        cls = data.__class__
        if cls not in self.supported_data and \
                not isinstance(data, self.inner_data_type):
            try:
                transformed_data = self.inner_data_type(data)
                self.set_data(transformed_data)
            except:  # NOQA
                raise ValueError(f"Data class {cls} is "
                                 f"not supported by {self.id} engine.\n"
                                 f"The supported classes are: "
                                 f"{self.supported_data} and "
                                 f"{self.inner_data_type}")
        if isinstance(data, DataHolder):
            self.inner_data = self.read_data(data)
            self.data_holder = data
        elif isinstance(data, self.inner_data_type):
            self.inner_data = data
            self.data_holder = None
        self.saved_add_info = {}

    @property
    def data(self):
        return self.inner_data

    @data.setter
    def data(self, new_data):
        self.set_data(new_data)

    def evaluate(self, values, **options):
        """
        Evaluation of the objective function of the engine.

        :param values: values of variables of setted demographic model.
        """
        raise NotImplementedError

    def set_and_evaluate(self, values, model, data, options={}):
        """
        Sets model and data for the engine instance and evaluates the
        objective function via calling :func:`evaluate`.

        :param values: values of variables of the demographic model.
        :param model: model.
        :type model: class from :attr:``supported_models``
        :param data: holder of the data or raw data for the engine.
        :type data: :class:`gadma.DataHolder` or :attr:``inner_data``

        :raises ValueError: if :param:`model` is `None` and any was not\
            setted before; or if :param:`data_holder` is `None` and any\
            was not setted before.
        """
        if model is not None:
            self.set_model(model)
        if data is not None:
            self.set_data(data)
        if self.model is None:
            raise ValueError("Please set model for engine or pass it as "
                             "argument to function.")
        if self.data is None:
            raise ValueError("Please set data for engine or pass it as "
                             "argument to function.")

        return self.evaluate(values, **options)

    def generate_code(self, values, filename=None, *args):
        """
        Prints nice formated code in the format of engine to file or returns
        it as string if no file is set.

        :param values: values for the engine's model.
        :param filename: file to print code. If None then the string will
                         be returned.
        """
        if self.data_holder is None:
            raise AttributeError("Engine was initialized with inner "
                                 "data. Need gadma.DataHolder for "
                                 "generation of code.")
        return id2printfunc[self.id](self, values,
                                     *args, filename=filename)
