import os

import compose
from compose.config.environment import Environment
from compose.config.interpolation import interpolate
from compose.plugin import compose_patch
from compose.service import BuildError

from build_improved import BuildImproved

docker_build_commands = [
    'FROM',
    'MAINTAINER',
    'RUN',
    'CMD',
    'LABEL',
    'EXPOSE',
    'ENV',
    'ADD',
    'COPY',
    'ENTRYPOINT',
    'VOLUME',
    'USER',
    'WORKDIR',
    'ARG',
    'ONBUILD',
    'STOPSIGNAL',
    'HEALTHCHECK',
    'SHELL'
]

docker_build_excluded_commands = [
    'RUN'
]

docker_build_interpolatable_commands = list(set(docker_build_commands) - set(docker_build_excluded_commands))


def merge_two_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


@compose_patch(compose.service.Service, "build")
def get_version_info(self, original_fnc, no_cache=False, pull=False, force_rm=False):
    tmp_docker_file_name_with_path = None

    if 'build' in self.options:
        environment = merge_two_dicts(
            self.options.get('environment', {}),
            dict(Environment.from_env_file('.'))
        )
        build_path = self.options['build']['context']

        if 'dockerfile' in self.options['build']:
            docker_file_name = self.options['build']['dockerfile']
        else:
            docker_file_name = 'Dockerfile'

        docker_file_name_with_path = os.path.join(build_path, docker_file_name)
        tmp_docker_file_name_with_path = os.path.join(build_path, '.tmp_' + docker_file_name)

        with open(docker_file_name_with_path, 'r') as docker_file,\
                open(tmp_docker_file_name_with_path, 'w') as tmp_docker_file:
            for line in docker_file:
                line_to_write = None

                for command in docker_build_interpolatable_commands:
                    if line.strip().startswith(command):
                        line_to_write = interpolate(line, environment)

                if line_to_write is None:
                    line_to_write = line

                tmp_docker_file.write(line_to_write)

        self.options['build']['dockerfile'] = tmp_docker_file_name_with_path

    try:
        return_value = original_fnc(self, no_cache, pull, force_rm)

        if tmp_docker_file_name_with_path is not None:
            os.remove(tmp_docker_file_name_with_path)

        return return_value
    except BuildError as e:
        if tmp_docker_file_name_with_path is not None:
            os.remove(tmp_docker_file_name_with_path)

        raise e


plugin = BuildImproved
