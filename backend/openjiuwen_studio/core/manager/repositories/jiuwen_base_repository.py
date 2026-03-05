from contextlib import contextmanager, nullcontext
from functools import wraps
from typing import Any, Callable, ContextManager, Dict, List, Optional, TypeVar

from fastapi import status
from sqlalchemy import (String, Text, Unicode, asc, between, desc, inspect,
                        or_, select, update, func)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import SessionLocal
from openjiuwen_studio.core.manager.repositories import BaseRepository
from openjiuwen_studio.models.db_fun_base import DBFunBase
from openjiuwen_studio.schemas.common import ResponseModel

T = TypeVar('T')


def escape_like(value: str, escape_char: str = "\\") -> str:
    """Escape LIKE metacharacters (%, _, \\) in user input to prevent wildcard injection."""
    return (
        value
        .replace(escape_char, escape_char + escape_char)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )


@contextmanager
def generate_db_jw():
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def get_db_jw(db_session: Session | None = None) -> ContextManager[Session]:
    if db_session is not None:
        return nullcontext(db_session)
    return generate_db_jw()


'''
description: 从dict数组中获取某个键值的数值；这个键值在dict中的名称可能不确定，而是有一个名称的list可能集，遍历list直到找到后返回
param {Dict} dict_data
param {*} key_list
'''


def get_val_from_dict(dict_data: Dict, key_list):
    for key in key_list:
        if key in dict_data:
            return dict_data[key]
    return None


'''
返回状态码：
HTTP_200_OK = 200                       ### 操作成功
HTTP_400_BAD_REQUEST = 400              ### 语法错误/参数无效/资源冲突的问题，比如因为创建时数据已存在导致冲突、传入的参数无效导致等原因，最终导致操作失败
HTTP_404_NOT_FOUND = 404                ### db无对应资源的问题，因数据未找到导致的错误
HTTP_500_INTERNAL_SERVER_ERROR = 500    ### db服务器内部故障，比如数据库配置错误、数据库连接掉线等问题导致失败，与api本身无关
'''

'''
description: jiuwen数据库的常用操作，返回值为ResponseModel类型
return {*}
'''


