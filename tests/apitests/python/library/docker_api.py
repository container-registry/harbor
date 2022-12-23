# -*- coding: utf-8 -*-

import base
import subprocess
import json
from testutils import BASE_IMAGE, BASE_IMAGE_ABS_PATH_NAME

try:
    import docker
except ImportError:
    import pip
    pip.main(['install', 'docker'])
    import docker

def docker_info_display():
    command = ["docker", "info", "-f", "'{{.OSType}}/{{.Architecture}}'"]
    print("Docker Info: ", command)
    ret = base.run_command(command)
    print("Command return: ", ret)

def docker_login_cmd(harbor_host, username, password, cfg_file = "./tests/apitests/python/update_docker_cfg.sh",  enable_manifest = True):
    if  username == "" or password == "":
        print("[Warnig]: No docker credential was provided.")
        return
    command = ["docker", "login", harbor_host, "-u", username, "-p", password]
    base.run_command(command)
    if enable_manifest == True:
        try:
            ret = subprocess.check_output([cfg_file], shell=False)
        except subprocess.CalledProcessError as exc:
            raise Exception("Failed to update docker config.")

def docker_manifest_create(index, manifests):
    command = ["docker","manifest","create", "--amend", index]
    command.extend(manifests)
    base.run_command(command)

def docker_images_all_list():
    command = ["docker","images","-a"]
    base.run_command(command)

def docker_load_image(image):
    command = ["docker","load","-i", image]
    base.run_command(command)

def docker_image_clean_all():
    docker_images_all_list()
    command = ["docker rmi -f $(docker images -a -q)"]
    base.run_command_with_popen(command)
    command = ["docker","system", "prune", "-a", "-f"]
    base.run_command(command)
    docker_images_all_list()

def docker_manifest_push(index):
    command = ["docker","manifest","push",index]
    ret = base.run_command(command)
    index_sha256=""
    manifest_list=[]
    for line in ret.split("\n"):
        if line[:7] == "sha256:":
            index_sha256 = line
        if line.find('Pushed ref') == 0:
            manifest_list.append(line[-71:])
    return index_sha256, manifest_list

def docker_manifest_push_to_harbor(index, manifests, harbor_server, username, password, cfg_file = "./tests/apitests/python/update_docker_cfg.sh"):
    docker_login_cmd(harbor_server, username, password, cfg_file=cfg_file)
    docker_manifest_create(index, manifests)
    return docker_manifest_push(index)

def list_repositories(harbor_host, username, password, n = None, last = None):
    if n is not None and last is not None:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/_catalog"
            + "?n=%d" % n
            + "&last="
            + last,
            "--insecure",
        ]
    elif n is not None:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/_catalog" + "?n=%d" % n,
            "--insecure",
        ]
    else:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/_catalog",
            "--insecure",
        ]
    ret = base.run_command(command)
    return json.loads(ret).get("repositories","")

def list_image_tags(harbor_host, repository, username, password, n = None, last = None):
    if n is not None and last is not None:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/{repository}/tags/list"
            + "?n=%d" % n
            + "&last="
            + last,
            "--insecure",
        ]
    elif n is not None:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/{repository}/tags/list" + "?n=%d" % n,
            "--insecure",
        ]
    else:
        command = [
            "curl",
            "-s",
            "-u",
            f"{username}:{password}",
            f"https://{harbor_host}/v2/{repository}/tags/list",
            "--insecure",
        ]
    ret = base.run_command(command)
    return json.loads(ret).get("tags","")

