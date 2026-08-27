#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""conversation and plan message definition"""

import os
import re
import time
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger, interface_logger
from jiuwen.common.security.cryptor import Crypt
from pymilvus import MilvusClient, DataType

from .base_vector import BaseVector
from .vector_db_factory import VectorDbFactory
from ..config import VectorTypeEnum, MilvusConfig, LongMemoryConfig

HTTP_TIMEOUT = os.getenv("HTTP_TIMEOUT", "15")

# 每个用户没工作流的摘要个数大于门限多少时开始总结
SUMMARY_OFFSET = 5


def interface_log(operate):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            result = func(*args, **kwargs)

            end_time = time.perf_counter()
            duration = round((end_time - start_time) * 1000)
            if interface_logger.isEnabledFor(logging.INFO):
                interface_logger.info(f"milvus_vector|{operate}|{duration}")
            return result

        return wrapper

    return decorator


class MilvusVector(BaseVector):
    client: MilvusClient
    config: MilvusConfig
    input_keys = []
    output_keys = []

    @classmethod
    def register(cls):
        if LongMemoryConfig.get_config().vector_type != VectorTypeEnum.MILVUS:
            return
        cls.save_config()
        with ThreadPoolExecutor() as executor:
            executor.submit(cls.async_register)

    @classmethod
    def save_config(cls):
        cls.config = LongMemoryConfig.get_config().milvus_config
        cls._check_config()
        cls._update_auth()
        cls.input_keys = cls.config.input_field.split(".")
        cls.output_keys = re.findall(r"[^.\[\]]+", cls.config.output_field)

    @classmethod
    @interface_log(operate="register")
    def async_register(cls):
        """
        异步加载数据库
        """
        logger.info("start init Milvus")
        cls.client = MilvusClient(cls.config.local_db_path)
        if cls.config.collection_name not in cls.client.list_collections():
            # 创建数据库
            try:
                cls.init_collection()
            except Exception:
                import traceback

                logger.error(traceback.format_exc())
                return
        VectorDbFactory.register_vector(cls)
        logger.info("end init Milvus")

    @classmethod
    @interface_log(operate="init")
    def init_collection(cls):
        schema = cls.client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field(
            "vector",
            DataType.FLOAT_VECTOR,
            dim=LongMemoryConfig.get_config().milvus_config.dim,
        )
        schema.add_field("user_id", DataType.VARCHAR, max_length=128)
        schema.add_field("workflow_id", DataType.VARCHAR, max_length=128)
        schema.add_field("text", DataType.VARCHAR, max_length=1000, mmap_enabled=True)
        schema.add_field("timestamp", DataType.INT64)

        index_params = cls.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
            index_name="vector_index",
        )
        index_params.add_index(
            field_name="timestamp", index_type="INVERTED", index_name="timestamp_index"
        )
        index_params.add_index(
            field_name="user_id", index_type="INVERTED", index_name="user_id_index"
        )
        index_params.add_index(
            field_name="workflow_id",
            index_type="INVERTED",
            index_name="workflow_id_index",
        )

        cls.client.create_collection(
            cls.config.collection_name,
            schema=schema,
            index_params=index_params,
            metric_type="COSINE",
        )

    @classmethod
    @interface_log(operate="search")
    def search(
        cls,
        query: str,
        condition: str,
        recall_threshold: float,
        recall_num: int,
        *args,
        **kwargs,
    ) -> list:
        user_id = kwargs.get("user_id")
        workflow_id = kwargs.get("workflow_id")
        if not (user_id and workflow_id):
            return []
        embedding = cls._query_embedding(query)
        if not embedding:
            return []
        results = cls.client.search(
            collection_name=cls.config.collection_name,
            data=[embedding],
            limit=recall_num,
            # search用不了参数替换，会有错误日志
            filter=f'user_id == "{user_id}" and workflow_id == "{workflow_id}"',
            output_fields=["text"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
        )
        return (
            [
                {"content": hit["entity"]["text"]}
                for hit in results[0]
                if hit["distance"] >= recall_threshold
            ]
            if results
            else []
        )

    @classmethod
    @interface_log(operate="save")
    def save(cls, file_data: list, **kwargs):
        user_id = kwargs.get("category")
        workflow_id = kwargs.get("tags")[0] if kwargs.get("tags") else ""
        if not (user_id and workflow_id):
            return
        data = [cls._build_record(x, user_id, workflow_id) for x in file_data]
        cls.client.insert(cls.config.collection_name, [x for x in data if x])

    @classmethod
    @interface_log(operate="remove")
    def remove(cls, **kwargs):
        workflow_id = kwargs.get("tags")[0] if kwargs.get("tags") else ""
        if not workflow_id:
            return
        ret = cls.client.delete(
            cls.config.collection_name, filter=f'workflow_id == "{workflow_id}"'
        )
        logger.info(f"remove {len(ret)}")

    @classmethod
    def _build_record(cls, text, user_id, workflow_id):
        embedding = cls._query_embedding(text)
        if not embedding:
            return None
        return {
            "text": text,
            "vector": embedding,
            "user_id": user_id,
            "workflow_id": workflow_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }

    @classmethod
    def _check_config(cls):
        if not (
            cls.config.model_url and cls.config.input_field and cls.config.output_field
        ):
            raise AttributeError("milvus config need embedding model")

    @classmethod
    def _update_auth(cls):
        if not cls.config.auth_header_value:
            return
        cls.config.auth_header_value = Crypt.decrypt(cls.config.auth_header_value)

    @classmethod
    def _query_embedding(cls, text):
        headers = {"Content-Type": "application/json"} | (
            {cls.config.auth_header_name: cls.config.auth_header_value}
            if cls.config.auth_header_name
            else {}
        )

        res = requests.post(
            url=cls.config.model_url,
            json=cls._build_embedding_input(text),
            headers=headers,
            verify=ModelUtil.parse_ssl_verify(),
            stream=False,
            timeout=HTTP_TIMEOUT,
        )
        return cls._read_embedding_data(res.json()) if res.status_code == 200 else None

    @classmethod
    def _build_embedding_input(cls, text):
        nested = {}
        current = nested
        for key in cls.input_keys[:-1]:
            current[key] = {}
            current = current[key]
        current[cls.input_keys[-1]] = text
        return nested

    @classmethod
    def _read_embedding_data(cls, response):
        current = response
        for key in cls.output_keys:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, list):
                current = current[int(key)]
            else:
                return current
        return current

    @classmethod
    @interface_log(operate="pop_old_data")
    def pop_old_data(cls, user_id, workflow_id):
        # milvus查询不支持order_by，只能先查出来再排序
        total_records = cls.client.query(
            collection_name=cls.config.collection_name,
            limit=1000,
            # query用不了参数替换，会有错误日志
            filter=f'user_id == "{user_id}" and workflow_id == "{workflow_id}"',
            output_fields=["id", "timestamp"],
        )
        total_records = sorted(total_records, key=lambda x: x["timestamp"])
        logger.info(
            f"user_id {user_id}, workflow_id {workflow_id}, vector data total length {len(total_records)}"
        )
        if len(total_records) <= cls.config.max_summary_num + SUMMARY_OFFSET:
            return []
        ids = [
            hit["id"]
            for hit in total_records[: len(total_records) - cls.config.max_summary_num]
        ]
        results = cls.client.query(
            collection_name=cls.config.collection_name,
            ids=ids,
            output_fields=["id", "text"],
        )
        del_ret = cls.client.delete(collection_name=cls.config.collection_name, ids=ids)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"pop ids {ids}, ret {del_ret}")
        return [hit["text"] for hit in results]

    @classmethod
    async def asearch(
        cls,
        query: str,
        condition: str,
        recall_threshold: float,
        recall_num: int,
        *args,
        **kwargs,
    ) -> list:
        return cls.search(
            query, condition, recall_threshold, recall_num, *args, **kwargs
        )
