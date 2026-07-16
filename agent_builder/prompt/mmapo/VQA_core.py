# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import base64
import os
import re
from typing import Dict, List, Any, Optional

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.prompt.mmapo.utils import is_network_image
from agent_builder.adapter.exception_bridge import JiuWenBaseException

DEFAULT_IMAGE_DIR = "demo"
IMAGE_DIR_ROOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IMAGE_FOLDER_NAME = os.environ.get("MMAPO_IMAGE_FOLDER", DEFAULT_IMAGE_DIR)
IMAGE_FOLDER_NAME_MAX_LENGTH = 64


class VQA:
    def __init__(self):
        self.image_dir_name = self._get_image_dir_name()

    @staticmethod
    def find_image_path_by_name(
        image_name: str, all_image_paths: List[str]
    ) -> Optional[str]:
        """
        在路径列表中查找匹配文件名的路径。
        """
        for path in all_image_paths:
            if os.path.basename(path) == image_name:
                return path
        return None

    @staticmethod
    def generate_filled_prompt(
        prompt_template: str,
        variable_dict: Dict[str, Any],
        variable_type_dict: Dict[str, Any],
    ) -> Optional[str]:
        """generate_filled_prompt"""
        filled_prompt_with_placeholder = prompt_template

        # 替换非图像变量
        for key, value in variable_dict.items():
            if variable_type_dict.get(key).lower() == "image":
                continue  # 图片变量暂时不处理
            placeholder = f"{{{{{key}}}}}"
            filled_prompt_with_placeholder = filled_prompt_with_placeholder.replace(
                placeholder, str(value)
            )

        # 提取prompt中剩余变量的占位符如{{IMAGE_0}}
        placeholders_in_prompt = set(
            re.findall(r"\{\{(.*?)\}\}", filled_prompt_with_placeholder)
        )

        for key in variable_dict:
            if variable_type_dict.get(key).lower() == "text":
                continue
            if key not in placeholders_in_prompt:
                logger.warning(
                    f"The image variable {key} is missing from "
                    f"the prompt template and cannot properly insert the image."
                )

        return filled_prompt_with_placeholder

    @staticmethod
    def _get_image_dir_name() -> str:
        image_dir_name = str(os.path.basename(IMAGE_FOLDER_NAME)).strip()
        if len(image_dir_name) > IMAGE_FOLDER_NAME_MAX_LENGTH:
            return DEFAULT_IMAGE_DIR
        if image_dir_name.startswith("."):
            return DEFAULT_IMAGE_DIR
        return image_dir_name

    def get_image(self, image_name: str, all_image_paths: List[str]) -> Optional[str]:
        """get_base64_image"""
        if is_network_image(image_name):
            return image_name
        image_path = self.find_image_path_by_name(image_name, all_image_paths)
        if not image_path or not os.path.isfile(image_path):
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.code,
                message=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.errmsg.format(
                    error_msg=f"The image {image_path} is unavailable or failed to load"
                ),
            )
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
            base64_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/png;base64,{base64_image}"

    def generate_messages_from_prompt(
        self,
        filled_prompt_with_placeholder: str,
        variable_dict: Dict[str, Any],
        variable_type_dict: Dict[str, Any],
        all_image_paths: List[str],
    ) -> List[Dict[str, str]]:
        """generate_messages_from_prompt"""
        image_keys = [k for k, v in variable_type_dict.items() if v.lower() == "image"]
        escaped_placeholders = [re.escape(p) for p in image_keys]
        pattern = r"\{\{" + "|".join(escaped_placeholders) + r"\}\}"
        text_parts = re.split(pattern, filled_prompt_with_placeholder)
        messages = []

        for i, text in enumerate(text_parts):
            if text.strip():
                messages.append({"type": "text", "text": str(text.strip())})

            if i < len(image_keys):
                image_key = image_keys[i]
                image_name = variable_dict.get(image_key, "")
                if not image_name:
                    logger.warning(
                        f"generate_messages: 模板中需要图片变量 {image_key}，但variable_dict中未提供。"
                    )
                    continue
                _image = self.get_image(image_name, all_image_paths)
                if not _image:
                    logger.warning(f"图片 {image_name} 获取失败，终止 message 构造。")
                    return []
                messages.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": _image, "detail": "low"},
                    }
                )
        return messages

    def get_message_from_raw_prompt(
        self,
        prompt_template: str,
        evaluation_dict: Dict[str, Any],
        all_image_paths: List[str],
    ):
        """get_message_from_raw_prompt"""

        filled_prompts_with_text = self.generate_filled_prompt(
            prompt_template,
            evaluation_dict.get("variable_dict"),
            evaluation_dict.get("variable_type_dict"),
        )

        message = self.get_message_from_filled_prompt(
            filled_prompts_with_text,
            evaluation_dict.get("variable_dict"),
            evaluation_dict.get("variable_type_dict"),
            all_image_paths,
        )
        return message

    def get_message_from_filled_prompt(
        self,
        filled_prompt_with_placeholder: str,
        variable_dict: Dict[str, Any],
        variable_type_dict: Dict[str, Any],
        all_image_paths: List[str],
    ) -> List[Dict[str, str]]:
        """get_message_from_filled_prompt"""

        messages = self.generate_messages_from_prompt(
            filled_prompt_with_placeholder,
            variable_dict,
            variable_type_dict,
            all_image_paths,
        )
        if not messages:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.code,
                message=StatusCode.PROMPT_STORAGE_TYPE_NOT_MATCH_ERROR.errmsg.format(
                    error_msg="Failed to generate messages from prompt."
                ),
            )
        return messages

    def get_all_image_paths(self, image_name_list) -> List[str]:
        """get_all_image_paths"""
        if not image_name_list:
            return []
        if self.image_dir_name:
            image_path_list = [
                os.path.join(IMAGE_DIR_ROOT_PATH, self.image_dir_name, imageName)
                for imageName in image_name_list
                if not is_network_image(imageName)
            ]
        else:
            image_path_list = [
                os.path.join(IMAGE_DIR_ROOT_PATH, imageName)
                for imageName in image_name_list
                if not is_network_image(imageName)
            ]
        return image_path_list
