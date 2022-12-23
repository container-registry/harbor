# -*- coding: utf-8 -*-

import os
import base
from datetime import datetime

oras_cmd = "oras"
file_artifact = "artifact.txt"
file_readme = "readme.md"
file_config = "config.json"

def oras_push(harbor_server, user, password, project, repo, tag):
    oras_login(harbor_server, user, password)
    with open(file_artifact, "w") as fo:
        fo.write( "hello artifact" )
    md5_artifact = base.run_command( ["md5sum", file_artifact] )
    with open(file_readme, "w") as fo:
        fo.write( r"Docs on this artifact" )
    md5_readme = base.run_command( [ "md5sum", file_readme] )
    with open(file_config, "w") as fo:
        fo.write( "{\"doc\":\"readme.md\"}" )
    exception = None
    for _ in range(5):
        exception = oras_push_cmd(harbor_server, project, repo, tag)
        if exception is None:
            break
    if exception != None:
        raise exception
    return md5_artifact.split(' ')[0], md5_readme.split(' ')[0]

def oras_push_cmd(harbor_server, project, repo, tag):
    try:
        ret = base.run_command(
            [
                oras_cmd,
                "push",
                f"{harbor_server}/{project}/{repo}:{tag}",
                "--manifest-config",
                "config.json:application/vnd.acme.rocket.config.v1+json",
                f"{file_artifact}:application/vnd.acme.rocket.layer.v1+txt",
                f"{file_readme}:application/vnd.acme.rocket.docs.layer.v1+json",
            ]
        )
        return None
    except Exception as e:
        print("Run command error:", e)
        return e

def oras_login(harbor_server, user, password):
     ret = base.run_command([oras_cmd, "login", "-u", user, "-p", password, harbor_server])

def oras_pull(harbor_server, user, password, project, repo, tag):
    try:
        cwd = os.getcwd()
        cwd = f"{cwd}/tmp" + datetime.now().strftime(r'%m%s')
        if os.path.exists(cwd):
          os.rmdir(cwd)
        os.makedirs(cwd)
        os.chdir(cwd)
    except Exception as e:
        raise Exception('Error: Exited with error {}',format(e))
    ret = base.run_command(
        [oras_cmd, "pull", f"{harbor_server}/{project}/{repo}:{tag}", "-a"]
    )
    assert os.path.exists(file_artifact)
    assert os.path.exists(file_readme)
    return base.run_command( ["md5sum", file_artifact] ).split(' ')[0], base.run_command( [ "md5sum", file_readme] ).split(' ')[0]
