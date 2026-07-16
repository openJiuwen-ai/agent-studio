#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
cloud map base
"""

import json
import os
from collections import namedtuple
from http.client import HTTPException
from json import JSONDecodeError
from pathlib import Path
from urllib.parse import ParseResult, scheme_chars
from urllib.parse import quote
from urllib.parse import urlencode

import requests
from agent_builder.common.logging.base import logger
from agent_builder.common.security.cloudmap.common import retry
from agent_builder.common.security.cloudmap.common import timed_lru_cache

try:
    from pystssdk import StsAuthRequest
    from pystssdk import sts_api
except ImportError:
    StsAuthRequest = None
    sts_api = None

SYS_ENV_PREFIX = "nuwa.cloudmap."
SERVER_ADDR = "serverAddr"
NAMESPACE_NAME = "namespaceName"

RESOURCE_TYPE_MICROSERVICE = "MICROSERVICE"
RESOURCE_TYPE_MIDDLEWARE = "MIDDLEWARE"
DEFAULT_CLUSTER_NAME = "default"
DEFAULT_MIDDLEWARE_INSTANCE_ID = "default"

CloudMapResource = namedtuple(
    "CloudMapResource",
    ["namespace", "serviceName", "resourceType", "resourceName", "clusterName"],
)

CloudMapMiddlewareParam = namedtuple(
    "CloudMapMiddlewareParam",
    ["resourceOwnerNamespace", "resourceOwnerService", "middlewareName", "cluster"],
)

CLOUD_MAP_RESOURCE_INSTANCE_FIELDS = [
    "instanceId",
    "ephemeral",
    "status",
    "health",
    "endPoints",
    "version",
    "host",
    "port",
    "hostName",
    "ipAddr",
    "dataCenter",
    "gray",
    "tag",
    "regTimestamp",
    "modTimestamp",
    "properties",
]
CloudMapResourceInstance = namedtuple(
    "CloudMapResourceInstance",
    CLOUD_MAP_RESOURCE_INSTANCE_FIELDS,
    defaults=(None,) * len(CLOUD_MAP_RESOURCE_INSTANCE_FIELDS),
)

CLOUD_MAP_HEALTH_FIELDS = ["healthMode", "checkType", "checkPath", "interval", "times"]
CloudMapHealth = namedtuple(
    "CloudMapHealth",
    CLOUD_MAP_HEALTH_FIELDS,
    defaults=(None,) * len(CLOUD_MAP_HEALTH_FIELDS),
)

CLOUD_MAP_DATA_CENTER_INFO = ["name", "region", "availableZone"]
CloudMapDataCenterInfo = namedtuple(
    "CloudMapDataCenterInfo",
    CLOUD_MAP_DATA_CENTER_INFO,
    defaults=(None,) * len(CLOUD_MAP_DATA_CENTER_INFO),
)

CLOUD_MAP_RESOURCE_INSTANCES_FIELDS = [
    "revision",
    "resource",
    "instances",
    "permission",
    "credentials",
]
CloudMapResourceInstances = namedtuple(
    "CloudMapResourceInstances",
    CLOUD_MAP_RESOURCE_INSTANCES_FIELDS,
    defaults=(None,) * len(CLOUD_MAP_RESOURCE_INSTANCES_FIELDS),
)

CLOUD_MAP_CLUSTER_INFO_FIELDS = ["properties", "permission"]
CloudMapClusterInfo = namedtuple(
    "CloudMapResourceInstances",
    CLOUD_MAP_CLUSTER_INFO_FIELDS,
    defaults=(None,) * len(CLOUD_MAP_CLUSTER_INFO_FIELDS),
)

HttpParams = namedtuple("HttpParams", ["method", "path", "query", "headers", "body"])

TARGET_SERVICE_NAME = "WiseCloudNuwaService"

TARGET_MICRO_SERVICE_NAME = "WiseCloudNuwaMapService"

CURRENT_CLOUD_MAP_CLIENT_VERSION = "0.0.1.100"

CACHE_TYPE_INSTANCES = "instances"

CACHE_DEFAULT_SECONDS = 3600

CACHE_DEFAULT_NUMS = 128

SAFE_BASE_DIRS = [
    Path.home(),  # 用户主目录
    Path("/tmp"),  # 临时目录
    Path("/var/tmp"),  # 系统临时目录
]


def get_cloud_map_client(properties):
    """get_cloud_map_client"""
    return CloudMapClient(properties)


class CloudMapClient(object):
    polling_timeout = 300
    polling_delay = 5
    retry_times = 3
    retry_delay = 3
    wait_timeout_mills = 3

    _instance = None
    _cache_seconds = CACHE_DEFAULT_SECONDS
    _cache_nums = CACHE_DEFAULT_NUMS

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CloudMapClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, properties):
        endpoint = os.getenv(f"{SYS_ENV_PREFIX}{SERVER_ADDR}")
        namespace = os.getenv(f"{SYS_ENV_PREFIX}{NAMESPACE_NAME}")
        if endpoint is None and self._properties_check(
            properties=properties, value=SERVER_ADDR
        ):
            raise Exception(f"{SERVER_ADDR} not found in env variable or properties")
        if endpoint is None:
            endpoint = properties[SERVER_ADDR]
        if endpoint.find(",") != -1:
            raise Exception("multi address not supported")
        if namespace is None and self._properties_check(
            properties=properties, value=NAMESPACE_NAME
        ):
            raise Exception(f"{NAMESPACE_NAME} not found in env variable or properties")
        if namespace is None:
            namespace = properties[NAMESPACE_NAME]
        if self._initialized:
            return

        endpoint_obj = self._url_parse(endpoint)
        self.scheme = "https" if endpoint_obj.scheme is None else endpoint_obj.scheme
        self.host = "" if endpoint_obj.hostname is None else endpoint_obj.hostname
        self.ip = None
        self.port = endpoint_obj.port
        if self.port is None:
            self.port = 80 if self.scheme == "http" else 443

        self._init_self_resource(namespace)
        self._init_cache(properties)
        self._init_client()
        self._initialized = True

    @staticmethod
    def _url_parse(url: str) -> ParseResult:
        """parse url"""
        for b in ["\t", "\r", "\n"]:
            url = url.replace(b, "")
        colon_loc = url.find(":")
        scheme, netloc, params, query, fragment = "", "", "", "", ""
        if colon_loc > 0:
            for char in url[:colon_loc]:
                if char not in scheme_chars:
                    break
            else:
                scheme, url = url[:colon_loc].lower(), url[colon_loc + 1 :]
        if scheme not in ["http", "https"]:
            raise ValueError("CloudMap endpoint scheme must be http or https.")
        url_parse = url.split("//")
        if len(url_parse) != 2:
            raise Exception("parse url error")
        _, netloc = url_parse

        return ParseResult(scheme, netloc, "", params, query, fragment)

    @staticmethod
    def _properties_check(properties, value):
        """_properties_check"""
        if properties is None or value not in properties or properties[value] == "":
            return True
        return False

    @staticmethod
    def _check_resource_valid(resource):
        """_check_resource_valid"""
        if resource.namespace is None or resource.namespace == "":
            raise Exception("namespace name is None")
        if resource.serviceName is None or resource.serviceName == "":
            raise Exception("service name is None")
        if resource.resourceType is None or resource.resourceType == "":
            raise Exception("resource type is None")
        if resource.resourceName is None or resource.resourceName == "":
            raise Exception("resource name is None")
        if resource.clusterName is None or resource.clusterName == "":
            raise Exception("cluster name is None")

    @staticmethod
    def _get_resource_id(resource):
        """_get_resource_id"""
        return (
            f"{resource.namespace}@@{resource.serviceName}@@{resource.resourceType}@@"
            f"{resource.resourceName}@@{resource.clusterName}"
        )

    @staticmethod
    def _deserialize_cloud_map_resource_instance(json_str):
        """_deserialize_cloud_map_resource_instance"""
        ret = json.loads(json_str)
        instances = list()
        for element in ret["instances"]:
            instance = (
                {"properties": element["properties"]}
                if "properties" in element
                else {"properties": dict()}
            )
            for k, v in element.items():
                if k == "properties":
                    continue
                if k not in CloudMapResourceInstance._fields:
                    instance["properties"][k] = v
                else:
                    if k == "health":
                        instance[k] = CloudMapHealth(**v)
                    else:
                        instance[k] = v
            instances.append(CloudMapResourceInstance(**instance))
        return {
            "revision": ret["revision"],
            "instances": instances,
            "permission": ret["permission"],
        }

    def get_self_resource(self):
        """get_self_resource"""
        return self.self_resource

    def get_middleware_client(self):
        """get_middleware_client"""
        return self.middleware_client

    def get_service_discovery_client(self):
        """get_service_discovery_client"""
        raise Exception("The discovery client is not supported!")

    @timed_lru_cache(seconds=_cache_seconds, maxsize=_cache_nums)
    def find_instances(self, resource, revision):
        """find_instances"""

        def _find_instances(res):
            method = "GET"
            base_path = "/nuwa/map/v1/instances"
            path = quote(
                f"{base_path}/{res.namespace}/{res.serviceName}/"
                f"{res.resourceType}/{res.resourceName}/{res.clusterName}"
            )

            headers = dict()
            headers["Host"] = self.host
            headers["Content-Type"] = "application/json"
            headers["x-nuwa-map-self-namespace"] = self.self_resource.namespace
            headers["x-nuwa-map-service"] = self.self_resource.serviceName
            headers["x-nuwa-map-self-cluster"] = self.self_resource.clusterName
            headers["x-nuwa-map-sdk-version"] = CURRENT_CLOUD_MAP_CLIENT_VERSION

            params = dict()
            params["revision"] = revision

            try:
                resp = self._rest_api(method, path, params, headers, None)
            except Exception as e:
                raise e

            if resp.status_code == 404:
                logger.error(f"find instances failed: status is {resp.status_code}")
                return None
            if resp.status_code // 200 != 1:
                logger.error(f"find instances failed: status is {resp.status_code}")
                raise Exception(f"find instances failed: status is {resp.status_code}")
            resp_body = resp.content
            try:
                ret = CloudMapClient._deserialize_cloud_map_resource_instance(resp_body)
                ret["resource"] = resource
            except JSONDecodeError as e:
                logger.error(
                    f"find instances {self._get_resource_id(resource)} decode response failed!"
                )
                raise Exception(
                    f"find instances {self._get_resource_id(resource)} decode response failed!"
                ) from e
            if (
                ret["revision"] is None
                or ret["instances"] is None
                or len(ret["instances"]) == 0
            ):
                logger.error(
                    f"find instances {self._get_resource_id(resource)} read content failed!"
                )
                raise Exception(
                    f"find instances {self._get_resource_id(resource)} read content failed!"
                )
            return CloudMapResourceInstances(**ret)

        self._check_resource_valid(resource)
        return _find_instances(resource)

    def _init_self_resource(self, namespace_name):
        """_init_self_resource"""
        sts_whoami = sts_api.whoami()
        service_name = sts_whoami.get("service")
        resource_type = RESOURCE_TYPE_MICROSERVICE
        resource_name = sts_whoami.get("micro_service")
        cluster_name = DEFAULT_CLUSTER_NAME

        self.self_resource = CloudMapResource(
            namespace_name, service_name, resource_type, resource_name, cluster_name
        )

    def _init_cache(self, properties):
        """_init_cache"""
        if (
            properties is not None
            and "cache_dir" in properties
            and properties["cache_dir"] != ""
        ):
            cache_dir = properties["cache_dir"]
            try:
                cache_dir_path = Path(cache_dir).resolve()
            except (OSError, IOError) as e:
                raise ValueError(
                    f"Invalid or inaccessible cache_dir: {cache_dir} by exception {e}"
                ) from e
            if not any(cache_dir_path.is_relative_to(b) for b in SAFE_BASE_DIRS):
                raise ValueError(
                    f"Cache directory must be within safe directories: {SAFE_BASE_DIRS}"
                )
            self.cache_dir = str(cache_dir_path)
        else:
            cache_path = (
                Path.home()
                / ".numa"
                / "map_py"
                / self.self_resource.namespace
                / self.self_resource.serviceName
                / self.self_resource.resourceName
                / self.self_resource.clusterName
                / CACHE_TYPE_INSTANCES
            )
            if not cache_path.exists():
                cache_path.mkdir(mode=0o600, parents=True)

            self.cache_dir = str(cache_path)

    def _init_client(self):
        """_init_client"""
        self.middleware_client = MiddlewareClient(self._instance)
        self.service_discovery_client = None

    def _rest_api(self, method, path, query, headers, body):
        """_rest_api"""
        return self._rest_api_with_timeout(method, path, query, headers, body)

    def _rest_api_with_timeout(self, method, path, query, headers, body):
        """_rest_api_with_timeout"""
        return self._execute_rest_api(method, path, query, headers, body)

    def _execute_rest_api(self, req_method, req_path, req_query, req_headers, req_body):
        """_execute_rest_api"""

        @retry(
            retry_times=CloudMapClient.retry_times,
            retry_delay=CloudMapClient.retry_delay,
            retry_exceptions=(HTTPException,),
        )
        def _execute_rest_api(method, path, query, headers, body):
            host = self.host if self.port in (80, 443) else f"{self.host}:{self.port}"
            path_and_query = path if query is None else f"{path}?{urlencode(query)}"
            url = f"{self.scheme}://{host}{path_and_query}"
            try:
                # for debug test HTTPConnection.debuglevel = 1
                req = requests.Request(
                    method=method, url=url, headers=headers, data=body
                )
                prepared_req = req.prepare()
                auth_req = (
                    StsAuthRequest.builder()
                    .RequestsHelper.from_request(prepared_req)
                    .append_header(headers)
                )
                token = auth_req.build().compute_headers(
                    TARGET_SERVICE_NAME, TARGET_MICRO_SERVICE_NAME
                )
                prepared_req.headers.update(token)
                prepared_req.headers.update({"Content-Type": "application/json"})
                resp = requests.Session().send(
                    prepared_req, timeout=CloudMapClient.wait_timeout_mills
                )
                if resp is None:
                    raise HTTPException("can't get HTTPResponse object!")
                if resp.status_code // 200 >= 2:
                    raise HTTPException(
                        f"HTTPResponse status is {resp.status_code}, need to retry!"
                    )
                return resp
            except (OSError, HTTPException) as err:
                raise HTTPException(
                    "HTTP request execution failed: unable to connect or receive response from remote service"
                ) from err
            except Exception as err:
                raise Exception(
                    "Request execution failed: an unexpected error occurred while processing the request"
                ) from err

        return _execute_rest_api(
            method=req_method,
            path=req_path,
            query=req_query,
            headers=req_headers,
            body=req_body,
        )


class MiddlewareClient(object):
    def __init__(self, cloud_map_client):
        self.cloud_map_client = cloud_map_client

    def find_cluster(self, middleware_param, revision):
        """find_cluster"""
        check_valid = True
        if (
            middleware_param.middlewareName is None
            or middleware_param.middlewareName == ""
        ):
            check_valid = False
        if middleware_param.cluster is None or middleware_param.cluster == "":
            check_valid = False
        if not check_valid:
            raise Exception("middleware name or cluster name is None")
        if (
            middleware_param.resourceOwnerNamespace is None
            or middleware_param.resourceOwnerNamespace == ""
        ):
            middleware_param.resourceOwnerNamespace = (
                self.cloud_map_client.get_self_resource().namespace
            )
        if (
            middleware_param.resourceOwnerService is None
            or middleware_param.resourceOwnerService == ""
        ):
            middleware_param.resourceOwnerService = (
                self.cloud_map_client.get_self_resource().serviceName
            )
        resource = CloudMapResource(
            middleware_param.resourceOwnerNamespace,
            middleware_param.resourceOwnerService,
            RESOURCE_TYPE_MIDDLEWARE,
            middleware_param.middlewareName,
            middleware_param.cluster,
        )
        resource_instances = self.cloud_map_client.find_instances(resource, revision)
        return CloudMapClusterInfo(
            **{
                "properties": resource_instances.instances[0].properties,
                "permission": resource_instances.permission,
            }
        )
