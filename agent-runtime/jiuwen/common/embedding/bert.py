#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Text embedding and ranking module"""

import json
import os
import time

import requests
from jiuwen.common.config import config
from jiuwen.common.configs.env_constants import (
    PLUGIN_RECALL_APP_CODE_KEY,
    PLUGIN_SSL_EMB_CERT_KEY,
    PLUGIN_RECALL_EMB_SERVICE_URL_KEY,
    PLUGIN_RECALL_EMB_DIM_KEY,
)
from jiuwen.common.log.base import logger
from jiuwen.common.security.cryptor import Crypt
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.plugin.common import exception
from jiuwen.plugin.common.constant import REQUEST_TIME_OUT

recall_config = config.get("plugin", dict()).get("recall", dict())


def get_cipher(cipher: str = ""):
    """decrypt cipher"""
    return Crypt().decrypt(cipher) if cipher else ""


class TextEmbeddingService:
    """Class for text embedding"""

    def __init__(self):
        self.emb_dim = int(
            os.environ.get(PLUGIN_RECALL_EMB_DIM_KEY, recall_config.get("emb_dim"))
        )
        self.mock_result = [0 if i != 0 else 1 for i in range(self.emb_dim)]
        self.api_url = os.environ.get(
            PLUGIN_RECALL_EMB_SERVICE_URL_KEY, recall_config.get("emb_service_url")
        )
        self.app_code = get_cipher(os.environ.get(PLUGIN_RECALL_APP_CODE_KEY, ""))
        self.ssl_check = True
        ssl_emb_cert = os.environ.get(PLUGIN_SSL_EMB_CERT_KEY)
        if ssl_emb_cert:
            ssl_emb_cert = safe_json_loads(ssl_emb_cert, ssl_emb_cert)
            if not isinstance(ssl_emb_cert, str) and not isinstance(ssl_emb_cert, bool):
                raise exception.PluginCommonException(
                    code=StatusCode.PLUGIN_PARAMS_CHECK_FAILED,
                    message="plugin ssl emb cert is not bool or str",
                )
            self.ssl_check = ssl_emb_cert

    def query_embedding(self, query):
        """Get the embeddings for a query using the API"""
        body = {"query": [query]}
        infer_start_time = time.time()
        try:
            response = requests.post(
                self.api_url,
                json=body,
                verify=self.ssl_check,
                headers={
                    "Content-Type": "application/json",
                    "X-Apig-AppCode": self.app_code,
                },
                timeout=REQUEST_TIME_OUT,
            )
            infer_cost = time.time() - infer_start_time
            res_dict = json.loads(response.content.decode("utf-8"))
            result = res_dict.get("emb")
            if not result or not isinstance(result, list):
                logger.error("TextEmbeddingService response error, return mock emb")
                return self.mock_result, infer_cost
            emb_values = [float(val) for val in result[0].split(",")]
            if len(emb_values) != self.emb_dim:
                logger.error(
                    f"TextEmbeddingService dimension mismatch, expected:{self.emb_dim}, actual:{len(emb_values)}"
                )
                return self.mock_result, infer_cost
            return emb_values, infer_cost
        except Exception:
            logger.error("TextEmbeddingService request error, return mock emb")
            ret = None
            return self.mock_result, ret
