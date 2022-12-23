import os, sys, shutil, glob
from packaging import version

import click

from utils.misc import get_realpath
from utils.migration import read_conf, search
from migrations import accept_versions

@click.command()
@click.option('-i', '--input', 'input_', required=True, help="The path of original config file")
@click.option('-o', '--output', default='', help="the path of output config file")
@click.option('-t', '--target', default='2.6.0', help="target version of input path")
def migrate(input_, output, target):
    """
    migrate command will migrate config file style to specific version
    :input_: is the path of the original config file
    :output: is the destination path of config file, the generated configs will storage in it
    :target: is the the target version of config file will upgrade to
    """
    if target not in accept_versions:
        click.echo(f'target version {target} not supported')
        sys.exit(-1)

    if not output:
        output = input_
    input_path = get_realpath(input_)
    output_path = get_realpath(output)

    configs = read_conf(input_path)
    input_version = configs.get('_version')
    if version.parse(input_version) < version.parse('1.9.0'):
        click.echo(
            f'the version {input_version} not supported, make sure the version in input file above 1.8.0'
        )
        sys.exit(-1)
    if input_version == target:
        click.echo(
            f"Version of input harbor.yml is identical to target {input_version}, no need to upgrade"
        )
        sys.exit(0)

    current_input_path = input_path
    for m in search(input_version, target):
        current_output_path = f"harbor.yml.{m.revision}.tmp"
        click.echo(f"migrating to version {m.revision}")
        m.migrate(current_input_path, current_output_path)
        current_input_path = current_output_path
    shutil.copy(current_input_path, output_path)
    click.echo(f"Written new values to {output}")
    for tmp_f in glob.glob("harbor.yml.*.tmp"):
        os.remove(tmp_f)