class JiuwenBaseRepository(BaseRepository[DBFunBase]):
    def __init__(self, db: Session, model_class: DBFunBase):
        self._model_class = model_class
        super().__init__(db, model_class)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"DB error: {str(e)}", exc_info=True)
                if "find_id" in kwargs:
                    if "dl" in kwargs:
                        logger.error(
                            f"db_table_name: {self._model_class.__tablename__}, find_ids: {kwargs['find_id']}, dl: {kwargs['dl']}")
                    else:
                        logger.error(
                            f"db_table_name: {self._model_class.__tablename__}, find_ids: {kwargs['find_id']}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Internal server error: database operation failed")
        return wrapper

    '''
    description: 在数据库中查找是否存在该dl数据
    param {Dict} find_id        用于定位数据的键值，dict，可有多个，里面的key是json数据中的key, 而非数据库的字段
    return {*}
    '''
    @with_exception_handling
    def _find_dl_in_sql(self, find_id: Dict[str, Any]) -> ResponseModel[None]:
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res
        if self.exists(**find_id):
            return ResponseModel(code=status.HTTP_200_OK, message="Found.")
        else:
            return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Not Found.")
    
    '''
    description: 在数据库中查找该dl数据的数量
    param {Dict} find_id        用于定位数据的键值，dict，可有多个，里面的key是json数据中的key, 而非数据库的字段
    return {*}
    '''
    @with_exception_handling
    def count_dl_in_sql(self, find_id: Dict[str, Any]) -> ResponseModel[int | None]:
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res
        count = self.count(**find_id)
        return ResponseModel(code=status.HTTP_200_OK, message="Count over.", data=count)

    def count_dl_in_sql_with_search(self, find_id: Dict[str, Any], searchs: Optional[dict[str, Optional[list[str]]]] = None) -> ResponseModel[int | None]:
        """
        Count records with search conditions - used for accurate total counts in search functionality
        """
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res

        mapper = inspect(self._model_class)

        # Build count query with find_id conditions
        from sqlalchemy.sql import column

        # Build base count query
        stmt = select(func.count()).select_from(self._model_class)

        # Apply find_id conditions
        for col_name, val in find_id.items():
            col = mapper.columns[col_name]
            stmt = stmt.where(col.in_(val) if isinstance(val, list) else col == val)

        # Apply search conditions if present
        if searchs:
            search_cols = []
            search_vals = []
            for search, cols in searchs.items():
                escaped = escape_like(search)
                if not cols:
                    this_search_cols = [c for c in mapper.columns if isinstance(c.type, (String, Text, Unicode))]
                    search_vals += [f"%{escaped}%" for _ in this_search_cols]
                    search_cols += this_search_cols
                else:
                    cols = self._model_class._json_key_filter(cols)
                    this_search_cols = [mapper.columns[c] for c in cols]
                    search_vals += [f"%{escaped}%" for _ in this_search_cols]
                    search_cols += this_search_cols

            stmt = stmt.where(or_(*[c.ilike(v, escape="\\") for c, v in zip(search_cols, search_vals)]))

        # Execute count query
        result = self.db.execute(stmt).scalar()
        count = result if result is not None else 0

        return ResponseModel(code=status.HTTP_200_OK, message="Count with search over.", data=count)

    '''
    description: 在数据库中查找是否存在该dl数据, 存在则并返回dl的cols_find字段的数据。下面所有的key均为sql数据库中的字段
    param {Dict} find_id            {key:value}, 用于定位数据的键值, dict类型, 支持多个, 里面的key是json中的key, 而非数据库的字段; value如果是list, 表示数值是list中任意一个即满足
    param {List} cols_find          key是json中的key, 而非数据库的字段, 最后只返回这些字段的数据; 如果为None则返回全部字段
    param {Dict} find_min_max       {key:value}, 用于定位数据的键值, 支持多个, 里面的key是json中的key, 而非数据库的字段; 
                                        value是list, 比如[min, max], len=2,  只查找[min, max]范围内的数据，如果min或max为None，分别表示没有左或右边界
    param {List} order_cols_asc     按照这里的字段(json的key)对结果进行升序排序
    param {List} order_cols_desc    按照这里的字段(json的key)对结果进行降序排序
    param {List} return_range       对返回的数量进行限制, [a, Option[b]], 1-2个int值.
                                        1. 1个值, 返回前a行;
                                        2. 2个值, 跳过前a行, 再返回b行数据, LIMIT offset, row_count
    param {dict[str, Optional[list]]} searchs   利用search字符进行模糊查找(找到其中一个即可), 其中searchs的说明如下:
                                                1) key是要匹配的字符, 则values是list|None, 
                                                    如果是list存放去哪几列(json的key,非数据库字段)进行模糊匹配，如果是None，说明对所有字符类列进行匹配。
                                                    例如: searchs = {"翻译助手": ['name', 'description'], "旅游": None}, 2个模糊查找, 能找到一个即可 
                                                        1. 第1个元素说明从 'name' 和 'description' 这2列进行模糊匹配"翻译助手";
                                                        2. 第2个元素说明从类型为String, Text, Unicode的所有列模糊查找"旅游";
                                                2) key是特殊值"searchs_by_sqlalchemy_code", 则values是list|sqlalchemy的code类型, 值为sqlalchemy的一些判断code, 可以直接作为or中组合判断条件                                                
    param {List} other_sqlalchemy_limitations   其他sqlalchemy的限制条件，其中的元素是sqlalchemy语句，最终使用.where()....where()串联各个限制
    param {bool} return_first_item      默认False, 返回[...].  True: 有数据时，仅返回首个元素数据
    param {bool} return_declarativebase  cols_find=None时才可用。默认False. True: 返回DeclarativeBase类型的模型,
                                                    False: 返回dict类型数据
    return {ResponseModel}      其中的data, 如果 return_first_item = True, 只返回首元素的数据;
                                            如果 return_first_item = False, 返回所有元素的list数组
    '''

    def get_dl_in_sql_with_cols(self, find_id: Dict[str, Any], cols_find: Optional[List] = None, find_min_max: Dict[str, list] = {},
                                 order_cols_asc: Optional[List] = [], order_cols_desc: Optional[List] = [],
                                 return_range: Optional[List] = None, searchs: Optional[dict[str, Optional[list[str]]]] = None, 
                                 other_sqlalchemy_limitations: Optional[List] = [],
                                 return_first_item: bool = False, return_declarativebase: bool = False) -> ResponseModel[list[dict | T] | dict | T | None]:
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res
        # 对于json的key，只保留模型有的attr
        if cols_find:  
            cols_find = self._model_class._json_key_filter(cols_find)
        order_cols_asc = self._model_class._json_key_filter(order_cols_asc)
        order_cols_desc = self._model_class._json_key_filter(order_cols_desc)
        if find_min_max:
            find_min_max_keys = self._model_class._json_key_filter(list(find_min_max.keys()))
            find_min_max = {k: find_min_max[k] for k in find_min_max_keys}
        mapper = inspect(self._model_class)
        # 1. 构造 select 列
        if cols_find is None:
            stmt = select(self._model_class)
        else:
            cols = [mapper.columns[name] for name in cols_find]
            stmt = select(*cols)
        # 2. where 条件
        # 2.1 find_id的单值或list限制，==号匹配
        for col_name, val in find_id.items():
            col = mapper.columns[col_name]
            stmt = stmt.where(col.in_(val) if isinstance(val, list) else col == val)
        # 2.2 find_min_max的范围限制，between匹配
        for col_name, val in find_min_max.items():
            if not (isinstance(val, (list, tuple)) and len(val) == 2):
                continue
            col = mapper.columns[col_name]
            if val[0] is not None and val[1] is not None:
                stmt = stmt.where(between(col, val[0], val[1]))
            elif val[0] is not None:
                stmt = stmt.where(col >= val[0])
            elif val[1] is not None:
                stmt = stmt.where(col <= val[1])
        # 2.3 模糊查找
        if searchs:
            search_cols = []
            search_vals = []
            searchs_code = searchs.pop(self._model_class.__searchs_by_sqlalchemy_code__, [])
            searchs_code = searchs_code if isinstance(searchs_code, list) else [searchs_code]
            for search, cols in searchs.items():
                escaped = escape_like(search)
                if not cols:
                    this_search_cols = [c for c in mapper.columns if isinstance(c.type, (String, Text, Unicode))]
                    search_vals += [f"%{escaped}%" for _ in this_search_cols]
                    search_cols += this_search_cols
                else:
                    cols = self.model_class._json_key_filter(cols)
                    this_search_cols = [mapper.columns[c] for c in cols]
                    search_vals += [f"%{escaped}%" for _ in this_search_cols]
                    search_cols += this_search_cols
            searchs_code += [c.ilike(v, escape="\\") for c, v in zip(search_cols, search_vals)]
            stmt = stmt.where(or_(*searchs_code))
        # 2.4 其他限制条件, 直接用sqlalchemy语句拼接
        if other_sqlalchemy_limitations:
            for limitation in other_sqlalchemy_limitations:
                stmt = stmt.where(limitation)
        # 3. 排序
        # 3.1 升序
        # 3. 排序
        for c in order_cols_asc or []:
            stmt = stmt.order_by(asc(mapper.columns[c]))
        for c in order_cols_desc or []:
            stmt = stmt.order_by(desc(mapper.columns[c]))
        # 4. 分页
        if return_range:
            if len(return_range) == 1:
                stmt = stmt.limit(return_range[0])
            elif len(return_range) == 2:
                stmt = stmt.offset(return_range[0]).limit(return_range[1])
        # 5. 执行
        rows = self.db.execute(stmt).all()
    
        # 6. 没有数据
        if not rows:
            return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Data not found.")
    
        # 单行 -> dict，多行 -> List[dict]
        if cols_find is None:       # 表格中的数据全部获取
            if return_declarativebase:  # 只有获取表格中所有数据，才会返回[model_list]
                data = [r[0] for r in rows]
            else:
                data = [r[0].model_dump() for r in rows]
        else:
            data = [self._model_class._json_flatten_rest(dict(zip(cols_find, r))) for r in rows]
        if return_first_item:
            data = data[0]
        return ResponseModel(code=status.HTTP_200_OK, message="Get dl successfully.", data=data)
    
    '''
    description: 在数据库中查找是否存在该dl数据，并返回dl的所有字段数据。
    具体参数说明请参考 get_dl_in_sql_with_cols 
    return {ResponseModel}      其中的data, 如果 return_first_item = True, 只返回首元素的数据;
                                            如果 return_first_item = False, 返回所有元素的list数组
    '''
    @with_exception_handling
    def get_dl_in_sql(self, find_id: Dict[str, Any], find_min_max: Dict[str, list] = {},
                        order_cols_asc: Optional[List] = [], order_cols_desc: Optional[List] = [],
                        return_range: Optional[List] = None, searchs: Optional[dict[str, Optional[list[str]]]] = None,  
                        other_sqlalchemy_limitations: Optional[List] = [],
                        return_first_item: bool = False, return_declarativebase: bool = False) -> ResponseModel[list[dict | T] | dict | T | None]:
        return self.get_dl_in_sql_with_cols(find_id, None, find_min_max, order_cols_asc, order_cols_desc, return_range, searchs, 
                                             other_sqlalchemy_limitations, return_first_item, return_declarativebase)

    '''
    description: 在数据库中查找是否存在该dl数据，并返回dl的meta数据(不包含可能较大的字段, 类型为Text, JSON, LargeBinary等)。
    具体参数说明请参考 get_dl_in_sql_with_cols 
    return {ResponseModel}      其中的data, 如果 return_first_item = True, 只返回首元素的数据;
                                            如果 return_first_item = False, 返回所有元素的list数组
    '''
    @with_exception_handling
    def _get_dl_meta_data_in_sql(self, find_id: Dict[str, Any], find_min_max: Dict[str, list] = {},
                        order_cols_asc: Optional[List] = [], order_cols_desc: Optional[List] = [],
                        return_range: Optional[List] = None, searchs: Optional[dict[str, Optional[list[str]]]] = None,  
                        other_sqlalchemy_limitations: Optional[List] = [],
                        return_first_item: bool = False, return_declarativebase: bool = False) -> ResponseModel[list[dict | T] | dict | T | None]:
        cols_find = self._model_class.get_meta_data_keys()
        return self.get_dl_in_sql_with_cols(find_id, cols_find, find_min_max, order_cols_asc, order_cols_desc, return_range, searchs, 
                                             other_sqlalchemy_limitations, return_first_item, return_declarativebase)

    '''
    description: 往数据库中注册数据
    param {Dict | None} find_id     用于定位数据是否已存在的键值，可有多个，里面的key是json数据中的key, 而非数据库的字段; 
                                    如果为None，则不作数据是否存在的验证，直接进行数据注册；这样可能会因数据已存在而报错
    param {Dict | T} dl             待注册的dict数据 或 sqlalchemy数据 
    return {*}
    '''
    @with_exception_handling
    def register_dl_in_sql(self, find_id: Dict[str, Any] | None, dl: Dict[str, Any] | T) -> ResponseModel[None]:
        if find_id:
            verify_res = self._model_class._find_id_verify(find_id)
            if verify_res.code != status.HTTP_200_OK:
                return verify_res
            if self.exists(**find_id):
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="This db already exists")
        if not dl:
            logger.debug(
                f"No valid data to register: \nsql_table_name: {self._model_class.__tablename__}, find_ids: {find_id}, dl: {dl}")
            return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No valid data to register")
        dl_with_rest = dl if isinstance(dl, self._model_class) else \
                            self._model_class._json_with_rest(dl, exclude_invalid=False, exclude_rest=False)
        self.create(dl_with_rest)
        return ResponseModel(code=status.HTTP_200_OK, message="Dl register successfully.")

    '''
    description: 批量往数据库中创建数据
    param {*} self
    param {List} dls    待创建的数据
    param {bool} exclude_invalid    结果是否过滤无效值(None, {}, ""等); 默认False(保留)
    return {*}
    '''

    def bulk_register_dl(self, dls: List[Dict[str, Any] | List[T]], 
                   exclude_invalid: bool = False) -> ResponseModel[None]:
        """Bulk create records.
        
        Args:
            objects: List of creation data
            
        Returns:
            List of created model instances
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            if not dls:
                return ResponseModel(code=status.HTTP_200_OK, message="empty Dl bulk register failed")
            db_objects = dls if isinstance(dls[0], self.model_class) else \
                                self.model_class.from_dicts(dls, exclude_invalid)
            self.db.add_all(db_objects)
            self.db.commit()
            
            # Refresh all objects to get auto-generated fields like ID
            for obj in db_objects:
                self.db.refresh(obj)
            return ResponseModel(code=status.HTTP_200_OK, message="Dl bulk register successfully.")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to bulk create records: {str(e)}")
            raise

    '''
    description: 从数据库中删除数据
    param {Dict} find_id        用于定位数据的键值，dict，可有多个，里面的key是json数据中的key, 而非数据库的字段
    return {*}
    '''

    def unregister_dl_in_sql(self, find_id: Dict[str, Any]) -> ResponseModel[None]:
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res
        to_delete_list = self.get_dl_in_sql(find_id, return_declarativebase=True)
        if to_delete_list.code != status.HTTP_200_OK:
            return to_delete_list
        # 删除数据: 选择逐条删除，原因：
        # 1. 一般一次删除的数据量较少(百/千级)
        # 2. 可保证ORM级及数据库级的事件/级联删除都能触发；批量删除只触发数据库级；
        if not to_delete_list.data:
            return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Dl not found.")
        for to_delete in to_delete_list.data:
            self.db.delete(to_delete)
        self.db.commit()
        return ResponseModel(code=status.HTTP_200_OK, message="Dl unregister successfully.")

    '''
    description: 不做rest字段的规则判断和整改，直接更新; 这里可以设置不commit提交，然后在外面单独提交
    param {*} find_id        用于定位数据, key是json的key, 非sql字段
    param {*} update_dl         待更新的数据, key是json的key, 非sql字段
    return {*}
    '''

    def _update_dl_in_sql_directly(self, find_id: Dict[str, Any], update_dl: Dict[str, Any], commit: bool = True) -> ResponseModel[None]:
        verify_res = self._model_class._find_id_verify(find_id)
        if verify_res.code != status.HTTP_200_OK:
            return verify_res
        if not update_dl:
            logger.debug(f"No valid data to update: ")
            return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No valid data to update")
        update_dl = self._model_class._json_with_rest(update_dl, exclude_invalid=True, exclude_rest=False)
        mapper = inspect(self._model_class)
        stmt = (
            update(self._model_class)
            .values({mapper.columns[col]: val for col, val in update_dl.items()})
            .where(*[mapper.columns[col] == val for col, val in find_id.items()])
        )
        result = self.db.execute(stmt)
        if commit:
            self.db.commit()
        return ResponseModel(code=status.HTTP_200_OK, message="Dl update successfully.")

    '''
    description: 更新数据库中的dl数据
    param {Dict} find_id        用于定位数据的键值，dict，可有多个，里面的key是json数据中的key, 而非数据库的字段
    param {Dict} update_dl      数据已存在, 待更新的json数据
    param {Dict} create_dl      如果数据暂不存在需要创建, 则最终创建数据为 update_dl+create_dl
    return {*}
    '''

    def update_dl_in_sql(self, find_id: Dict[str, Any], update_dl: Dict[str, Any], 
                          create_dl: Dict[str, Any] = {}) -> ResponseModel[None]:
        if self._find_dl_in_sql(find_id).code != status.HTTP_200_OK:
            create_dl.update(update_dl)
            return self.register_dl_in_sql(find_id, create_dl)
        
        dl_db = self._model_class._json_2_db_data(update_dl, exclude_invalid=True, exclude_rest=False)
        rest_db_key = self._model_class.__rest_db_col_name__

        # 如果sql表中没有保存rest的字段，或者 待更新dl_db数据中没有rest的字段， 直接调用update_directly函数
        if not hasattr(self._model_class, rest_db_key) or (rest_db_key not in dl_db):
            update_res = self._update_dl_in_sql_directly(find_id, update_dl)
        # 如果dl_db数据中的rest字段数值为空，
        elif not dl_db.get(rest_db_key, None):  
            update_res = self._update_dl_in_sql_directly(find_id, update_dl)
        else:  # 说明当前更新的数据中，有部分需要存入到 __rest__ 中去
            # 先获取数据表的PRIMARY KEY字段, List[Column]
            primary_keys = inspect(self._model_class).primary_key
            if not primary_keys:
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Update fail: Please ensure that the table {self._model_class.__tablename__} has a primary key for updates.")
            primay_key_db = primary_keys[0].name  # 主健在db表上的字段名
            # 主键在json上的key名称
            primay_key_json = self._model_class._db_field_2_json_key(primay_key_db)
            if primay_key_json is None:
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                    message=f"Update fail: Can't get primay_key's name on json. sql_table_name: {self._model_class.__tablename__} ,\
                                                find_id: {find_id}, primay_key_db: {primay_key_db}. Please update TABLE_META.")
            # 先获取要更新的数据 在sql上的 primay_key的数值
            cols_find = [primay_key_json, rest_db_key]
            get_primaykey_and_rest = self.get_dl_in_sql_with_cols(find_id, cols_find)
            if get_primaykey_and_rest.code != status.HTTP_200_OK:  # 如果没有找到主键和_rest_
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Update fail: Can't get primay_key and rest from db with find_id. \
                                        sql_table_name: {self._model_class.__tablename__} , find_id: {find_id}, primay_key: {primay_key_json}.")

            primaykey_rest_json_list = get_primaykey_and_rest.data
            for prkey_rest in primaykey_rest_json_list:
                primay_key_val = prkey_rest.pop(primay_key_json, None)
                if not primay_key_val:  # 说明主键获取失败
                    continue
                # 使用主键去更新数据
                update_find_id = {primay_key_json: primay_key_val}
                # 将__rest__中的数据，加入到待更新的数据中，避免更新后覆盖了__rest__数据
                prkey_rest.update(update_dl)
                # 数据转换并保存
                update_res = self._update_dl_in_sql_directly(update_find_id, prkey_rest, commit=False)
                if update_res.code != status.HTTP_200_OK:
                    logger.error(f"Update error: sql_table_name: {self._model_class.__tablename__}")
            self.db.commit()
        return update_res

