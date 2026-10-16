INSERT INTO t_tool (tool_id, project_id, tool_display_name, tool_chinese_name, tool_desc, icon, type, metadata, call_mode, input_schema, output_schema, visibility, published, customize_node, creator, creator_id, is_share)
VALUES (
    'draw-box',
    '',
    '框选插件',
    '框选插件',
    '画布框选交互插件，支持区域面积计算、重叠检测和框选合并操作',
    'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHJ4PSIyIiBzdHJva2U9IiMxRTkwRkYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWRhc2hhcnJheT0iNCAyIiBmaWxsPSJyZ2JhKDMwLDE0NCwyNTUsMC4wOCkiLz48Y2lyY2xlIGN4PSI4IiBjeT0iOCIgcj0iMi41IiBmaWxsPSIjMUU5MEZGIi8+PGNpcmNsZSBjeD0iMzIiIGN5PSI4IiByPSIyLjUiIGZpbGw9IiMxRTkwRkYiLz48Y2lyY2xlIGN4PSI4IiBjeT0iMzIiIHI9IjIuNSIgZmlsbD0iIzFFOTBGRiIvPjxjaXJjbGUgY3g9IjMyIiBjeT0iMzIiIHI9IjIuNSIgZmlsbD0iIzFFOTBGRiIvPjwvc3ZnPg==',
    'inner',
    '{"component_type": "custom.draw_box"}',
    'custom',
    '{"type":"object","properties":{"operation":{"type":"string","enum":["calculate_area","find_overlaps","merge_boxes"],"description":"框选数据操作类型：calculate_area=计算面积, find_overlaps=检测重叠, merge_boxes=合并框选","default":"calculate_area"},"coordinates":{"type":"array","description":"坐标点列表（calculate_area 操作时为坐标点数组 [{x,y},...]；find_overlaps/merge_boxes 操作时为多组坐标点数组的数组 [[{x,y},...],...]）","items":{"type":"object","properties":{"x":{"type":"number","description":"X坐标"},"y":{"type":"number","description":"Y坐标"}},"required":["x","y"]}}},"required":["coordinates"]}',
    '{"type":"object","properties":{"output":{"type":"object","description":"处理结果","properties":{"operation":{"type":"string","description":"执行的操作类型"},"area":{"type":"number","description":"框选区域面积（calculate_area）"},"center":{"type":"object","description":"中心点坐标（calculate_area）","properties":{"x":{"type":"number","description":"X坐标"},"y":{"type":"number","description":"Y坐标"}}},"bounds":{"type":"object","description":"边界范围（calculate_area）","properties":{"min_x":{"type":"number","description":"最小X坐标"},"max_x":{"type":"number","description":"最大X坐标"},"min_y":{"type":"number","description":"最小Y坐标"},"max_y":{"type":"number","description":"最大Y坐标"}}},"point_count":{"type":"integer","description":"坐标点数量（calculate_area）"},"overlap_pairs":{"type":"array","description":"重叠对列表（find_overlaps）","items":{"type":"object","properties":{"box_a":{"type":"integer","description":"框选组A序号"},"box_b":{"type":"integer","description":"框选组B序号"}}}},"overlap_count":{"type":"integer","description":"重叠对数量（find_overlaps）"},"merged_boxes":{"type":"array","description":"合并后的框选区域列表（merge_boxes）","items":{"type":"object","properties":{"min_x":{"type":"number","description":"最小X坐标"},"max_x":{"type":"number","description":"最大X坐标"},"min_y":{"type":"number","description":"最小Y坐标"},"max_y":{"type":"number","description":"最大Y坐标"}}}},"box_count":{"type":"integer","description":"合并后框选区域数量（merge_boxes）"}}}}}',
    'global',
    1,
    1,
    'system',
    'system',
    0
);
