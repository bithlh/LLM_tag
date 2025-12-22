# -*- coding: utf-8 -*-
"""
图片标签筛选与修正系统 - 后端服务
功能：图片管理、标签编辑、URL图片下载、数据导入导出
"""

from flask import Flask, render_template, jsonify, request, Response, stream_with_context
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import uuid
import time

app = Flask(__name__)

# 添加CORS支持（如果需要）
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ========== 配置 ==========
IMAGE_FOLDER = 'static/images'
DATA_FILE = 'data/annotations.json'

# 确保数据文件夹存在
os.makedirs('data', exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)


# ========== 数据初始化 ==========
def init_sample_data():
    """初始化示例数据"""
    if not os.path.exists(DATA_FILE):
        sample_data = {
            "groups": []
        }
        save_data(sample_data)


def scan_and_add_images():
    """扫描images目录，自动添加新发现的图片并分组"""
    try:
        # 获取所有图片文件
        image_files = []
        if os.path.exists(IMAGE_FOLDER):
            for filename in os.listdir(IMAGE_FOLDER):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    image_files.append(filename)

        # 加载现有数据
        data = load_data()

        # 收集所有现有图片文件名
        existing_filenames = set()
        for group in data.get('groups', []):
            for img in group.get('images', []):
                existing_filenames.add(img['filename'])

        # 获取当前最大ID
        max_id = 0
        for group in data.get('groups', []):
            for img in group.get('images', []):
                max_id = max(max_id, img.get('id', 0))

        # 找出新图片
        new_files = [f for f in image_files if f not in existing_filenames]

        if not new_files:
            return

        # 将新图片两两分组添加到现有数据中
        new_groups_added = 0
        for i in range(0, len(new_files), 2):
            group_images = new_files[i:i+2]
            group_imgs = []
            for filename in group_images:
                max_id += 1
                group_imgs.append({
                    "id": max_id,
                    "filename": filename
                })

            new_group = {
                "id": len(data.get('groups', [])) + new_groups_added + 1,
                "images": group_imgs,
                "primary_category": "",
                "confidence": [],
                "attributes": {
                    "通用特征": {},
                    "专属特征": {}
                },
                "tags": [],
                "video_description": "",
                "reasoning": "",
                "reviewed": False,
                "modified": False
            }
            data['groups'].append(new_group)
            new_groups_added += 1

        # 保存更新后的数据
        if new_groups_added > 0:
            save_data(data)
            print(f"✓ 自动添加了 {len(new_files)} 张新图片，组成 {new_groups_added} 个新组")

    except Exception as e:
        print(f"✗ 扫描图片目录时出错: {e}")


def load_data():
    """加载标注数据"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 确保数据结构兼容
            if 'groups' not in data:
                data['groups'] = []
            return data
    except FileNotFoundError:
        init_sample_data()
        return load_data()


def save_data(data):
    """保存标注数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 路由：页面渲染 ==========
@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')


# ========== 路由：获取数据 ==========
@app.route('/api/groups', methods=['GET'])
def get_groups():
    """获取图片组和标签信息，支持分页"""
    scan_and_add_images()
    data = load_data()

    # 获取分页参数
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    # 确保参数合理
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 10

    groups = data.get('groups', [])
    total_groups = len(groups)

    # 计算分页
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    # 获取当前页的数据
    paginated_groups = groups[start_index:end_index]

    # 构建响应
    response = {
        'groups': paginated_groups,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_groups': total_groups,
            'total_pages': (total_groups + per_page - 1) // per_page,
            'has_next': end_index < total_groups,
            'has_prev': page > 1
        }
    }

    return jsonify(response)


@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """获取单个组信息"""
    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            return jsonify(group)
    return jsonify({'error': 'Group not found'}), 404