class DockerAPI(object):
    def __init__(self):
        self.DCLIENT = docker.APIClient(base_url='unix://var/run/docker.sock',version='auto',timeout=30)
        self.DCLIENT2 = docker.from_env()

    def docker_login(self, registry, username, password, expected_error_message = None):
        ret = ""
        err_message = ""
        if  username == "" or password == "":
            print("[Warnig]: No docker credential was provided.")
            return
        if expected_error_message == "":
            expected_error_message = None
        if registry == "docker":
            registry = None
        try:
            ret = self.DCLIENT.login(registry = registry, username=username, password=password)
        except Exception as err:
            print( "Docker image pull catch exception")
            err_message = str(err)
            if expected_error_message is None:
                raise Exception(r" Docker pull image failed")
        else:
            print("Docker image login did not catch exception")
            err_message = ret
        finally:
            if expected_error_message is None:
                if "error".lower() in str(err_message).lower():
                    raise Exception(r" It's was not suppose to catch error when login registry")

            elif str(err_message).lower().find(expected_error_message.lower()) < 0:
                raise Exception(r" err message is different from expected error message")
            else:
                print(r"Docker image login got expected error message")

    def docker_image_pull(self, image, tag = None, expected_error_message = None, is_clean_all_img = True):
        ret = ""
        err_message = ""
        _tag = tag if tag is not None else "latest"
        if expected_error_message == "":
            expected_error_message = None
        try:
            ret = self.DCLIENT.pull(f'{image}:{_tag}')
        except Exception as err:
            print("Docker image pull catch exception:", err)
            err_message = str(err)
            if expected_error_message is None:
                raise Exception(f" Docker pull image {image} failed, error is [{str(err)}]")
        else:
            print("Docker image pull did not catch exception and return message is:", ret)
            err_message = ret
        finally:
            if expected_error_message is None:
                if "error".lower() in str(err_message).lower():
                    raise Exception(
                        f" It's was not suppose to catch error when pull image {image}, return message is [{err_message}]"
                    )
            elif str(err_message).lower().find(expected_error_message.lower()) < 0:
                raise Exception(
                    f" Failed to catch error [{expected_error_message}] when pull image {image}, return message: {err_message}"
                )
            else:
                print(f"Docker image pull got expected error message:{expected_error_message}")
            if is_clean_all_img:
                docker_image_clean_all()

    def docker_image_tag(self, image, harbor_registry, tag = None):
        _tag = base._random_name("tag")
        if tag is not None:
            _tag = tag
        ret = ""
        try:
            ret = self.DCLIENT.tag(image, harbor_registry, _tag, force=True)
            print("Docker image tag commond return:", ret)
            return harbor_registry, _tag
        except docker.errors.APIError as err:
            raise Exception(f" Docker tag image {image} failed, error is [{str(err)}]")

    def docker_image_push(self, harbor_registry, tag, expected_error_message = None):
        ret = ""
        err_message = ""
        docker_images_all_list()
        if expected_error_message == "":
            expected_error_message = None
        try:
            ret = self.DCLIENT.push(harbor_registry, tag)
        except Exception as err:
            print("Docker image push catch exception:", err)
            err_message = str(err)
            if expected_error_message is None:
                raise Exception(f" Docker push image {image} failed, error is [{str(err)}]")
        else:
            print("Docker image push did not catch exception and return message is:", ret)
            err_message = ret
        finally:
            if expected_error_message is None:
                if "error".lower() in str(err_message).lower():
                    raise Exception(
                        f" It's was not suppose to catch error when push image {harbor_registry}, return message is [{err_message}]"
                    )
            elif str(err_message).lower().find(expected_error_message.lower()) < 0:
                raise Exception(
                    f" Failed to catch error [{expected_error_message}] when push image {harbor_registry}, return message: {err_message}"
                )
            else:
                print(f"Docker image push got expected error message:{expected_error_message}")
        docker_images_all_list()

    def docker_image_build(self, harbor_registry, tags=None, size=1, expected_error_message = None, clean_images=True):
        ret = ""
        err_message = ""
        docker_images_all_list()
        try:
            baseimage = BASE_IMAGE['name'] + ":" + BASE_IMAGE['tag']
            if not self.DCLIENT.images(name=baseimage):
                print(f"Docker load is triggered when building {harbor_registry}")
                docker_load_image(BASE_IMAGE_ABS_PATH_NAME)
                docker_images_all_list()
            c = self.DCLIENT.create_container(
                image=baseimage,
                command=f'dd if=/dev/urandom of=test bs=1M count={size}',
            )
            self.DCLIENT.start(c)
            self.DCLIENT.wait(c)
            if not tags:
                tags=['latest']
            firstrepo = f"{harbor_registry}:{tags[0]}"
            #self.DCLIENT.commit(c, firstrepo)
            self.DCLIENT2.containers.get(c).commit(harbor_registry, tags[0])
            for tag in tags[1:]:
                repo = f"{harbor_registry}:{tag}"
                self.DCLIENT.tag(firstrepo, repo)
            for tag in tags:
                repo = f"{harbor_registry}:{tag}"
                ret = self.DCLIENT.push(repo)
                print("docker_image_push ret:", ret)
                print(f"build image {repo} with size {size}")
            self.DCLIENT.remove_container(c)
        except Exception as err:
            print("Docker image build catch exception:", err)
            err_message = str(err)
            if expected_error_message is None:
                raise Exception(
                    f" Docker push image {harbor_registry} failed, error is [{str(err)}]"
                )
        else:
            print("Docker image build did not catch exception and return message is:", ret)
            err_message = ret
        finally:
            if expected_error_message is None:
                if "error".lower() in str(err_message).lower():
                    raise Exception(
                        f" It's was not suppose to catch error when build image {harbor_registry}, return message is [{err_message}]"
                    )
            elif str(err_message).lower().find(expected_error_message.lower()) < 0:
                raise Exception(
                    f" Failed to catch error [{expected_error_message}] when build image {harbor_registry}, return message: {err_message}"
                )
            else:
                print(
                    f"Docker image build got expected error message: {expected_error_message}"
                )
            if clean_images:
                docker_image_clean_all()
