import os
import pickle
import uuid

import pandas as pd

import dagstermill

from dagster import (
    as_dagster_type,
    check,
    DependencyDefinition,
    Field,
    InputDefinition,
    Int,
    lambda_solid,
    ModeDefinition,
    OutputDefinition,
    PipelineDefinition,
    RepositoryDefinition,
    resource,
    SerializationStrategy,
    solid,
    SolidDefinition,
    SolidInstance,
    String,
)

from dagster_pandas import DataFrame


def nb_test_path(name):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'notebooks/{name}.ipynb'.format(name=name)
    )


def define_hello_world_pipeline():
    return PipelineDefinition(name='hello_world_pipeline', solid_defs=[define_hello_world_solid()])


def define_hello_world_solid():
    return dagstermill.define_dagstermill_solid('hello_world', nb_test_path('hello_world'))


def define_hello_world_with_output():
    return dagstermill.define_dagstermill_solid(
        'hello_world_output', nb_test_path('hello_world_output'), [], [OutputDefinition()]
    )


def define_hello_world_with_output_pipeline():
    return PipelineDefinition(
        name='hello_world_with_output_pipeline', solid_defs=[define_hello_world_with_output()]
    )


def define_hello_world_explicit_yield():
    return dagstermill.define_dagstermill_solid(
        'hello_world_explicit_yield_pipeline',
        nb_test_path('hello_world_explicit_yield'),
        [],
        [OutputDefinition()],
    )


def define_hello_world_explicit_yield_pipeline():
    return PipelineDefinition(
        name='hello_world_explicit_yield_pipeline', solid_defs=[define_hello_world_explicit_yield()]
    )


def define_hello_logging_solid():
    return dagstermill.define_dagstermill_solid('hello_logging', nb_test_path('hello_logging'))


def define_hello_logging_pipeline():
    return PipelineDefinition(
        name='hello_logging_pipeline', solid_defs=[define_hello_logging_solid()]
    )


# This probably should be moved to a library because it is immensely useful for testing
def solid_definition(fn):
    return check.inst(fn(), SolidDefinition)


@solid_definition
def add_two_numbers_pm_solid():
    return dagstermill.define_dagstermill_solid(
        'add_two_numbers',
        nb_test_path('add_two_numbers'),
        [InputDefinition(name='a', dagster_type=Int), InputDefinition(name='b', dagster_type=Int)],
        [OutputDefinition(Int)],
    )


@solid_definition
def mult_two_numbers_pm_solid():
    return dagstermill.define_dagstermill_solid(
        'mult_two_numbers',
        nb_test_path('mult_two_numbers'),
        [InputDefinition(name='a', dagster_type=Int), InputDefinition(name='b', dagster_type=Int)],
        [OutputDefinition(Int)],
    )


@lambda_solid
def return_one():
    return 1


@lambda_solid
def return_two():
    return 2


def define_add_pipeline():
    add_two_numbers = add_two_numbers_pm_solid
    return PipelineDefinition(
        name='test_add_pipeline',
        solid_defs=[return_one, return_two, add_two_numbers],
        dependencies={
            add_two_numbers.name: {
                'a': DependencyDefinition('return_one'),
                'b': DependencyDefinition('return_two'),
            }
        },
    )


@solid(inputs=[], config_field=Field(Int))
def load_constant(context):
    return context.solid_config


def define_test_notebook_dag_pipeline():
    return PipelineDefinition(
        name='test_notebook_dag',
        solid_defs=[load_constant, add_two_numbers_pm_solid, mult_two_numbers_pm_solid],
        dependencies={
            SolidInstance('load_constant', alias='load_a'): {},
            SolidInstance('load_constant', alias='load_b'): {},
            SolidInstance(name='add_two_numbers', alias='add_two'): {
                'a': DependencyDefinition('load_a'),
                'b': DependencyDefinition('load_b'),
            },
            SolidInstance(name='mult_two_numbers', alias='mult_two'): {
                'a': DependencyDefinition('add_two'),
                'b': DependencyDefinition('load_b'),
            },
        },
    )


def define_error_pipeline():
    return PipelineDefinition(
        name='error_pipeline',
        solid_defs=[
            dagstermill.define_dagstermill_solid('error_solid', nb_test_path('error_notebook'))
        ],
    )


@solid_definition
def clean_data_solid():
    return dagstermill.define_dagstermill_solid(
        'clean_data', nb_test_path('clean_data'), outputs=[OutputDefinition(DataFrame)]
    )


@solid_definition
def LR_solid():
    return dagstermill.define_dagstermill_solid(
        'linear_regression',
        nb_test_path('tutorial_LR'),
        inputs=[InputDefinition(name='df', dagster_type=DataFrame)],
    )


