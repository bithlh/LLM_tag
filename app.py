from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 配置
IMAGE_FOLDER = 'static/images'
DATA_FILE = 'data/annotations.json'

# 确保数据文件夹存在
os.makedirs('data', exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)


# 自动扫描图片目录并初始化数据
def init_sample_data():
    if not os.path.exists(DATA_FILE):
        sample_data = {
            "groups": []
        }
        save_data(sample_data)

    # 扫描images目录，添加新发现的图片
    scan_and_add_images()


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
                "tags": []
            }
            data['groups'].append(new_group)
            new_groups_added += 1

        # 保存更新后的数据
        if new_groups_added > 0:
            save_data(data)
            print(f"自动添加了 {len(new_files)} 张新图片，组成 {new_groups_added} 个新组")

    except Exception as e:
        print(f"扫描图片目录时出错: {e}")


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


@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')


@app.route('/api/groups', methods=['GET'])
def get_groups():
    """获取所有图片组和标签信息"""
    # 确保扫描到最新的图片
    scan_and_add_images()
    data = load_data()
    return jsonify(data)


@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """获取单个组信息"""
    data = load_data()
    for group in data.get('groups', []):
        if group['id'] == group_id:
            return jsonify(group)
    return jsonify({'error': 'Group not found'}), 404


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


@app.route('/api/export', methods=['GET'])
def export_data():
    """导出清洗后的数据"""
    data = load_data()
    return jsonify(data)


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
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/import', methods=['POST'])
def import_data():
    """导入JSON数据并自动分组"""
    try:
        import_data = request.get_json()
        if not import_data or 'images' not in import_data:
            return jsonify({'error': 'Invalid data format'}), 400

        # 合并导入的数据
        data = load_data()

        # 收集现有图片ID
        existing_image_ids = set()
        for group in data.get('groups', []):
            for img in group.get('images', []):
                existing_image_ids.add(img['id'])

        # 获取当前最大ID
        max_id = 0
        for group in data.get('groups', []):
            for img in group.get('images', []):
                max_id = max(max_id, img.get('id', 0))

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
                    max_id += 1
                    new_images.append({
                        'id': max_id,
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'reviewed': img.get('reviewed', False)
                    })

        # 将新图片两两分组
        imported_groups = 0
        for i in range(0, len(new_images), 2):
            group_images = new_images[i:i+2]

            # 合并tags
            group_tags = []
            for img in group_images:
                group_tags.extend(img.get('tags', []))
            group_tags = list(set(group_tags))  # 去重

            new_group = {
                'id': len(data.get('groups', [])) + imported_groups + 1,
                'images': [{'id': img['id'], 'filename': img['filename']} for img in group_images],
                'tags': group_tags,
                'reviewed': any(img.get('reviewed', False) for img in group_images)
            }
            data['groups'].append(new_group)
            imported_groups += 1

        save_data(data)
        return jsonify({'imported': len(new_images), 'groups_created': imported_groups})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/file', methods=['POST'])
def import_from_file():
    """从文件导入标注数据并自动分组"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.json'):
            return jsonify({'error': 'Only JSON files are allowed'}), 400

        # 读取文件内容
        file_content = file.read().decode('utf-8')
        import_data = json.loads(file_content)

        if not import_data or 'images' not in import_data:
            return jsonify({'error': 'Invalid JSON format'}), 400

        # 合并导入的数据
        data = load_data()

        # 收集现有图片ID
        existing_image_ids = set()
        for group in data.get('groups', []):
            for img in group.get('images', []):
                existing_image_ids.add(img['id'])

        # 获取当前最大ID
        max_id = 0
        for group in data.get('groups', []):
            for img in group.get('images', []):
                max_id = max(max_id, img.get('id', 0))

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
                    max_id += 1
                    new_images.append({
                        'id': max_id,
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'reviewed': img.get('reviewed', False)
                    })

        # 将新图片两两分组
        imported_groups = 0
        for i in range(0, len(new_images), 2):
            group_images = new_images[i:i+2]

            # 合并tags
            group_tags = []
            for img in group_images:
                group_tags.extend(img.get('tags', []))
            group_tags = list(set(group_tags))  # 去重

            new_group = {
                'id': len(data.get('groups', [])) + imported_groups + 1,
                'images': [{'id': img['id'], 'filename': img['filename']} for img in group_images],
                'tags': group_tags,
                'reviewed': any(img.get('reviewed', False) for img in group_images)
            }
            data['groups'].append(new_group)
            imported_groups += 1

        save_data(data)
        return jsonify({'imported': len(new_images), 'groups_created': imported_groups})

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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

    # 按使用频率排序标签
    tag_distribution = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    return jsonify({
        'total_groups': total_groups,
        'total_images': total_images,
        'modified_groups': modified_groups,
        'total_tags': total_tags,
        'tag_distribution': tag_distribution
    })


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


if __name__ == '__main__':
    init_sample_data()
    # 启动时扫描一次图片目录
    scan_and_add_images()
    app.run(debug=True, host='127.0.0.1', port=5000)
