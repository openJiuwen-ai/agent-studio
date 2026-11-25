#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
import os
import time
from typing import Optional, Dict, Any, List, Iterable

from jiuwen.common.configs.env_constants import RULE_CACHE_ENABLE_KEY
from jiuwen.common.intent_detection.adapt.engine import IntentDeterminationEngine
from jiuwen.common.intent_detection.adapt.intent import IntentBuilder
from jiuwen.common.intent_detection.config import RuleMatcherConfig
from jiuwen.common.intent_detection.layers.base import (
    BaseMatcher,
    IntentInput,
    IntentOutput,
)
from jiuwen.common.intent_detection.utils.tokenizer import JiebaTokenizerPool
from jiuwen.common.log.base import logger
from jiuwen.common.store.async_redis import get_async_redis_instance
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.serve.controllers.execution.open_utils import cache_intent_rule_queue
from pydantic import BaseModel, Field

# adapt 结果字段
ADAPT_INTENT_TYPE = "intent_type"
ADAPT_CONFIDENCE = "confidence"
ADAPT_ENTITIES = "entities"

# adapt结果返回数量
DEFAULT_RULE_MATCHER_TOP_K = 5
DEFAULT_RULE_MATCHER_REDIS_RULE_KEY = "intent_rules"

DECODE_TYPE = "utf-8"


class RuleRetrivalConfig(BaseModel):
    rules_key: str = Field(min_length=1)
    top_k: int = Field(default=5)
    use_history: bool = False
    history_max_turns: int = Field(default=3, ge=0)