@solid_definition
def RF_solid():
    return dagstermill.define_dagstermill_solid(
        'random_forest_regression',
        nb_test_path('tutorial_RF'),
        inputs=[InputDefinition(name='df', dagster_type=DataFrame)],
    )


def define_tutorial_pipeline():
    return PipelineDefinition(
        name='tutorial_pipeline',
        solid_defs=[clean_data_solid, LR_solid, RF_solid],
        dependencies={
            SolidInstance('clean_data'): {},
            SolidInstance('linear_regression'): {'df': DependencyDefinition('clean_data')},
            SolidInstance('random_forest_regression'): {'df': DependencyDefinition('clean_data')},
        },
    )


# Placeholder class to cause the unregistered notebook solid to fail -- custom serialization
# strategies require repository registration
class ComplexSerializationStrategy(SerializationStrategy):  # pylint: disable=no-init
    def serialize(self, value, write_file_obj):
        pass  # pragma: nocover

    def deserialize(self, read_file_obj):
        pass  # pragma: nocover


complex_serialization_strategy = ComplexSerializationStrategy()

ComplexDagsterType = as_dagster_type(
    pd.DataFrame, serialization_strategy=complex_serialization_strategy
)


def no_repo_reg_solid():
    return dagstermill.define_dagstermill_solid(
        'no_repo_reg',
        nb_test_path('no_repo_reg_error'),
        outputs=[OutputDefinition(name='df', dagster_type=ComplexDagsterType)],
    )


def define_no_repo_registration_error_pipeline():
    return PipelineDefinition(name='repo_registration_error', solid_defs=[no_repo_reg_solid()])


@solid('resource_solid', required_resources={'list'})
def resource_solid(context):
    context.resources.list.append('Hello, solid!')
    return True


@solid_definition
def hello_world_resource_solid():
    return dagstermill.define_dagstermill_solid(
        'hello_world_resource',
        nb_test_path('hello_world_resource'),
        inputs=[InputDefinition('nonce')],
        required_resources={'list'},
    )


@solid_definition
def hello_world_resource_with_exception_solid():
    return dagstermill.define_dagstermill_solid(
        'hello_world_resource_with_exception',
        nb_test_path('hello_world_resource_with_exception'),
        inputs=[InputDefinition('nonce')],
        required_resources={'list'},
    )


class FilePickleList(object):
    # This is not thread- or anything else-safe
    def __init__(self, path):
        self.closed = False
        self.id = str(uuid.uuid4())[-6:]
        self.path = path
        self.list = []
        if not os.path.exists(self.path):
            self.write()
        self.read()
        self.open()

    def init(self):
        self.write()

    def open(self):
        self.read()
        self.append('Opened')

    def append(self, obj):
        if self.closed:
            raise Exception()
        self.read()
        self.list.append(self.id + ': ' + obj)
        self.write()

    def read(self):
        with open(self.path, 'rb') as fd:
            self.list = pickle.load(fd)
            return self.list

    def write(self):
        with open(self.path, 'wb') as fd:
            pickle.dump(self.list, fd)

    def close(self):
        self.append('Closed')
        self.closed = True


@resource(config_field=Field(String))
def filepicklelist_resource(init_context):
    filepicklelist = FilePickleList(init_context.resource_config)
    try:
        yield filepicklelist
    finally:
        filepicklelist.close()


def define_resource_pipeline():
    return PipelineDefinition(
        name='resource_pipeline',
        solid_defs=[resource_solid, hello_world_resource_solid],
        dependencies={'hello_world_resource': {'nonce': DependencyDefinition('resource_solid')}},
        mode_definitions=[ModeDefinition(resources={'list': filepicklelist_resource})],
    )


def define_resource_with_exception_pipeline():
    return PipelineDefinition(
        name='resource_with_exception_pipeline',
        solid_defs=[resource_solid, hello_world_resource_with_exception_solid],
        dependencies={
            'hello_world_resource_with_exception': {'nonce': DependencyDefinition('resource_solid')}
        },
        mode_definitions=[ModeDefinition(resources={'list': filepicklelist_resource})],
    )


def define_example_repository():
    return RepositoryDefinition(
        name='notebook_repo',
        pipeline_dict={
            'error_pipeline': define_error_pipeline,
            'hello_world_pipeline': define_hello_world_pipeline,
            'hello_world_with_output_pipeline': define_hello_world_with_output_pipeline,
            'hello_logging_pipeline': define_hello_logging_pipeline,
            'resource_pipeline': define_resource_pipeline,
            'resource_with_exception_pipeline': define_resource_with_exception_pipeline,
            'test_add_pipeline': define_add_pipeline,
            'test_notebook_dag': define_test_notebook_dag_pipeline,
            'tutorial_pipeline': define_tutorial_pipeline,
            'repo_registration_error': define_no_repo_registration_error_pipeline,
        },
    )
