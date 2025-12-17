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
            "images": []
        }
        save_data(sample_data)

    # 扫描images目录，添加新发现的图片
    scan_and_add_images()


def scan_and_add_images():
    """扫描images目录，自动添加新发现的图片"""
    try:
        # 获取所有图片文件
        image_files = []
        if os.path.exists(IMAGE_FOLDER):
            for filename in os.listdir(IMAGE_FOLDER):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    image_files.append(filename)

        # 加载现有数据
        data = load_data()
        existing_filenames = {img['filename'] for img in data['images']}

        # 获取当前最大ID
        max_id = max((img['id'] for img in data['images']), default=0)

        # 添加新发现的图片
        new_images_added = 0
        for filename in image_files:
            if filename not in existing_filenames:
                max_id += 1
                new_image = {
                    "id": max_id,
                    "filename": filename,
                    "tags": []
                }
                data['images'].append(new_image)
                new_images_added += 1

        # 保存更新后的数据
        if new_images_added > 0:
            save_data(data)
            print(f"自动添加了 {new_images_added} 张新图片到数据库")

    except Exception as e:
        print(f"扫描图片目录时出错: {e}")


def load_data():
    """加载标注数据"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
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


@app.route('/api/images', methods=['GET'])
def get_images():
    """获取所有图片和标签信息"""
    # 确保扫描到最新的图片
    scan_and_add_images()
    data = load_data()
    return jsonify(data)


@app.route('/api/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    """获取单个图片信息"""
    data = load_data()
    for img in data['images']:
        if img['id'] == image_id:
            return jsonify(img)
    return jsonify({'error': 'Image not found'}), 404


@app.route('/api/images/<int:image_id>/tags', methods=['DELETE'])
def delete_tag(image_id):
    """删除指定图片的某个标签"""
    tag = request.json.get('tag')
    if not tag:
        return jsonify({'error': 'Tag not provided'}), 400

    data = load_data()
    for img in data['images']:
        if img['id'] == image_id:
            if tag in img['tags']:
                img['tags'].remove(tag)
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{tag}" removed',
                    'remaining_tags': img['tags']
                })
            else:
                return jsonify({'error': 'Tag not found'}), 404

    return jsonify({'error': 'Image not found'}), 404


@app.route('/api/images/<int:image_id>/tags', methods=['POST'])
def add_tag(image_id):
    """添加新标签"""
    tag = request.json.get('tag')
    if not tag:
        return jsonify({'error': 'Tag not provided'}), 400

    data = load_data()
    for img in data['images']:
        if img['id'] == image_id:
            if tag not in img['tags']:
                img['tags'].append(tag)
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{tag}" added',
                    'tags': img['tags']
                })
            else:
                return jsonify({'error': 'Tag already exists'}), 400

    return jsonify({'error': 'Image not found'}), 404




@app.route('/api/images/<int:image_id>/tags/edit', methods=['PUT'])
def edit_tag(image_id):
    """编辑标签"""
    old_tag = request.json.get('old_tag')
    new_tag = request.json.get('new_tag')

    if not old_tag or not new_tag:
        return jsonify({'error': 'Both old_tag and new_tag are required'}), 400

    data = load_data()
    for img in data['images']:
        if img['id'] == image_id:
            if old_tag in img['tags']:
                img['tags'] = [new_tag if tag == old_tag else tag for tag in img['tags']]
                img['modified'] = True
                save_data(data)
                return jsonify({
                    'success': True,
                    'message': f'Tag "{old_tag}" changed to "{new_tag}"',
                    'tags': img['tags']
                })
            else:
                return jsonify({'error': 'Old tag not found'}), 404

    return jsonify({'error': 'Image not found'}), 404


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
    """导入JSON数据"""
    try:
        import_data = request.get_json()
        if not import_data or 'images' not in import_data:
            return jsonify({'error': 'Invalid data format'}), 400

        # 合并导入的数据
        data = load_data()
        existing_ids = {img['id'] for img in data['images']}
        max_id = max(existing_ids) if existing_ids else 0

        imported = 0
        for img in import_data['images']:
            if 'filename' in img:
                if img.get('id') and img['id'] not in existing_ids:
                    # 保留原有ID
                    new_img = {
                        'id': img['id'],
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'primary_category': img.get('primary_category', ''),
                        'confidence': img.get('confidence', []),
                        'attributes': img.get('attributes', {'通用特征': {}, '专属特征': {}}),
                        'video_description': img.get('video_description', ''),
                        'reasoning': img.get('reasoning', ''),
                        'reviewed': img.get('reviewed', False)
                    }
                    data['images'].append(new_img)
                    imported += 1
                elif not img.get('id'):
                    # 分配新ID
                    max_id += 1
                    new_img = {
                        'id': max_id,
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'primary_category': img.get('primary_category', ''),
                        'confidence': img.get('confidence', []),
                        'attributes': img.get('attributes', {'通用特征': {}, '专属特征': {}}),
                        'video_description': img.get('video_description', ''),
                        'reasoning': img.get('reasoning', ''),
                        'reviewed': img.get('reviewed', False)
                    }
                    data['images'].append(new_img)
                    imported += 1

        save_data(data)
        return jsonify({'imported': imported})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/file', methods=['POST'])
def import_from_file():
    """从文件导入标注数据"""
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
        existing_ids = {img['id'] for img in data['images']}
        max_id = max(existing_ids) if existing_ids else 0

        imported = 0
        for img in import_data['images']:
            if 'filename' in img:
                if img.get('id') and img['id'] not in existing_ids:
                    # 保留原有ID
                    new_img = {
                        'id': img['id'],
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'primary_category': img.get('primary_category', ''),
                        'confidence': img.get('confidence', []),
                        'attributes': img.get('attributes', {'通用特征': {}, '专属特征': {}}),
                        'video_description': img.get('video_description', ''),
                        'reasoning': img.get('reasoning', ''),
                        'reviewed': img.get('reviewed', False)
                    }
                    data['images'].append(new_img)
                    imported += 1
                elif not img.get('id'):
                    # 分配新ID
                    max_id += 1
                    new_img = {
                        'id': max_id,
                        'filename': img['filename'],
                        'tags': img.get('tags', []),
                        'primary_category': img.get('primary_category', ''),
                        'confidence': img.get('confidence', []),
                        'attributes': img.get('attributes', {'通用特征': {}, '专属特征': {}}),
                        'video_description': img.get('video_description', ''),
                        'reasoning': img.get('reasoning', ''),
                        'reviewed': img.get('reviewed', False)
                    }
                    data['images'].append(new_img)
                    imported += 1

        save_data(data)
        return jsonify({'imported': imported})

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    data = load_data()
    images = data['images']

    # 计算基础统计
    total_images = len(images)
    modified_images = len([img for img in images if img.get('modified', False)])

    # 计算标签统计
    tag_counts = {}
    total_tags = 0
    for img in images:
        for tag in img.get('tags', []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            total_tags += 1

    # 按使用频率排序标签
    tag_distribution = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    return jsonify({
        'total_images': total_images,
        'modified_images': modified_images,
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

    for img in data['images']:
        if tag in img.get('tags', []):
            img['tags'].remove(tag)
            img['modified'] = True
            deleted_count += 1

    save_data(data)

    return jsonify({
        'message': f'从 {deleted_count} 张图片中删除了标签 "{tag}"'
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

    for img in data['images']:
        if old_tag in img.get('tags', []):
            img['tags'] = [new_tag if t == old_tag else t for t in img['tags']]
            img['modified'] = True
            replaced_count += 1

    save_data(data)

    return jsonify({
        'message': f'在 {replaced_count} 张图片中将 "{old_tag}" 替换为 "{new_tag}"'
    })


if __name__ == '__main__':
    init_sample_data()
    # 启动时扫描一次图片目录
    scan_and_add_images()
    app.run(debug=True, host='127.0.0.1', port=5000)
