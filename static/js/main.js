/**
 * 图片标签筛选与修正系统 - 前端主程序
 * 功能：图片管理、标签编辑、批量操作、数据导入导出
 */

class ImageTagSystem {
    constructor() {
        this.groups = [];
        this.currentFilter = 'all';
        this.pendingImportData = null;
        this.init();
    }

    // ========== 初始化 ==========
    async init() {
        await this.loadGroups();
        this.bindEvents();
        this.bindButtonEvents();
        this.bindUrlImportEvents();
        this.updateStatistics();
    }

    // ========== 数据加载 ==========
    async loadGroups() {
        try {
            const response = await fetch('/api/groups');
            const data = await response.json();
            this.groups = data.groups || [];
            this.renderAllGroups();
            this.updateStatistics();
        } catch (error) {
            this.showToast('加载图片组失败: ' + error.message, 'error');
            console.error('加载失败:', error);
        }
    }

    // ========== 渲染所有组 ==========
    renderAllGroups() {
        const container = document.getElementById('groupsContent');

        // 根据筛选条件过滤组
        let filteredGroups = this.groups;
        if (this.currentFilter === 'modified') {
            filteredGroups = this.groups.filter(group => group.modified);
        }

        if (filteredGroups.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📂 暂无图片组</p>
                    <p class="hint">请上传图片或导入数据</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        filteredGroups.forEach(group => {
            const groupSection = document.createElement('div');
            groupSection.className = `group-section ${group.modified ? 'modified' : ''} ${group.id === 1 ? 'group-template' : ''}`;
            groupSection.dataset.groupId = group.id;

            let badges = '';
            if (group.modified) {
                badges += '<span class="badge badge-warning">✏️</span>';
            }
            if (group.reviewed) {
                badges += '<span class="badge badge-success">✓</span>';
            }

            // 构建图片HTML
            let imagesHtml = '';
            group.images.forEach(img => {
                imagesHtml += `
                    <div class="group-image-item">
                        <img src="/static/images/${img.filename}"
                             alt="${img.filename}"
                             onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22%3E%3Crect fill=%22%23ddd%22 width=%22400%22 height=%22300%22/%3E%3Ctext fill=%22%23999%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2220%22%3E图片未找到%3C/text%3E%3C/svg%3E'">
                        <div class="image-filename">${img.filename}</div>
                    </div>
                `;
            });

            // 构建头部信息HTML（主要类别和置信度）
            let headerInfoHtml = '';
            if (group.primary_category) {
                headerInfoHtml += `<span class="category-badge">${group.primary_category}</span>`;
            }
            if (group.confidence && group.confidence.length > 0) {
                headerInfoHtml += group.confidence.map(conf => `<span class="confidence-item">${conf}</span>`).join('');
            }

            // 构建结构化信息HTML（属性和标签）
            let structuredInfoHtml = '';

            // 属性和标签合并在一个大白框里
            structuredInfoHtml += `
                <div class="combined-section">
                    <div class="attributes-header">
                        <h4 class="info-title">通用特征</h4>
                        <h4 class="info-title">专属特征</h4>
                        <h4 class="info-title">标签</h4>
                    </div>
                    <div class="attributes-content">
                        <div class="attributes-column">
                            ${group.attributes ? Object.entries(group.attributes['通用特征'] || {}).map(([key, values]) =>
                                values.map(value =>
                                    `<div class="attribute-tag" data-group-id="${group.id}" data-category="通用特征" data-key="${key}" data-value="${value}">
                                        <span class="attribute-tag-text">${key}: ${value}</span>
                                        <button class="attribute-delete-btn" title="删除">×</button>
                                    </div>`
                                ).join('')
                            ).join('') : ''}
                        </div>
                        <div class="attributes-column">
                            ${group.attributes ? Object.entries(group.attributes['专属特征'] || {}).map(([key, values]) =>
                                values.map(value =>
                                    `<div class="attribute-tag" data-group-id="${group.id}" data-category="专属特征" data-key="${key}" data-value="${value}">
                                        <span class="attribute-tag-text">${key}: ${value}</span>
                                        <button class="attribute-delete-btn" title="删除">×</button>
                                    </div>`
                                ).join('')
                            ).join('') : ''}
                        </div>
                        <div class="attributes-column">
                            ${group.tags && group.tags.length > 0 ? group.tags.map(tag =>
                                `<div class="attribute-tag" data-group-id="${group.id}" data-tag="${tag}">
                                    <span class="attribute-tag-text">${tag}</span>
                                    <button class="attribute-delete-btn" title="删除">×</button>
                                </div>`
                            ).join('') : '<div class="empty-state"><p>暂无标签</p></div>'}
                        </div>
                    </div>
                </div>
            `;

            // 视频描述
            if (group.video_description) {
                structuredInfoHtml += `
                    <div class="info-section">
                        <h4 class="info-title">
                            <span class="title-icon">📹</span>
                            视频描述
                        </h4>
                        <div class="info-content">
                            <div class="description-text">
                                ${group.video_description}
                            </div>
                        </div>
                    </div>
                `;
            }

            // 推理过程
            if (group.reasoning) {
                structuredInfoHtml += `
                    <div class="info-section">
                        <h4 class="info-title reasoning-title">
                            <span class="title-icon">🧠</span>
                            推理过程
                        </h4>
                        <div class="info-content">
                            <div class="description-text reasoning-text">
                                ${group.reasoning}
                            </div>
                        </div>
                    </div>
                `;
            }

            groupSection.innerHTML = `
                <div class="group-header">
                    <div class="header-left">
                        <h2 class="group-title">图片组 ${group.id}</h2>
                        <div class="group-stats">
                            <span>${group.images.length} 张图片</span>
                            <span>${group.tags ? group.tags.length : 0} 个标签</span>
                            ${badges}
                        </div>
                    </div>
                    <div class="header-right">
                        ${headerInfoHtml}
                    </div>
                </div>
                <div class="group-content">
                    <div class="group-images">
                        ${imagesHtml}
                    </div>
                    <div class="group-tags-section">
                        ${structuredInfoHtml}
                    </div>
                </div>
            `;

            container.appendChild(groupSection);
        });
    }

    // ========== 事件绑定 ==========
    bindEvents() {
        // 标签容器事件委托 - 处理所有组的标签操作
        document.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.delete-btn');
            const editBtn = e.target.closest('.edit-btn');
            const attributeDeleteBtn = e.target.closest('.attribute-delete-btn');

            if (deleteBtn) {
                const tag = deleteBtn.dataset.tag;
                const groupId = parseInt(deleteBtn.closest('.group-section').dataset.groupId);
                this.deleteTag(groupId, tag);
            } else if (attributeDeleteBtn) {
                const groupId = parseInt(attributeDeleteBtn.closest('.group-section').dataset.groupId);
                const attributeTag = attributeDeleteBtn.closest('.attribute-tag');
                const category = attributeTag.dataset.category;

                if (category) {
                    // 属性删除
                    const key = attributeTag.dataset.key;
                    const value = attributeTag.dataset.value;
                    this.deleteAttribute(groupId, category, key, value);
                } else {
                    // 标签删除
                    const tag = attributeTag.dataset.tag;
                    this.deleteTag(groupId, tag);
                }
            }
        });

