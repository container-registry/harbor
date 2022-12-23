#!/usr/bin/env python
# -*- coding:utf-8 -*-
# bug-report: feilengcui008@gmail.com

""" api for docker registry """

import urllib2
import urllib
import json
import base64


class RegistryException(Exception):
    """ registry api related exception """
    pass


class RegistryApi(object):
    """ interact with docker registry and harbor """
    def __init__(self, username, password, registry_endpoint):
        self.username = username
        self.password = password
        self.basic_token = base64.encodestring(f"{str(username)}:{str(password)}")[:-1]
        self.registry_endpoint = registry_endpoint.rstrip('/')
        auth = self.pingRegistry(f"{self.registry_endpoint}/v2/_catalog")
        if auth is None:
            raise RegistryException("get token realm and service failed")
        self.token_endpoint = auth[0]
        self.service = auth[1]

    def pingRegistry(self, registry_endpoint):
        """ ping v2 registry and get realm and service """
        headers = {}
        try:
            res = urllib2.urlopen(registry_endpoint)
        except urllib2.HTTPError as e:
            headers = e.hdrs.dict
        try:
            (realm, service, _) = headers['www-authenticate'].split(',')
            return (realm[14:-1:], service[9:-1])
        except Exception as e:
            return None

    def getBearerTokenForScope(self, scope):
        """ get bearer token from harbor """
        payload = urllib.urlencode({'service': self.service, 'scope': scope})
        url = f"{self.token_endpoint}?{payload}"
        req = urllib2.Request(url)
        req.add_header('Authorization', f'Basic {self.basic_token}')
        try:
            response = urllib2.urlopen(req)
            return json.loads(response.read())["token"]
        except Exception as e:
            return None

    def getRepositoryList(self, n=None):
        """ get repository list """
        scope = "registry:catalog:*"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            return None
        url = f"{self.registry_endpoint}/v2/_catalog"
        if n is not None:
            url = f"{url}?n={str(n)}"
        req = urllib2.Request(url)
        req.add_header('Authorization', f'Bearer {bear_token}')
        try:
            response = urllib2.urlopen(req)
            return json.loads(response.read())
        except Exception as e:
            return None

    def getTagList(self, repository):
        """ get tag list for repository """
        scope = f"repository:{repository}:pull"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            return None
        url = f"{self.registry_endpoint}/v2/{repository}/tags/list"
        req = urllib2.Request(url)
        req.add_header('Authorization', f'Bearer {bear_token}')
        try:
            response = urllib2.urlopen(req)
            return json.loads(response.read())
        except Exception as e:
            return None

    def getManifest(self, repository, reference="latest", v1=False):
        """ get manifest for tag or digest """
        scope = f"repository:{repository}:pull"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            return None
        url = f"{self.registry_endpoint}/v2/{repository}/manifests/{reference}"
        req = urllib2.Request(url)
        req.get_method = lambda: 'GET'
        req.add_header('Authorization', f'Bearer {bear_token}')
        req.add_header('Accept', 'application/vnd.docker.distribution.manifest.v2+json')
        if v1:
            req.add_header('Accept', 'application/vnd.docker.distribution.manifest.v1+json')
        try:
            response = urllib2.urlopen(req)
            return json.loads(response.read())
        except Exception as e:
            return None

    def existManifest(self, repository, reference, v1=False):
        """ check to see it manifest exist """
        scope = f"repository:{repository}:pull"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            raise RegistryException("manifestExist failed due to token error")
        url = f"{self.registry_endpoint}/v2/{repository}/manifests/{reference}"
        req = urllib2.Request(url)
        req.get_method = lambda: 'HEAD'
        req.add_header('Authorization', f'Bearer {bear_token}')
        req.add_header('Accept', 'application/vnd.docker.distribution.manifest.v2+json')
        if v1:
            req.add_header('Accept', 'application/vnd.docker.distribution.manifest.v1+json')
        try:
            response = urllib2.urlopen(req)
            return (True, response.headers.dict["docker-content-digest"])
        except Exception as e:
            return (False, None)

    def deleteManifest(self, repository, reference):
        """ delete manifest by tag """
        (is_exist, digest) = self.existManifest(repository, reference)
        if not is_exist:
            raise RegistryException("manifest not exist")
        scope = f"repository:{repository}:pull,push"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            raise RegistryException("delete manifest failed due to token error")
        url = f"{self.registry_endpoint}/v2/{repository}/manifests/{digest}"
        req = urllib2.Request(url)
        req.get_method = lambda: 'DELETE'
        req.add_header('Authorization', f'Bearer {bear_token}')
        try:
            urllib2.urlopen(req)
        except Exception as e:
            return False
        return True

    def getManifestWithConf(self, repository, reference="latest"):
        """ get manifest for tag or digest """
        manifest = self.getManifest(repository, reference)
        if manifest is None:
            raise RegistryException(f"manifest for {repository} {reference} not exist")
        config_digest = manifest["config"]["digest"]
        scope = f"repository:{repository}:pull"
        bear_token = self.getBearerTokenForScope(scope)
        if bear_token is None:
            return None
        url = f"{self.registry_endpoint}/v2/{repository}/blobs/{config_digest}"
        req = urllib2.Request(url)
        req.get_method = lambda: 'GET'
        req.add_header('Authorization', f'Bearer {bear_token}')
        req.add_header('Accept', 'application/vnd.docker.distribution.manifest.v2+json')
        try:
            response = urllib2.urlopen(req)
            manifest["configContent"] = json.loads(response.read())
            return manifest
        except Exception as e:
            return None
