from typing import (Any, Container, Dict, List, Optional, Sequence, Type,
                    TypeVar, Union, get_type_hints)

from fastapi import status
from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import JSON, LargeBinary, Text, UnicodeText, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped

from openjiuwen_studio.schemas.common import ResponseModel

orm_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Base(DeclarativeBase):
    pass


T = TypeVar("T", bound='DBFunBase')


class DBFunBase:
    """
    作用
        - 从 dict / dict 列表初始化: 支持 db<->json 显式映射
        - 如果数据库存在_rest_字段，未知字段自动落入 _rest_(JSON)
    """
    __version_none__ = "draft"      # 对于version为空或者草稿版本，version的取值
    __rest_db_col_name__ = "_rest_"  # 自定义 _rest_ 字段对应数据库表名: _rest_
    __latest_publish_version__ = "latest_publish_version"   # 如果version等于此值，代表获取最新的发布版本
    # 数据库模糊查找时，searchs中此字段的values会作为模糊匹配的code，与searchs中的其他搜索值一起形成or条件进行搜索
    __searchs_by_sqlalchemy_code__ = "searchs_by_sqlalchemy_code"

    # 模型字段 与 外部JSON key的映射表, 无论是否一样都会进行映射, 无_rest_。1对1: str:str
    __json_2_db_map__ = None    # dict, 外部 key → 模型字段名
    __db_2_json_map__ = None    # dict, 模型字段名 → 外部 key
    __meta_data_keys__ = None        # list, 元数据字段名列表(外部key), 用于过滤掉可能数据量较大的字段(如: Text, UnicodeText, JSON, LargeBinary)

    @classmethod
    def _get_db_2_json_map(cls) -> dict:
        """
        获取__db_json_2_map__：模型字段 与 外部JSON key的映射表（模型字段名 → 外部 key）。无_rest_
        """
        if cls.__db_2_json_map__ is None:
            cls.__db_2_json_map__ = {col.name: attr_name for attr_name, col in inspect(
                cls).columns.items() if col.name != cls.__rest_db_col_name__}
        return cls.__db_2_json_map__

    @classmethod
    def _get_json_2_db_map(cls) -> dict:
        """获取反向映射表： 外部 key → 模型字段名   """
        if cls.__json_2_db_map__ is None:
            cls.__json_2_db_map__ = {v: k for k, v in cls._get_db_2_json_map().items()}
        return cls.__json_2_db_map__
    
    @classmethod
    def get_meta_data_keys(cls) -> list:
        """
        获取模型中“非大字段”的字段名(key)
        排除 Text, JSON, LargeBinary 等可能较大的字段
        """
        if cls.__meta_data_keys__:
            return cls.__meta_data_keys__
        mapper = inspect(cls)
        cls.__meta_data_keys__ = []
        for attr_name, col in mapper.columns.items():
            if isinstance(col.type, (Text, UnicodeText, JSON, LargeBinary)):
                continue
            cls.__meta_data_keys__.append(attr_name)
        return cls.__meta_data_keys__
    
    @classmethod
    def _json_key_2_db_field(cls, json_key: Union[str, List]) -> Union[str, List]:
        """ json的key转数据库的字段，如果没有找到对应的字段，对应位置返回None  """
        field_map_reverse = cls._get_json_2_db_map()

        def one_key_2_db_field(key: str) -> str:
            if key in field_map_reverse:
                return field_map_reverse[key]
            return None
        if isinstance(json_key, List):
            return [one_key_2_db_field(k) for k in json_key]
        return one_key_2_db_field(json_key)

    @classmethod
    def _db_field_2_json_key(cls, db_field: Union[str, List]) -> Union[str, List]:
        """ 数据库字段转json的key，如果没有找到对应的字段，对应位置返回None  """
        field_map = cls._get_db_2_json_map()

        def one_field_2_json_key(field: str) -> str:
            if field in field_map:
                return field_map[field]
            return None
        if isinstance(db_field, List):
            return [one_field_2_json_key(f) for f in db_field]
        return one_field_2_json_key(db_field)

    '''
    description: 因为find_id用于定位数据行，比较重要, 这里对find_id进行验证:
                    1. 所有的值均不能为空
                    2. 所有的key(json中的key，非数据库字段)均能在表格中找到对应字段
                    3. 验证成功, 同时返回find_id_db: 将json key转换为数据库字段; 验证失败返回None
    param {Dict} find_id    key是Json的key，非数据库的字段
    return {*}
    '''
    @classmethod
    def _find_id_verify(cls, find_id: dict[str, Any]) -> ResponseModel[None]:
        if not find_id:
            return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="[Find_id verify]: Find_id cannot be empty.")
        for k, v in find_id.items():
            if v is None or v == "":   # 如果v是None或""
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="[Find_id verify]: All data in find_id cannot be empty.")
            if k not in cls._get_json_2_db_map():
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="[Find_id verify]: All keys in JSON must match the fields in the database.")
        return ResponseModel(code=status.HTTP_200_OK, message="Find_id is ok.")

    @classmethod
    def filter_invalid_keys(cls, data: dict[str, Any], invalid_set: set = {None}) -> dict:
        """过滤掉无效字段"""
        return {k: v for k, v in data.items() if v not in tuple(invalid_set)}

    '''
    description: 把 JSON key转成 模型字段： 可选择：
                    1. 是否保存无效值(None, ""等)
                    2. 是否保存_rest_字段用于保存未匹配上的数据
    param {*} cls
    param {Dict} data   待转换的数据, key为json的key，非数据库的字段
    param {bool} exclude_invalid    结果是否丢弃无效值(None, ""等); 默认False(保留)
    param {bool} exclude_rest       如果rest非空，结果是否丢弃_rest_字段; 默认False(保留)。如果rest是空的，直接不返回该字段
    return {*}
    '''
    @classmethod
    def _json_2_db_data(cls, data: Dict[str, Any], exclude_invalid: bool = False,
                        exclude_rest: bool = False) -> Dict:
        # 过滤掉无效值(None, ""等)
        if exclude_invalid:
            data = cls.filter_invalid_keys(data)
        # 1 根据匹配条件，将json的部分key转换成数据库字段
        res = {}
        for json_key, db_col in cls._get_json_2_db_map().items():
            if json_key not in data:
                continue
            res[db_col] = data.pop(json_key)
        # 2. 如果要保存_rest_字段，则把剩余的键值对放入_rest_
        if not exclude_rest and hasattr(cls, cls.__rest_db_col_name__):
            if data:
                res[cls.__rest_db_col_name__] = data
        return res

    '''
    description: 对于输入的json_key list, 只返回能匹配上模型属性(包含_rest_)的key
    param {*} cls
    param {Union} json_key
    param {*} List
    return {*}
    '''
    @classmethod
    def _json_key_filter(cls, json_key: Union[List]) -> Union[List]:
        return [k for k in json_key if k in cls._get_json_2_db_map() or k == cls.__rest_db_col_name__]

    '''
    description: 对输入的json数据, 将其中的_rest_数据(若存在)进行展开
    param {*} cls
    param {Dict} data   输入的json数据
    param {bool} exclude_invalid    是否将无效值(None, {}, ""等)丢弃; 默认False(保存)
    return {*}      输出的json数据，带_rest_关键字
    '''
    @classmethod
    def _json_flatten_rest(cls, data: Dict[str, Any], exclude_invalid: bool = False):
        res = data.pop(cls.__rest_db_col_name__, None) or {}
        res.update(data)
        # 过滤掉无效值(None, {}, ""等)
        if exclude_invalid:
            res = cls.filter_invalid_keys(res)
        return res

    '''
    description: 对输入的data, 将未知字段整合保存到 _rest_(JSON)中，已知字段不改变, key还是json的key(非数据库字段)
    param {*} cls
    param {Dict} data   输入的json数据
    param {bool} exclude_invalid    是否将无效值(None, {}, ""等)丢弃; 默认False(保存)
    param {bool} exclude_rest       如果rest非空，结果是否丢弃_rest_字段; 默认False(保留)。如果rest是空的，直接不返回该字段
    return {*}      输出的json数据，带_rest_关键字
    '''
    @classmethod
    def _json_with_rest(cls, data: Dict[str, Any], exclude_invalid: bool = False,
                        exclude_rest: bool = False) -> Dict:
        # 过滤掉无效值(None, {}, ""等)
        if exclude_invalid:
            data = cls.filter_invalid_keys(data)
        # 1. 取出已知字段
        kv = {k: v for k, v in data.items() if k in cls._get_json_2_db_map()}
        # 2. 把剩余的键值对放入_rest_
        if not exclude_rest and hasattr(cls, cls.__rest_db_col_name__):
            rest = {k: v for k, v in data.items() if k not in cls._get_json_2_db_map()}
            if rest:
                kv[cls.__rest_db_col_name__] = rest
        return kv
    
    @classmethod
    def sqlalchemy_to_pydantic(cls, *, config: type = orm_config, 
                               exclude: set[str] | None = None) -> type[BaseModel]:
        exclude = exclude or set()
        # 因relationship等类型有时会先以str代表，先替换其为Any类，避免get_type_hints报错
        ann_back = cls.__annotations__.copy()
        for name, _ in list(cls.__annotations__.items()):
            if name not in inspect(cls).columns.keys():     # 非数据表colums列
                cls.__annotations__[name] = Any     # 也可以直接 del ann[name]
        hints = get_type_hints(cls)
        # 还原原注释
        cls.__annotations__ = ann_back
        fields: dict[str, tuple[type, Any]] = {}
        for attr_name, column in inspect(cls).columns.items():
            if attr_name in exclude or column.name == cls.__rest_db_col_name__:
                continue
            # 1. 优先使用 Mapped[T] 里的 T
            if attr_name in hints:
                raw = hints[attr_name]
                # 解开 Mapped[XXX]
                if hasattr(raw, "__origin__") and raw.__origin__ is Mapped:
                    python_type = raw.__args__[0]
                else:
                    python_type = raw
                # 把 "T | None" 拆成 (T, None) 或 (T, ...)
                if hasattr(python_type, "__origin__") and python_type.__origin__ is Union:
                    # Python 3.10+ 写的 dict | list 会走这里
                    args = python_type.__args__
                    if type(None) in args or not column.nullable:
                        non_none = next(t for t in args if t is not type(None))
                        fields[attr_name] = (python_type, None)      # Optional 分支
                    else:
                        fields[attr_name] = (python_type, ...)
                else:
                    fields[attr_name] = (python_type, ...) if not column.nullable else (Optional[python_type], None)
                continue
            # 2. 无Mapped，则使用 mapped_column中的信息来推断类型
            if hasattr(column.type, "impl") and hasattr(column.type.impl, "python_type"):
                py_type = column.type.impl.python_type
            elif hasattr(column.type, "python_type"):
                py_type = column.type.python_type
            else:
                raise RuntimeError(f"cannot infer python type for {column}")

            fields[attr_name] = (py_type, ...) if not column.nullable else (Optional[py_type], None)

        return create_model(cls.__name__, __config__=config, **fields)

    '''
    description: 从dict数据初始化模型; 从dict中取有效key, 无效key保存至_rest_字段或直接丢弃但不影响运行
    param {Dict} data   输入dict, key为json的key，非数据库的字段
    param {bool} exclude_invalid    结果是否丢弃无效值(None, {}, ""等); 默认False(保留)
    return {*}
    '''
    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any], exclude_invalid: bool = False) -> T:
        """单个 dict -> 实例"""
        kv = cls._json_with_rest(data, exclude_invalid, exclude_rest=False)
        return cls(**kv)

    '''
    description: 从[dict]数组中批处理初始化模型; 从各个dict中取有效key, 无效key保存至_rest_字段或直接丢弃但不影响运行
    param {type} cls
    param {Sequence} data_list  输入dict数组, key为json的key，非数据库的字段
    param {bool} exclude_invalid    结果是否过滤无效值(None, {}, ""等); 默认True(过滤)
    return {*}
    '''
    @classmethod
    def from_dicts(cls: type[T], data_list: Sequence[Dict[str, Any]], 
                   exclude_invalid: bool = False) -> List[T]:
        """dict 列表 -> 实例列表"""
        return [cls.from_dict(d, exclude_invalid) for d in data_list]
    
    '''
    description: 将模型转换成json的dict数组，然后进行输出；如果模型表中有_rest_，则 _rest_ 里的键值对拆平到顶层，不出现 _rest_ 本身。
    param {*} self
    param {*} exclude_none  结果是否过滤None; 默认False(保留)
    param {set} exclude     需要过滤掉的字段
    return {*}
    '''

    def model_dump(self, exclude_none: bool = False, exclude: set = set(), exclude_value: set = set()):
        # 1. 取出已知字段
        base = {attr: getattr(self, attr) for attr in self._get_json_2_db_map().keys()}
        # 2. 把 _rest_ 摊平
        res = {} if not hasattr(self, self.__rest_db_col_name__) else getattr(self, self.__rest_db_col_name__) or {}
        res.update(base)
        # 3. 过滤部分key
        res = {k: v for k, v in res.items() if k not in exclude}
        # 4. 过滤个别值
        invalid_set = set({None}) if exclude_none else set()
        invalid_set = invalid_set.union(exclude_value)
        if invalid_set:
            res = self.filter_invalid_keys(res, invalid_set)
        return res

    '''
    description: 模型转换成json的dict数组，然后进行输出；如果模型表中有_rest_，则 _rest_ 里的键值对拆平到顶层，不出现 _rest_ 本身。
    param {bool} exclude_invalid    结果是否过滤无效值(None, ""等); 默认False(保留)
    return {*}
    '''

    def to_dict(self, exclude_invalid: bool = False) -> Dict[str, Any]:
        exclude = set()
        # 过滤掉无效值(None, ""等)
        if exclude_invalid:
            exclude = {None, ""}
        return self.model_dump(exclude=exclude)
    