        // 弹窗关闭
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.classList.remove('show');
                }
            });
        });

        // 点击弹窗外部关闭
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('show');
                }
            });
        });
    }

    // ========== 绑定按钮事件 ==========
    bindButtonEvents() {
        // 导出按钮
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportData();
            });
        }

        // 导入按钮
        const importBtn = document.getElementById('importBtn');
        if (importBtn) {
            importBtn.addEventListener('click', () => {
                this.showImportModal();
            });
        }

        // 导入标签页切换
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                e.target.classList.add('active');
                document.getElementById(tabName + 'Tab').classList.add('active');
            });
        });

        // JSON导入
        document.getElementById('importJsonBtn').addEventListener('click', () => {
            this.importFromJson();
        });

        // JSON文件导入
        document.getElementById('selectFileBtn').addEventListener('click', () => {
            document.getElementById('jsonFileInput').click();
        });

        document.getElementById('jsonFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('selectedFileName').textContent = file.name;
            }
        });

        document.getElementById('importFileBtn').addEventListener('click', () => {
            this.importFromFile();
        });
    }

    // ========== 绑定URL导入事件 ==========
    bindUrlImportEvents() {
        // 选择文件按钮
        document.getElementById('selectUrlFileBtn').addEventListener('click', () => {
            document.getElementById('urlJsonFileInput').click();
        });

        // 文件选择变化
        document.getElementById('urlJsonFileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('urlFileName').textContent = file.name;
                await this.previewUrlJson(file);
            }
        });

        // 导入按钮
        document.getElementById('importUrlBtn').addEventListener('click', () => {
            this.importFromUrlJson();
        });
    }

    // ========== 预览JSON文件内容 ==========
    async previewUrlJson(file) {
        try {
            const text = await file.text();
            const jsonData = JSON.parse(text);

            // 验证JSON格式
            if (!jsonData.groups || !Array.isArray(jsonData.groups)) {
                this.showToast('JSON格式错误：缺少groups数组', 'error');
                document.getElementById('urlPreview').style.display = 'none';
                document.getElementById('importUrlBtn').disabled = true;
                return;
            }

            // 统计信息
            let totalGroups = jsonData.groups.length;
            let totalImages = 0;
            let totalTags = 0;
            let totalAttributes = 0;

            jsonData.groups.forEach(group => {
                totalImages += group.images ? group.images.length : 0;
                totalTags += group.tags ? group.tags.length : 0;
                
                if (group.attributes) {
                    Object.values(group.attributes).forEach(category => {
                        Object.values(category).forEach(values => {
                            totalAttributes += values.length;
                        });
                    });
                }
            });

            // 显示预览
            document.getElementById('urlPreviewContent').innerHTML = `
                <div class="url-preview-item">
                    <span>📦 图片组数量：</span>
                    <strong>${totalGroups} 组</strong>
                </div>
                <div class="url-preview-item">
                    <span>🖼️ 图片总数：</span>
                    <strong>${totalImages} 张</strong>
                </div>
                <div class="url-preview-item">
                    <span>🏷️ 标签总数：</span>
                    <strong>${totalTags} 个</strong>
                </div>
                <div class="url-preview-item">
                    <span>⚙️ 属性总数：</span>
                    <strong>${totalAttributes} 个</strong>
                </div>
            `;

            document.getElementById('urlPreview').style.display = 'block';
            document.getElementById('importUrlBtn').disabled = false;

            // 保存JSON数据供导入使用
            this.pendingImportData = jsonData;

        } catch (error) {
            this.showToast('JSON解析失败: ' + error.message, 'error');
            document.getElementById('urlPreview').style.display = 'none';
            document.getElementById('importUrlBtn').disabled = true;
        }
    }

    // ========== 从URL JSON导入 ==========
    async importFromUrlJson() {
        if (!this.pendingImportData) {
            this.showToast('请先选择JSON文件', 'warning');
            return;
        }

        const progressDiv = document.getElementById('importProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const importBtn = document.getElementById('importUrlBtn');

        progressDiv.style.display = 'block';
        importBtn.disabled = true;
        progressFill.style.width = '0%';
        progressText.textContent = '准备导入...';

        try {
            const response = await fetch('/api/import/url-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.pendingImportData)
            });

            if (!response.ok) {
                throw new Error('服务器响应错误');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let result = null;
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (let line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.progress !== undefined) {
                                progressFill.style.width = data.progress + '%';
                                progressText.textContent = data.message || `进度: ${data.progress}%`;
                            }
                            
                            if (data.complete) {
                                result = data;
                            }
                        } catch (e) {
                            console.error('解析进度数据失败:', e);
                        }
                    }
                }
            }

            if (result && result.success) {
                this.showToast(
                    `✓ 成功导入 ${result.groups_created} 个组，${result.images_downloaded} 张图片`, 
                    'success'
                );
                
                if (result.errors && result.errors.length > 0) {
                    console.warn('导入过程中的错误:', result.errors);
                    this.showToast(
                        `注意：${result.errors.length} 张图片下载失败，详见控制台`, 
                        'warning'
                    );
                }

                await this.loadGroups();
                document.getElementById('importModal').classList.remove('show');
                
                // 重置状态
                this.resetUrlImportForm();
            } else {
                throw new Error(result?.error || '导入失败');
            }

        } catch (error) {
            this.showToast('导入失败: ' + error.message, 'error');
            console.error('导入错误:', error);
        } finally {
            importBtn.disabled = false;
        }
    }

    // ========== 重置URL导入表单 ==========
    resetUrlImportForm() {
        document.getElementById('urlJsonFileInput').value = '';
        document.getElementById('urlFileName').textContent = '';
        document.getElementById('urlPreview').style.display = 'none';
        document.getElementById('importProgress').style.display = 'none';
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('importUrlBtn').disabled = true;
        this.pendingImportData = null;
    }

    // ========== 删除标签 ==========
    async deleteTag(groupId, tag) {
        if (!confirm(`确定要删除标签 "${tag}" 吗？`)) {
            return;
        }

        try {
            const response = await fetch(`/api/groups/${groupId}/tags`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 已删除标签: ${tag}`, 'success');
                this.updateGroupTags(groupId, result.remaining_tags);
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('删除标签失败', 'error');
            console.error(error);
        }
    }

    // ========== 删除属性 ==========
    async deleteAttribute(groupId, category, key, value) {
        if (!confirm(`确定要删除属性 "${key}: ${value}" 吗？`)) {
            return;
        }

        try {
            const response = await fetch(`/api/groups/${groupId}/attributes`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: category,
                    key: key,
                    value: value
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 已删除属性 "${key}: ${value}"`, 'success');
                this.updateGroupAttributes(groupId, result.attributes);
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('删除属性失败', 'error');
            console.error(error);
        }
    }

    // ========== 更新组的标签显示 ==========
    updateGroupTags(groupId, tags) {
        // 更新本地数据
        const group = this.groups.find(g => g.id === groupId);
        if (group) {
            group.tags = tags;
            group.modified = true;
        }

        // 更新UI - 标签在combined-section的第三列
        const groupSection = document.querySelector(`.group-section[data-group-id="${groupId}"]`);
        if (groupSection) {
            const attributesColumns = groupSection.querySelectorAll('.attributes-column');
            const tagsColumn = attributesColumns[2];
            
            if (tagsColumn) {
                if (tags && tags.length > 0) {
                    tagsColumn.innerHTML = tags.map(tag =>
                        `<div class="attribute-tag" data-group-id="${groupId}" data-tag="${tag}">
                            <span class="attribute-tag-text">${tag}</span>
                            <button class="attribute-delete-btn" title="删除">×</button>
                        </div>`
                    ).join('');
                } else {
                    tagsColumn.innerHTML = '<div class="empty-state"><p>暂无标签</p></div>';
                }
            }

            // 更新组头部统计信息
            const statsEl = groupSection.querySelector('.group-stats');
            const imagesCount = group ? group.images.length : 0;
            statsEl.innerHTML = `
                <span>${imagesCount} 张图片</span>
                <span>${tags.length} 个标签</span>
                ${group && group.modified ? '<span class="badge badge-warning">✏️</span>' : ''}
                ${group && group.reviewed ? '<span class="badge badge-success">✓</span>' : ''}
            `;
        }

        this.updateStatistics();
    }

    // ========== 更新组的属性显示 ==========
    updateGroupAttributes(groupId, attributes) {
        // 更新本地数据
        const group = this.groups.find(g => g.id === groupId);
        if (group) {
            group.attributes = attributes;
            group.modified = true;
        }

        // 更新UI
        const groupSection = document.querySelector(`.group-section[data-group-id="${groupId}"]`);
        if (groupSection) {
            const attributesContent = groupSection.querySelector('.attributes-content');
            if (attributesContent) {
                attributesContent.innerHTML = `
                    <div class="attributes-column">
                        ${attributes && Object.entries(attributes['通用特征'] || {}).map(([key, values]) =>
                            values.map(value =>
                                `<div class="attribute-tag" data-group-id="${groupId}" data-category="通用特征" data-key="${key}" data-value="${value}">
                                    <span class="attribute-tag-text">${key}: ${value}</span>
                                    <button class="attribute-delete-btn" title="删除">×</button>
                                </div>`
                            ).join('')
                        ).join('')}
                    </div>
                    <div class="attributes-column">
                        ${attributes && Object.entries(attributes['专属特征'] || {}).map(([key, values]) =>
                            values.map(value =>
                                `<div class="attribute-tag" data-group-id="${groupId}" data-category="专属特征" data-key="${key}" data-value="${value}">
                                    <span class="attribute-tag-text">${key}: ${value}</span>
                                    <button class="attribute-delete-btn" title="删除">×</button>
                                </div>`
                            ).join('')
                        ).join('')}
                    </div>
                    <div class="attributes-column">
                        ${group.tags && group.tags.length > 0 ? group.tags.map(tag =>
                            `<div class="attribute-tag" data-group-id="${groupId}" data-tag="${tag}">
                                <span class="attribute-tag-text">${tag}</span>
                                <button class="attribute-delete-btn" title="删除">×</button>
                            </div>`
                        ).join('') : '<div class="empty-state"><p>暂无标签</p></div>'}
                    </div>
                `;
            }
        }

        this.updateStatistics();
    }

    // ========== 更新统计信息 ==========
    updateStatistics() {
        const total = this.groups.length;
        document.getElementById('totalCount').textContent = total;
    }

    // ========== 从JSON导入 ==========
    async importFromJson() {
        const jsonText = document.getElementById('jsonInput').value.trim();

        if (!jsonText) {
            this.showToast('请输入JSON数据', 'warning');
            return;
        }

        try {
            const data = JSON.parse(jsonText);

            const response = await fetch('/api/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 成功导入 ${result.imported} 张图片，创建 ${result.groups_created} 个组`, 'success');
                await this.loadGroups();
                document.getElementById('importModal').classList.remove('show');
                document.getElementById('jsonInput').value = '';
            } else {
                this.showToast('导入失败: ' + result.error, 'error');
            }
        } catch (error) {
            this.showToast('JSON格式错误: ' + error.message, 'error');
        }
    }

    // ========== 从文件导入JSON ==========
    async importFromFile() {
        const fileInput = document.getElementById('jsonFileInput');
        const file = fileInput.files[0];

        if (!file) {
            this.showToast('请先选择JSON文件', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/import/file', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 成功导入 ${result.imported} 张图片，创建 ${result.groups_created} 个组`, 'success');
                await this.loadGroups();
                document.getElementById('importModal').classList.remove('show');
                fileInput.value = '';
                document.getElementById('selectedFileName').textContent = '';
            } else {
                this.showToast('导入失败: ' + result.error, 'error');
            }
        } catch (error) {
            this.showToast('导入失败: ' + error.message, 'error');
        }
    }

    // ========== 导出数据 ==========
    async exportData() {
        try {
            const response = await fetch('/api/export');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = `annotations_${new Date().toISOString().slice(0,10)}.json`;
            a.click();

            URL.revokeObjectURL(url);
            this.showToast('✓ 数据导出成功！', 'success');
        } catch (error) {
            console.error('导出错误:', error);
            this.showToast('导出失败: ' + error.message, 'error');
        }
    }

    // ========== 显示导入弹窗 ==========
    showImportModal() {
        document.getElementById('importModal').classList.add('show');
    }

    // ========== Toast 提示 ==========
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 4000);
    }
}

// ========== 启动应用 ==========
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ImageTagSystem();
    console.log('✓ 图片标签筛选系统已启动');
});
