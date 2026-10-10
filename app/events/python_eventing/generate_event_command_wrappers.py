from typing import Type

from app.engine.codegen.codegen_utils import GeneratedSource, get_codegen_header
from app.events.event_commands import EventCommand, get_all_event_commands
from app.events.event_version import EventVersion


def create_wrapper_func(command_name: str, command_t: Type[EventCommand]):
    command_param_names = command_t.keywords
    command_params = ', '.join([f'{p}: Any' for p in command_param_names])
    if command_params:
        command_params += ', '

    command_params_list = '[' + ', '.join([f'"{param}"' for param in command_param_names]) + ']'

    command_optional_param_names = command_t.optional_keywords
    command_optional_params = ', '.join(["%s: Any = None" % param for param in command_optional_param_names])
    if command_optional_params:
        command_optional_params += ', '

    command_param_dict_str = ', '.join(['"%s": %s' % (param.replace('*', ''), param.replace('*', '')) for param in command_param_names + command_optional_param_names])
    command_param_dict_str = '{' + command_param_dict_str + '}'
    func = \
"""
def {command_name}({command_params}{command_optional_params}) -> event_commands.{command_type}:
    command_t = event_commands.{command_type}
    parameters: dict[str, Any] = {command_param_dict}
    parameters = dict(filter(optional_value_filter({command_params_list}), parameters.items()))
    for k, v in parameters.items():
        if isinstance(v, str):
            param_name = command_t.get_validator_from_keyword(k)
            if param_name is None:
                continue
            param_validator = event_validators.get(param_name)
            if param_validator and issubclass(param_validator, event_validators.EnumValidator):
                parameters[k] = event_validators.convert(param_name, v)
    return command_t(parameters=parameters).set_flags('from_python')
""".format(command_name=command_name, command_type=command_t.__name__, command_params_list=command_params_list,
           command_params=command_params, command_optional_params=command_optional_params,
           command_param_dict=command_param_dict_str)
    return func

def generate_event_command_python_wrappers():
    import os
    dir_path = os.path.dirname(os.path.realpath(__file__))
    generated_event_wrappers = GeneratedSource(os.path.join(dir_path, 'python_event_command_wrappers.py'))

    generated_event_wrappers.writelines(get_codegen_header())

    with open(os.path.join(dir_path, 'python_event_commands_base.py'), 'r') as event_commands_base:
        # copy item system base
        for line in event_commands_base.readlines():
            generated_event_wrappers.write(line)

    for command_name, command_t in get_all_event_commands(EventVersion.PYEV1).items():
        func_str = create_wrapper_func(command_name, command_t)
        generated_event_wrappers.write(func_str)

    generated_event_wrappers.close()