@app.route('/api/groups/<int:group_id>/delete', methods=['POST', 'OPTIONS'])
def delete_group(group_id):
    """删除整个图片组"""
    try:
        # 处理CORS预检请求
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200

        print(f"收到删除请求: group_id={group_id}, method={request.method}")

        # 验证group_id是否有效
        if not isinstance(group_id, int) or group_id <= 0:
            return jsonify({'error': 'Invalid group ID'}), 400

        data = load_data()
        print(f"当前组数量: {len(data.get('groups', []))}")

        for i, group in enumerate(data.get('groups', [])):
            print(f"检查组 {group['id']}")
            if group['id'] == group_id:
                # 获取要删除的图片信息（可能是本地文件名或远程URL）
                images_info = []
                for img in group.get('images', []):
                    if 'filename' in img:
                        # 本地图片
                        images_info.append({'type': 'local', 'filename': img['filename']})
                    elif 'url' in img:
                        # 远程图片
                        images_info.append({'type': 'remote', 'url': img['url']})
                    else:
                        # 其他格式
                        images_info.append({'type': 'unknown', 'data': img})

                # 从数据中删除组
                deleted_group = data['groups'].pop(i)

                # 保存数据
                save_data(data)

                print(f"成功删除图片组 {group_id}")

                # 注意：这里不删除物理文件，因为：
                # 1. 远程图片无法删除
                # 2. 本地图片可能被其他地方引用
                # 用户可以手动清理不需要的文件

                return jsonify({
                    'success': True,
                    'message': f'图片组 {group_id} 已删除',
                    'deleted_images': len(images_info),
                    'images_info': images_info  # 返回图片信息，让用户了解删除了什么
                })

        print(f"未找到图片组 {group_id}")
        return jsonify({'error': 'Group not found'}), 404

    except Exception as e:
        print(f"删除图片组时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500


# ========== 路由：标签操作 ==========
@app.route('/api/groups/<int:group_id>/tags', methods=['DELETE'])
def delete_tag(group_id):
    """删除指定组的某个标签"""
    tag = request.json.get('tag')
    if not tag:
        return jsonify({'error': 'Tag not provided'}), 400

    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            if tag in group.get('tags', []):
                group['tags'].remove(tag)
                group['modified'] = True
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{tag}" removed',
                    'remaining_tags': group['tags']
                })
            else:
                return jsonify({'error': 'Tag not found'}), 404

    return jsonify({'error': 'Group not found'}), 404


@app.route('/api/groups/<int:group_id>/tags', methods=['POST'])
def add_tag(group_id):
    """添加新标签"""
    tag = request.json.get('tag')
    if not tag:
        return jsonify({'error': 'Tag not provided'}), 400

    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            if tag not in group.get('tags', []):
                group['tags'].append(tag)
                group['modified'] = True
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{tag}" added',
                    'tags': group['tags']
                })
            else:
                return jsonify({'error': 'Tag already exists'}), 400

    return jsonify({'error': 'Group not found'}), 404


@app.route('/api/groups/<int:group_id>/tags/edit', methods=['PUT'])
def edit_tag(group_id):
    """编辑标签"""
    old_tag = request.json.get('old_tag')
    new_tag = request.json.get('new_tag')

    if not old_tag or not new_tag:
        return jsonify({'error': 'Both old_tag and new_tag are required'}), 400

    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            if old_tag in group.get('tags', []):
                group['tags'] = [new_tag if tag == old_tag else tag for tag in group['tags']]
                group['modified'] = True
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{old_tag}" changed to "{new_tag}"',
                    'tags': group['tags']
                })
            else:
                return jsonify({'error': 'Old tag not found'}), 404

    return jsonify({'error': 'Group not found'}), 404


# ========== 路由：属性操作 ==========
@app.route('/api/groups/<int:group_id>/attributes', methods=['DELETE'])
def delete_attribute(group_id):
    """删除指定组的属性"""
    category = request.json.get('category')
    key = request.json.get('key')
    value = request.json.get('value')

    if not category or not key or not value:
        return jsonify({'error': 'Category, key and value are required'}), 400

    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            attributes = group.get('attributes', {})
            if category in attributes and key in attributes[category]:
                if value in attributes[category][key]:
                    attributes[category][key].remove(value)
                    # 如果该key下没有值了，删除整个key
                    if not attributes[category][key]:
                        del attributes[category][key]
                    group['modified'] = True
                    save_data(data)
                    return jsonify({
                        'success': True,
                        'message': f'Attribute "{key}: {value}" removed',
                        'attributes': attributes
                    })
                else:
                    return jsonify({'error': 'Attribute value not found'}), 404
            else:
                return jsonify({'error': 'Attribute key not found'}), 404

    return jsonify({'error': 'Group not found'}), 404


