#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
cloud map rainbow
"""

import json

from agent_builder.common.security.cloudmap.base import CloudMapMiddlewareParam
from agent_builder.common.security.cloudmap.base import get_cloud_map_client

try:
    from pystssdk import AesCryptor
    from pystssdk import sts_api
except ImportError:
    AesCryptor = None
    sts_api = None


class DataSourceAccount(object):
    """DataSourceAccount"""

    def __init__(self, user_name, password):
        self.user_name = user_name
        self.password = password


class ConnectionPool(object):
    def __init__(self, min_idle, max_active, connection_properties):
        self.min_idle = min_idle
        self.max_active = max_active
        self.connection_properties = connection_properties


class DataSourceAddress(object):
    def __init__(self, ip_list, db_type, db_weight):
        self.ip_list = ip_list
        self.db_type = db_type
        self.db_weight = db_weight


class DataSourceInfo(object):
    def __init__(self, account, connection_pool, addresses, meta_data):
        self.account = account
        self.connection_pool = connection_pool
        self.addresses = addresses
        self.meta_data = meta_data


def _get_connection_pool(conf) -> ConnectionPool:
    """get_connection_pool"""
    connection_pool = ConnectionPool(
        conf["minIdle"] if "minIdle" in conf else None,
        conf["maxActive"] if "maxActive" in conf else None,
        conf["connectionProperties"] if "connectionProperties" in conf else None,
    )
    return connection_pool


def _get_account(conf) -> DataSourceAccount:
    """get account"""
    password = None
    if "encStsPasswd" in conf and conf["encStsPasswd"] != "":
        kek_cryptor = AesCryptor.builder().with_service_kek().build()
        password = kek_cryptor.decrypt().from_hex(conf["encStsPasswd"]).to_raw_str()
    account = DataSourceAccount(
        conf["userName"] if "userName" in conf else None, password
    )
    return account


def get_data_source_info(properties, cluster_name):
    """get_data_source_info"""
    cloud_map_client = get_cloud_map_client(properties)
    middleware_client = cloud_map_client.get_middleware_client()
    resource = CloudMapMiddlewareParam(
        cloud_map_client.get_self_resource().namespace,
        sts_api.whoami().get("service"),
        "rainbow",
        cluster_name,
    )
    cluster_info = middleware_client.find_cluster(resource, "")
    if "conf" not in cluster_info.permission:
        raise Exception(
            "SDK configuration format error: "
            "missing one or more required configuration fields in cluster_info.permission."
        )
    conf = json.loads(cluster_info.permission["conf"])
    connection_pool = _get_connection_pool(conf=conf)
    if (
        "condition" not in cluster_info.properties
        or "metadata" not in cluster_info.properties
    ):
        raise Exception(
            "SDK configuration format error: "
            "missing one or more required configuration fields in cluster_info.permission."
        )
    condition = json.loads(cluster_info.properties["condition"])
    addresses = []
    for cond in condition:
        address = DataSourceAddress(
            cond["ipList"] if "ipList" in cond else None,
            cond["dbType"] if "dbType" in cond else None,
            cond["dbWeight"] if "dbWeight" in cond else None,
        )
        addresses.append(address)
    account = _get_account(conf=conf)
    return DataSourceInfo(
        account,
        connection_pool,
        addresses,
        json.loads(cluster_info.properties["metadata"]),
    )