class RuleMatcher(BaseMatcher):
    """
    规则匹配
    """

    name = "rule"
    redis_instance = None

    def __init__(self, config: RuleMatcherConfig):
        """
        初始化

        Args:
            config: 配置项
        """
        self.config = config
        self.rule_retrival_config = self._get_rule_retrival_config(config)
        self.tokenizer_config = config.tokenizer_config
        # 懒加载 Redis 客户端（只在首次创建 RuleMatcher 时初始化）
        if RuleMatcher.redis_instance is None:
            RuleMatcher.redis_instance = get_async_redis_instance()
        self.redis_client = RuleMatcher.redis_instance
        self.tokenizer = JiebaTokenizerPool.get_instance().get_tokenizer()  # 分词器实例
        self.engine = None  # 全局引擎（不指定domain时使用）
        self._engine_initialized = False  # 全局引擎是否已初始化
        self._domain_engines: Dict[str, IntentDeterminationEngine] = {}

    async def invoke(
        self, input_data: IntentInput, top_k: Optional[int] = None, **kwargs
    ) -> IntentOutput:
        """
        异步匹配接口
        """
        try:
            retr_top_k = max(
                top_k or 0, self.rule_retrival_config.top_k
            )  # 匹配返回的topk，取较大者
            domains = kwargs.get("domains")
            logger.info(
                f"in rule_matcher, domains:{domains}", simple_log="start rule match"
            )
            engines = await self._get_engines(domains)  # 获取domain对应的规则引擎
            if not engines:
                return IntentOutput()

            query_text = self._build_context_query(input_data)
            logger.info(
                f"succeed to get query_text in rule matcher:{query_text}",
                simple_log="succeed to get query_text in rule matcher",
            )

            detect_intent_start = time.perf_counter()
            intent_results = await self._get_intent_results(
                engines, query_text, retr_top_k
            )
            detect_intent_end = time.perf_counter()
            detect_intent_duration = round(
                (detect_intent_end - detect_intent_start) * 1000
            )
            wf_performance_buffer.info(
                f"time for {self.name} detecting intent",
                detect_intent_duration,
                is_record=True,
            )

            logger.info(
                f"succeed to get intent_results in rule_matcher, intent_results:{intent_results},"
                f" valid_intents:{input_data.valid_intents}",
                simple_log="succeed to get intent_results",
            )
            res = self._build_output(
                list(input_data.valid_intents.keys()), intent_results, top_k
            )
            logger.info(
                f"succeed to get rule match res:{res}",
                simple_log="succeed to get rule match res",
            )
            return res

        except Exception as e:
            logger.error(f"Failed to match intent by rule matcher: {e}", exc_info=True)
            return IntentOutput()

    async def _get_engines(self, domains: Optional[List[str]]) -> List[Any]:
        """获取意图引擎"""
        if domains:
            return await self._get_domain_engines(domains)

        if not self._engine_initialized:
            await self._init_engine()
            self._engine_initialized = True

        return [self.engine] if self.engine else []

    async def _get_intent_results(
        self, engines: List[Any], query_text: str, top_k: int
    ) -> List[Dict]:
        """检索结果并合并结果"""
        all_results = []
        for engine in engines:
            results = engine.determine_intent(query_text, top_k)

            if isinstance(results, Iterable) and not isinstance(
                results, (str, bytes, list, tuple, dict)
            ):
                results = list(results)
            if results:
                all_results.append(results)

        return self._merge_intent_results(all_results, top_k)

    def _build_output(
        self,
        valid_intents: list,
        intent_results: List[Dict],
        top_k: Optional[int] = None,
    ) -> IntentOutput:
        """构造输出"""

        filtered_results = []
        candidates = []
        for r in intent_results:
            intent_type = r.get(ADAPT_INTENT_TYPE)
            if intent_type and intent_type in valid_intents:
                filtered_results.append(r)
                candidates.append(intent_type)

        candidates = candidates[:top_k] if top_k else []

        threshold = self.config.threshold

        if filtered_results:
            best = filtered_results[0]
            intent_name = best.get(ADAPT_INTENT_TYPE)
            score = best.get(ADAPT_CONFIDENCE, 0.0)
            intent_id = valid_intents.index(intent_name) + 1

            if score >= threshold:
                return IntentOutput(
                    intent_id=str(intent_id),
                    intent_name=intent_name,
                    score=score,
                    is_matched=True,
                    matched_layer=self.name,
                )

        return IntentOutput(candidates=candidates)

    async def _init_engine(self):
        """
        初始化全局adapt引擎
        从Redis加载所有规则（不指定domain时使用）
        """
        self.engine = IntentDeterminationEngine(self.tokenizer)
        rules = await self._load_all_rules()
        self._register_rules(rules)

    async def _load_all_rules(self) -> dict[str, Any]:
        """
        从Redis加载所有规则

        Returns:
            dict: 规则
        """
        load_rule_start = time.perf_counter()

        self.rules_key = self.rule_retrival_config.rules_key
        cache_rule = await cache_intent_rule_queue.aget(self.rules_key)
        if cache_rule:
            logger.info(
                f"got cached rule for domain key :{self.rules_key}",
                simple_log="got cached rule",
            )
            end_time = time.perf_counter()
            duration = round((end_time - load_rule_start) * 1000)
            logger.info(f"get rule cache time {duration}")
            return cache_rule
        logger.info(
            f"no cached rule for domain key :{self.rules_key}",
            simple_log="no cached rule",
        )

        redis_client = self.redis_client.get_redis_client()
        raw_rules = await redis_client.hgetall(self.rules_key)
        rules = {}

        for k, v in raw_rules.items():
            intent_name = k.decode(DECODE_TYPE) if isinstance(k, bytes) else k
            rule = v.decode(DECODE_TYPE) if isinstance(v, bytes) else v
            rules[intent_name] = safe_json_loads(rule)
        if str(os.environ.get(RULE_CACHE_ENABLE_KEY, "false")).lower() == "true":
            await cache_intent_rule_queue.aput(self.rules_key, rules)
            logger.info("put rules in cache")
        logger.info(f"Loaded {len(rules)} rules from Redis")

        load_rule_end = time.perf_counter()
        load_rule_duration = round((load_rule_end - load_rule_start) * 1000)
        wf_performance_buffer.info(
            "time for loading rules", load_rule_duration, is_record=True
        )

        return rules

    def _get_domain_rules_key(self, domain: str) -> str:
        """
        获取指定domain的规则库key

        Args:
            domain: 域名

        Returns:
            str: domain对应的Redis key
        """
        return f"{self.rule_retrival_config.rules_key}:{domain}"

    async def _load_rules_by_domain(self, domain: str) -> dict[str, Any]:
        """
        从Redis加载指定domain的规则

        Args:
            domain: 域名

        Returns:
            dict: 该domain下的规则
        """
        load_rule_start = time.perf_counter()
        redis_client = self.redis_client.get_redis_client()
        domain_key = self._get_domain_rules_key(domain)
        cache_rule = await cache_intent_rule_queue.aget(domain_key)
        if cache_rule:
            logger.info(
                f"got cached rule for domain key :{domain_key}",
                simple_log="got cached rule",
            )
            end_time = time.perf_counter()
            duration = round((end_time - load_rule_start) * 1000)
            logger.info(f"get rule cache time {duration}")
            return cache_rule
        logger.info(
            f"no cached rule for domain key :{domain_key}", simple_log="no cached rule"
        )
        # 获取该domain下的所有规则
        raw_rules = await redis_client.hgetall(domain_key)
        rules = {}

        for k, v in raw_rules.items():
            intent_name = k.decode(DECODE_TYPE) if isinstance(k, bytes) else k
            rule_str = v.decode(DECODE_TYPE) if isinstance(v, bytes) else v
            rules[intent_name] = safe_json_loads(rule_str)
        if str(os.environ.get(RULE_CACHE_ENABLE_KEY, "false")).lower() == "true":
            await cache_intent_rule_queue.aput(domain_key, rules)
            logger.info("put rules in cache")
        logger.info(
            f"Loaded {len(rules)} rules for domain '{domain}' from Redis key '{domain_key}'"
        )
        return rules

    def _register_rules(self, rules: dict[str, Any]):
        """
        注册规则到全局adapt引擎

        Args:
            rules: 规则
        """
        self._register_rules_to_engine(self.engine, rules)

    def _build_context_query(self, input_data: IntentInput) -> str:
        """
        构建查询
        Args:
            input_data: 输入，包括query，对话历史等

        Returns:
            合并后的对话历史内容
        """
        if not self.rule_retrival_config.use_history or not input_data.dialogue_history:
            return input_data.query

        max_turns = self.config.history_max_turns
        history = (
            input_data.dialogue_history[-max_turns:]
            if input_data.dialogue_history
            else []
        )

        context_parts = []
        for turn in history:
            if hasattr(turn, "role") and hasattr(turn, "content"):
                content = turn.content
            elif isinstance(turn, dict):
                content = turn.get("content", "")
            else:
                content = ""
            if content:
                context_parts.append(content)

        # 对话历史包括最新的用户输入
        return " ".join(context_parts)

    def _tokenize(self, query: str) -> list:
        """
        分词

        Args:
            query: 用户查询

        Returns:
            list: 分词结果
        """
        if self.tokenizer:
            return self.tokenizer.tokenize(query)
        return query.split()

    async def _get_or_create_domain_engine(
        self, domain: str
    ) -> IntentDeterminationEngine:
        """
        获取或创建指定domain的引擎
        Args:

            domain: 域名

        Returns:
            IntentDeterminationEngine: domain对应的引擎实例
        """
        if domain in self._domain_engines:
            logger.info(f"Reusing cached engine for domain '{domain}'")
            return self._domain_engines[domain]

        logger.info(f"Creating new engine for domain '{domain}'")
        engine = IntentDeterminationEngine(self.tokenizer)
        rules = await self._load_rules_by_domain(domain)
        self._register_rules_to_engine(engine, rules)

        self._domain_engines[domain] = engine
        return engine

    async def _get_domain_engines(
        self, domains: List[str]
    ) -> List[IntentDeterminationEngine]:
        """
        获取多个domain的引擎列表
        每个domain使用独立的引擎，复用已缓存的引擎

        Args:
            domains: 域列表

        Returns:
            List[IntentDeterminationEngine]: domain引擎列表
        """
        engines = []
        for domain in domains:
            engine = await self._get_or_create_domain_engine(domain)
            engines.append(engine)
        return engines

    def _register_rules_to_engine(
        self, engine: IntentDeterminationEngine, rules: dict[str, Any]
    ):
        """
        注册规则到指定的adapt引擎

        Args:
            engine: adapt引擎实例
            rules: 规则
        """
        register_rule_start = time.perf_counter()

        words_to_add = []
        for intent_name, rule in rules.items():
            builder = IntentBuilder(intent_name)
            for req in rule.get("requires", []):
                if not isinstance(req, (list, tuple)) or len(req) != 2:
                    logger.warning(
                        f"Invalid requires format for intent {intent_name}: {req}"
                    )
                    continue
                entity, keywords = req
                if not isinstance(entity, str):
                    logger.warning(
                        f"Entity must be a string, got {type(entity)}: {entity}"
                    )
                    continue
                if not isinstance(keywords, (list, tuple)):
                    logger.warning(
                        f"Keywords must be a list, got {type(keywords)}: {keywords}"
                    )
                    continue
                for kw in keywords:
                    engine.register_entity(kw, entity)
                    words_to_add.append(kw)
                builder = builder.require(entity)

            for opt in rule.get("optionally", []):
                if not isinstance(opt, (list, tuple)) or len(opt) != 2:
                    logger.warning(
                        f"Invalid optionally format for intent {intent_name}: {opt}"
                    )
                    continue
                entity, keywords = opt
                if not isinstance(entity, str):
                    logger.warning(
                        f"Entity must be a string, got {type(entity)}: {entity}"
                    )
                    continue
                if not isinstance(keywords, (list, tuple)):
                    logger.warning(
                        f"Keywords must be a list, got {type(keywords)}: {keywords}"
                    )
                    continue
                for kw in keywords:
                    engine.register_entity(kw, entity)
                    words_to_add.append(kw)
                builder = builder.optionally(entity)

            engine.register_intent_parser(builder.build())

        register_rule_duration = round(
            (time.perf_counter() - register_rule_start) * 1000
        )
        wf_performance_buffer.info(
            "time for registering rules", register_rule_duration, is_record=True
        )

        for word in words_to_add:
            self.tokenizer.add_word(word)

    def _merge_intent_results(
        self, all_results: List[List[dict]], top_k: int
    ) -> List[dict]:
        """
        合并多个引擎的意图识别结果

        Args:
            all_results: 各引擎的结果列表
            top_k: 返回的结果数

        Returns:
            List[dict]: 结果列表
        """
        merged = []
        for results in all_results:
            merged.extend(results)
        merged.sort(key=lambda x: x.get(ADAPT_CONFIDENCE, 0.0), reverse=True)
        return merged[:top_k] if top_k else merged

    def _get_rule_retrival_config(
        self, config: RuleMatcherConfig
    ) -> RuleRetrivalConfig:
        return RuleRetrivalConfig(
            rules_key=DEFAULT_RULE_MATCHER_REDIS_RULE_KEY,
            top_k=DEFAULT_RULE_MATCHER_TOP_K,
            use_history=config.use_history,
            history_max_turns=config.history_max_turns,
        )
