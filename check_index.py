import json

with open('data_base_v3/multimodal_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

figs_dict = data.get('figures', {})
print(f'图片总数: {len(figs_dict)}')
print(f'类型: {type(figs_dict)}')

if figs_dict:
    # 获取第一个键值对
    first_key = list(figs_dict.keys())[0]
    first_fig = figs_dict[first_key]
    
    print(f'\n示例图片 (key={first_key}):')
    print(f'  数据: {first_fig}')
    
    # 检查是否有 image_path 字段
    if 'image_path' in first_fig:
        path = first_fig['image_path']
        print(f'\n  image_path: {path}')
        import os
        print(f'  路径存在: {os.path.exists(path)}')
    else:
        print(f'\n  ⚠ 没有image_path字段!')
        print(f'  可用字段: {list(first_fig.keys())}')