# ========== 路由：导入导出 ==========
@app.route('/api/export', methods=['GET'])
def export_data():
    """导出清洗后的数据"""
    data = load_data()
    return jsonify(data)


@app.route('/api/import', methods=['POST'])
def import_data():
    """导入JSON数据并自动分组"""
    try:
        import_data = request.get_json()
        if not import_data:
            return jsonify({'error': 'No data provided'}), 400

        # 合并导入的数据
        data = load_data()

        # 获取当前最大ID
        max_group_id = max([g['id'] for g in data.get('groups', [])], default=0)
        max_image_id = 0
        for group in data.get('groups', []):
            for img in group.get('images', []):
                max_image_id = max(max_image_id, img.get('id', 0))

        imported_groups = 0

        # 检查数据格式：如果是example.json格式的单个图片组
        if 'output' in import_data and 'task' in import_data:
            print("检测到example.json格式的数据")
            # 处理单个图片组数据
            output_data = import_data.get('output', {})

            # 检查是否已存在相同UID的图片组
            import_uid = import_data.get('task', {}).get('uid')
            if import_uid:
                existing_group = None
                for group in data.get('groups', []):
                    if group.get('task', {}).get('uid') == import_uid:
                        existing_group = group
                        break

                if existing_group:
                    print(f"发现重复UID {import_uid}，跳过导入（现有组ID: {existing_group['id']}）")
                    return jsonify({
                        'success': False,
                        'message': f'UID {import_uid} 已存在，跳过导入',
                        'existing_group_id': existing_group['id']
                    })

            # 从cover_url和live_url创建图片
            images = []
            if import_data.get('task', {}).get('cover_url'):
                max_image_id += 1
                images.append({
                    'id': max_image_id,
                    'url': import_data['task']['cover_url'],
                    'type': 'cover'
                })

            if import_data.get('task', {}).get('live_url'):
                max_image_id += 1
                images.append({
                    'id': max_image_id,
                    'url': import_data['task']['live_url'],
                    'type': 'live'
                })

            if images:
                max_group_id += 1
                new_group = {
                    'id': max_group_id,
                    'task': import_data.get('task', {}),
                    'provider': import_data.get('provider', ''),
                    'model': import_data.get('model', ''),
                    'timestamp': import_data.get('timestamp', ''),
                    'elapsed_seconds': import_data.get('elapsed_seconds', 0),
                    'usage': import_data.get('usage', {}),
                    'images': images,
                    'primary_category': output_data.get('primary_category', ''),
                    'confidence': output_data.get('confidence', []),
                    'attributes': output_data.get('attributes', {
                        '通用特征': {},
                        '专属特征': {}
                    }),
                    'tags': output_data.get('tags', []),
                    'video_description': output_data.get('video_description', ''),
                    'reasoning': output_data.get('reasoning', ''),
                    'push_title': output_data.get('push_title', ''),
                    '封面图包含文字': output_data.get('封面图包含文字', ''),
                    '直播图包含文字': output_data.get('直播图包含文字', ''),
                    'reviewed': False,
                    'modified': False
                }
                data['groups'].append(new_group)
                imported_groups += 1
                print(f"成功导入单个图片组，ID: {max_group_id}")

        # 检查是否是原来的images数组格式
        elif 'images' in import_data:
            print("检测到传统images数组格式的数据")
            # 收集现有图片ID
            existing_image_ids = set()
            for group in data.get('groups', []):
                for img in group.get('images', []):
                    existing_image_ids.add(img['id'])

            # 收集需要导入的图片
            new_images = []
            for img in import_data['images']:
                if 'filename' in img:
                    if img.get('id') and img['id'] not in existing_image_ids:
                        # 保留原有ID
                        new_images.append({
                            'id': img['id'],
                            'filename': img['filename'],
                            'tags': img.get('tags', []),
                            'reviewed': img.get('reviewed', False)
                        })
                    elif not img.get('id'):
                        # 分配新ID
                        max_image_id += 1
                        new_images.append({
                            'id': max_image_id,
                            'filename': img['filename'],
                            'tags': img.get('tags', []),
                            'reviewed': img.get('reviewed', False)
                        })

            # 将新图片两两分组
            for i in range(0, len(new_images), 2):
                group_images = new_images[i:i+2]

                # 合并tags
                group_tags = []
                for img in group_images:
                    group_tags.extend(img.get('tags', []))
                group_tags = list(set(group_tags))  # 去重

                max_group_id += 1
                new_group = {
                    'id': max_group_id,
                    'images': [{'id': img['id'], 'filename': img['filename']} for img in group_images],
                    'primary_category': '',
                    'confidence': [],
                    'attributes': {
                        '通用特征': {},
                        '专属特征': {}
                    },
                    'tags': group_tags,
                    'video_description': '',
                    'reasoning': '',
                    'reviewed': any(img.get('reviewed', False) for img in group_images),
                    'modified': False
                }
                data['groups'].append(new_group)
                imported_groups += 1

        else:
            return jsonify({'error': 'Unsupported data format. Expected either "images" array or single group with "output" field'}), 400

        if imported_groups > 0:
            save_data(data)
            print(f"成功导入 {imported_groups} 个图片组")
            return jsonify({
                'success': True,
                'message': f'成功导入 {imported_groups} 个图片组',
                'groups_created': imported_groups
            })
        else:
            return jsonify({'error': 'No valid data to import'}), 400

    except Exception as e:
        print(f"导入数据时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500


def process_single_group_item(item_data, data, max_group_id_ref, max_image_id_ref):
    """处理单个图片组对象的导入"""
    # 检查是否已存在相同UID的图片组
    import_uid = item_data.get('task', {}).get('uid')
    if import_uid:
        existing_group = None
        for group in data.get('groups', []):
            if group.get('task', {}).get('uid') == import_uid:
                existing_group = group
                break

        if existing_group:
            print(f"发现重复UID {import_uid}，跳过导入（现有组ID: {existing_group['id']}）")
            return False  # 不算作成功导入

    # 从cover_url和live_url创建图片
    images = []
    if item_data.get('task', {}).get('cover_url'):
        max_image_id_ref[0] += 1
        images.append({
            'id': max_image_id_ref[0],
            'url': item_data['task']['cover_url'],
            'type': 'cover'
        })

    if item_data.get('task', {}).get('live_url'):
        max_image_id_ref[0] += 1
        images.append({
            'id': max_image_id_ref[0],
            'url': item_data['task']['live_url'],
            'type': 'live'
        })

    if images:
        max_group_id_ref[0] += 1
        output_data = item_data.get('output', {})
        new_group = {
            'id': max_group_id_ref[0],
            'task': item_data.get('task', {}),
            'provider': item_data.get('provider', ''),
            'model': item_data.get('model', ''),
            'timestamp': item_data.get('timestamp', ''),
            'elapsed_seconds': item_data.get('elapsed_seconds', 0),
            'usage': item_data.get('usage', {}),
            'images': images,
            'primary_category': output_data.get('primary_category', ''),
            'confidence': output_data.get('confidence', []),
            'attributes': output_data.get('attributes', {
                '通用特征': {},
                '专属特征': {}
            }),
            'tags': output_data.get('tags', []),
            'video_description': output_data.get('video_description', ''),
            'reasoning': output_data.get('reasoning', ''),
            'push_title': output_data.get('push_title', ''),
            '封面图包含文字': output_data.get('封面图包含文字', ''),
            '直播图包含文字': output_data.get('直播图包含文字', ''),
            'reviewed': False,
            'modified': False
        }
        data['groups'].append(new_group)
        print(f"成功导入单个图片组，ID: {max_group_id_ref[0]}, UID: {import_uid}")
        return True

    return False


@app.route('/api/import/file', methods=['POST'])
def import_from_file():
    """从文件导入标注数据并自动分组"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not (file.filename.endswith('.json') or file.filename.endswith('.jsonl')):
            return jsonify({'error': 'Only JSON and JSONL files are allowed'}), 400

        # 读取文件内容
        file_content = file.read().decode('utf-8')

        # 检查是否是JSON Lines格式（.jsonl文件）
        if file.filename.endswith('.jsonl'):
            print("检测到JSON Lines格式的文件")
            # 解析JSON Lines格式
            json_objects = []
            for line_num, line in enumerate(file_content.strip().split('\n'), 1):
                line = line.strip()
                if line:  # 跳过空行
                    try:
                        json_obj = json.loads(line)
                        json_objects.append(json_obj)
                    except json.JSONDecodeError as e:
                        return jsonify({'error': f'JSON解析错误在第{line_num}行: {str(e)}'}), 400

            if not json_objects:
                return jsonify({'error': 'JSONL文件中没有有效的JSON对象'}), 400

            import_data = json_objects  # 对于JSONL，直接使用对象数组
        else:
            # 处理单个JSON对象
            import_data = json.loads(file_content)
            if not import_data:
                return jsonify({'error': 'Empty JSON file'}), 400

        # 合并导入的数据
        data = load_data()

        # 获取当前最大ID
        max_group_id = max([g['id'] for g in data.get('groups', [])], default=0)
        max_image_id = 0
        for group in data.get('groups', []):
            for img in group.get('images', []):
                max_image_id = max(max_image_id, img.get('id', 0))

        imported_groups = 0

        # 处理数据：如果是JSON Lines数组，每个元素都是一个图片组对象
        if isinstance(import_data, list):
            print(f"处理JSON Lines格式，包含 {len(import_data)} 个对象")
            max_group_id_ref = [max_group_id]
            max_image_id_ref = [max_image_id]
            for item_index, item_data in enumerate(import_data):
                try:
                    print(f"处理第 {item_index + 1} 个对象...")
                    success = process_single_group_item(item_data, data, max_group_id_ref, max_image_id_ref)
                    if success:
                        imported_groups += 1
                except Exception as e:
                    print(f"处理第 {item_index + 1} 个对象时出错: {str(e)}")
                    # 继续处理其他对象，不中断整个导入过程

            # 更新外部变量
            max_group_id = max_group_id_ref[0]
            max_image_id = max_image_id_ref[0]

        # 检查数据格式：如果是example.json格式的单个图片组
        elif 'output' in import_data and 'task' in import_data:
            print("检测到example.json格式的文件数据")
            max_group_id_ref = [max_group_id]
            max_image_id_ref = [max_image_id]
            success = process_single_group_item(import_data, data, max_group_id_ref, max_image_id_ref)
            if success:
                imported_groups += 1
                max_group_id = max_group_id_ref[0]
                max_image_id = max_image_id_ref[0]

        # 检查是否是原来的images数组格式
        elif 'images' in import_data:
            print("检测到传统images数组格式的文件数据")
            # 收集现有图片ID
            existing_image_ids = set()
            for group in data.get('groups', []):
                for img in group.get('images', []):
                    existing_image_ids.add(img['id'])

            # 收集需要导入的图片
            new_images = []
            for img in import_data['images']:
                if 'filename' in img:
                    if img.get('id') and img['id'] not in existing_image_ids:
                        new_images.append({
                            'id': img['id'],
                            'filename': img['filename'],
                            'tags': img.get('tags', []),
                            'reviewed': img.get('reviewed', False)
                        })
                    elif not img.get('id'):
                        max_image_id += 1
                        new_images.append({
                            'id': max_image_id,
                            'filename': img['filename'],
                            'tags': img.get('tags', []),
                            'reviewed': img.get('reviewed', False)
                        })

            # 将新图片两两分组
            for i in range(0, len(new_images), 2):
                group_images = new_images[i:i+2]

                # 合并tags
                group_tags = []
                for img in group_images:
                    group_tags.extend(img.get('tags', []))
                group_tags = list(set(group_tags))

                max_group_id += 1
                new_group = {
                    'id': max_group_id,
                    'images': [{'id': img['id'], 'filename': img['filename']} for img in group_images],
                    'primary_category': '',
                    'confidence': [],
                    'attributes': {
                        '通用特征': {},
                        '专属特征': {}
                    },
                    'tags': group_tags,
                    'video_description': '',
                    'reasoning': '',
                    'reviewed': any(img.get('reviewed', False) for img in group_images),
                    'modified': False
                }
                data['groups'].append(new_group)
                imported_groups += 1

        else:
            return jsonify({'error': 'Unsupported JSON format. Expected either "images" array or single group with "output" field'}), 400

        if imported_groups > 0:
            save_data(data)
            print(f"成功从文件导入 {imported_groups} 个图片组")
            return jsonify({
                'success': True,
                'message': f'成功导入 {imported_groups} 个图片组',
                'groups_created': imported_groups
            })
        else:
            return jsonify({'error': 'No valid data to import from file'}), 400

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== 路由：URL导入（核心功能） ==========
@app.route('/api/import/url-json', methods=['POST'])
def import_url_json():
    """从包含URL的JSON导入图片组"""
    def generate():
        try:
            import_data = request.get_json()
            if not import_data or 'groups' not in import_data:
                yield f"data: {json.dumps({'error': 'Invalid data format', 'complete': True, 'success': False})}\n\n"
                return

            data = load_data()
            
            # 获取现有的最大组ID和图片ID
            max_group_id = max([g['id'] for g in data.get('groups', [])], default=0)
            max_image_id = 0
            for group in data.get('groups', []):
                for img in group.get('images', []):
                    max_image_id = max(max_image_id, img.get('id', 0))

            total_groups = len(import_data['groups'])
            groups_created = 0
            images_downloaded = 0
            errors = []

            # 逐个处理组
            for idx, group_data in enumerate(import_data['groups']):
                try:
                    # 发送进度更新
                    progress = int((idx / total_groups) * 100)
                    yield f"data: {json.dumps({'progress': progress, 'message': f'正在处理第 {idx+1}/{total_groups} 组...'})}\n\n"

                    new_group_images = []
                    
                    # 处理组内的每张图片
                    for img_data in group_data.get('images', []):
                        # 获取图片URL（支持 url 和 filename 字段）
                        image_url = img_data.get('url') or img_data.get('filename')
                        
                        if not image_url:
                            errors.append(f"组 {idx+1}: 图片缺少URL")
                            continue

                        # 下载图片
                        try:
                            # 生成唯一文件名
                            ext = image_url.split('.')[-1].split('?')[0].lower()
                            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                                ext = 'jpg'
                            
                            filename = f"{uuid.uuid4().hex}.{ext}"
                            file_path = os.path.join(IMAGE_FOLDER, filename)

                            # 下载图片（设置超时和请求头）
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                            response = requests.get(
                                image_url, 
                                timeout=30, 
                                stream=True, 
                                headers=headers,
                                verify=False  # 如果遇到SSL问题
                            )
                            response.raise_for_status()

                            # 保存图片
                            with open(file_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)

                            max_image_id += 1
                            new_group_images.append({
                                'id': max_image_id,
                                'filename': filename
                            })
                            images_downloaded += 1

                        except requests.exceptions.RequestException as e:
                            errors.append(f"下载失败 {image_url}: {str(e)}")
                            continue
                        except Exception as e:
                            errors.append(f"保存失败 {image_url}: {str(e)}")
                            continue

                    # 如果成功下载了图片，创建组
                    if new_group_images:
                        max_group_id += 1
                        new_group = {
                            'id': max_group_id,
                            'images': new_group_images,
                            'primary_category': group_data.get('primary_category', ''),
                            'confidence': group_data.get('confidence', []),
                            'attributes': group_data.get('attributes', {
                                '通用特征': {},
                                '专属特征': {}
                            }),
                            'tags': group_data.get('tags', []),
                            'video_description': group_data.get('video_description', ''),
                            'reasoning': group_data.get('reasoning', ''),
                            'reviewed': group_data.get('reviewed', False),
                            'modified': False
                        }
                        data['groups'].append(new_group)
                        groups_created += 1
                    else:
                        errors.append(f"组 {idx+1}: 没有成功下载任何图片")

                except Exception as e:
                    errors.append(f"处理组 {idx+1} 失败: {str(e)}")
                    continue

            # 保存数据
            save_data(data)

            # 发送完成消息
            yield f"data: {json.dumps({'progress': 100, 'message': '✓ 导入完成！', 'complete': True, 'success': True, 'groups_created': groups_created, 'images_downloaded': images_downloaded, 'errors': errors})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'complete': True, 'success': False})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ========== 路由：文件上传 ==========
@app.route('/api/upload', methods=['POST'])
def upload_files():
    """上传图片文件"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    uploaded = 0
    errors = []

    for file in files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(IMAGE_FOLDER, filename)
            try:
                file.save(file_path)
                uploaded += 1
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        else:
            errors.append(f"{file.filename}: Invalid file type")

    # 重新扫描图片目录以更新数据库
    scan_and_add_images()

    return jsonify({
        'uploaded': uploaded,
        'errors': errors
    })


def allowed_file(filename):
    """检查文件是否为允许的图片格式"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========== 路由：统计信息 ==========
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    data = load_data()
    groups = data.get('groups', [])

    # 计算基础统计
    total_groups = len(groups)
    total_images = sum(len(group.get('images', [])) for group in groups)
    modified_groups = len([group for group in groups if group.get('modified', False)])

    # 计算标签统计
    tag_counts = {}
    total_tags = 0
    for group in groups:
        for tag in group.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            total_tags += 1

    # 按使用频率排序标签（前20个）
    tag_distribution = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20])

    return jsonify({
        'total_groups': total_groups,
        'total_images': total_images,
        'modified_groups': modified_groups,
        'total_tags': total_tags,
        'tag_distribution': tag_distribution
    })


@app.route('/api/groups/stats', methods=['GET'])
def get_groups_stats():
    """获取图片组分页统计信息"""
    scan_and_add_images()
    data = load_data()
    groups = data.get('groups', [])

    per_page = int(request.args.get('per_page', 10))
    if per_page < 1 or per_page > 100:
        per_page = 10

    total_groups = len(groups)
    total_pages = (total_groups + per_page - 1) // per_page

    return jsonify({
        'total_groups': total_groups,
        'total_pages': total_pages,
        'per_page': per_page
    })


# ========== 路由：批量操作 ==========
@app.route('/api/batch/delete-tag', methods=['POST'])
def batch_delete_tag():
    """批量删除标签"""
    tag = request.json.get('tag')
    if not tag:
        return jsonify({'error': 'Tag not provided'}), 400

    data = load_data()
    deleted_count = 0

    for group in data.get('groups', []):
        if tag in group.get('tags', []):
            group['tags'].remove(tag)
            group['modified'] = True
            deleted_count += 1

    save_data(data)

    return jsonify({
        'message': f'从 {deleted_count} 个组中删除了标签 "{tag}"'
    })


@app.route('/api/batch/replace-tag', methods=['POST'])
def batch_replace_tag():
    """批量替换标签"""
    old_tag = request.json.get('old_tag')
    new_tag = request.json.get('new_tag')

    if not old_tag or not new_tag:
        return jsonify({'error': 'Both old_tag and new_tag are required'}), 400

    data = load_data()
    replaced_count = 0

    for group in data.get('groups', []):
        if old_tag in group.get('tags', []):
            group['tags'] = [new_tag if t == old_tag else t for t in group['tags']]
            group['modified'] = True
            replaced_count += 1

    save_data(data)

    return jsonify({
        'message': f'在 {replaced_count} 个组中将 "{old_tag}" 替换为 "{new_tag}"'
    })


# ========== 主程序入口 ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 图片标签筛选系统启动中...")
    print("=" * 60)
    
    init_sample_data()
    scan_and_add_images()
    
    print("✓ 数据初始化完成")
    print("✓ 服务器地址: http://127.0.0.1:5000")
    print("=" * 60)
    
    # 禁用SSL验证警告（如果需要）
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    app.run(debug=True, host='127.0.0.1', port=5000)
