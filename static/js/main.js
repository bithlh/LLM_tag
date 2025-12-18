/**
 * 图片标签筛选与修正系统 - 前端主程序
 * 功能：图片管理、标签编辑、批量操作、数据导入导出
 */

class ImageTagSystem {
    constructor() {
        this.groups = [];
        this.currentFilter = 'all';
        this.init();
    }

    // ========== 初始化 ==========
    async init() {
        await this.loadGroups();
        this.bindEvents();
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
            groupSection.className = `group-section ${group.modified ? 'modified' : ''}`;
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

            // 构建标签HTML
            let tagsHtml = '';
            if (group.tags.length > 0) {
                group.tags.forEach(tag => {
                    tagsHtml += `
                        <div class="tag" data-group-id="${group.id}" data-tag="${tag}">
                            <span class="tag-text">${tag}</span>
                            <div class="tag-actions">
                                <button class="tag-btn edit-btn" data-tag="${tag}" title="编辑标签">✏️</button>
                                <button class="tag-btn delete-btn" data-tag="${tag}" title="删除标签">×</button>
                            </div>
                        </div>
                    `;
                });
            } else {
                tagsHtml = '<div class="empty-state"><p>暂无标签</p></div>';
            }

            groupSection.innerHTML = `
                <div class="group-header">
                    <h2 class="group-title">图片组 ${group.id}</h2>
                    <div class="group-stats">
                        <span>${group.images.length} 张图片</span>
                        <span>${group.tags.length} 个标签</span>
                        ${badges}
                    </div>
                </div>
                <div class="group-content">
                    <div class="group-images">
                        ${imagesHtml}
                    </div>
                    <div class="group-tags-section">
                        <div class="group-tags-header">
                            <h3 class="group-tags-title">标签管理</h3>
                            <div class="tag-actions">
                                <div class="add-tag-form">
                                    <input type="text" class="new-tag-input" data-group-id="${group.id}" placeholder="添加新标签..." />
                                    <button class="add-tag-btn btn btn-primary" data-group-id="${group.id}">添加</button>
                                </div>
                            </div>
                        </div>
                        <div class="tag-container" data-group-id="${group.id}">
                            ${tagsHtml}
                        </div>
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
            const addBtn = e.target.closest('.add-tag-btn');

            if (deleteBtn) {
                const tag = deleteBtn.dataset.tag;
                const groupId = parseInt(deleteBtn.closest('.group-section').dataset.groupId);
                this.deleteTag(groupId, tag);
            } else if (editBtn) {
                const tag = editBtn.dataset.tag;
                const groupId = parseInt(editBtn.closest('.group-section').dataset.groupId);
                this.showEditModal(groupId, tag);
            } else if (addBtn) {
                const groupId = parseInt(addBtn.dataset.groupId);
                this.addTag(groupId);
            }
        });

        // 输入框回车事件委托
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.classList.contains('new-tag-input')) {
                const groupId = parseInt(e.target.dataset.groupId);
                this.addTag(groupId);
            }
        });

        // 下一张按钮
        document.getElementById('nextBtn').addEventListener('click', () => {
            this.loadNextImage();
        });

        // 导入/导出按钮
        document.getElementById('importBtn').addEventListener('click', () => {
            this.showImportModal();
        });

        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportData();
        });

        // 批量操作按钮
        document.getElementById('batchDeleteBtn').addEventListener('click', () => {
            this.showBatchDeleteModal();
        });

        document.getElementById('batchReplaceBtn').addEventListener('click', () => {
            this.showBatchReplaceModal();
        });

        document.getElementById('statsBtn').addEventListener('click', () => {
            this.showStatsModal();
        });

        // 筛选按钮
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.renderImageList();
            });
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

        // 文件上传
        this.setupFileUpload();

        // JSON导入
        document.getElementById('importJsonBtn').addEventListener('click', () => {
            this.importFromJson();
        });

        // 编辑标签保存
        document.getElementById('saveEditBtn').addEventListener('click', () => {
            this.saveEditedTag();
        });

        // 批量删除确认
        document.getElementById('confirmBatchDeleteBtn').addEventListener('click', () => {
            this.confirmBatchDelete();
        });

        // 批量替换确认
        document.getElementById('confirmBatchReplaceBtn').addEventListener('click', () => {
            this.confirmBatchReplace();
        });
    }

    // ========== 添加标签 ==========
    async addTag(groupId) {
        const input = document.querySelector(`.new-tag-input[data-group-id="${groupId}"]`);
        const tag = input.value.trim();

        if (!tag) {
            this.showToast('请输入标签名称', 'warning');
            return;
        }

        try {
            const response = await fetch(`/api/groups/${groupId}/tags`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 已添加标签: ${tag}`, 'success');
                this.updateGroupTags(groupId, result.tags);
                input.value = '';
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('添加标签失败', 'error');
            console.error(error);
        }
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

    // ========== 更新组的标签显示 ==========
    updateGroupTags(groupId, tags) {
        // 更新本地数据
        const group = this.groups.find(g => g.id === groupId);
        if (group) {
            group.tags = tags;
            group.modified = true;
        }

        // 更新UI
        const tagContainer = document.querySelector(`.tag-container[data-group-id="${groupId}"]`);
        if (tagContainer) {
            if (tags.length > 0) {
                tagContainer.innerHTML = tags.map(tag => `
                    <div class="tag" data-group-id="${groupId}" data-tag="${tag}">
                        <span class="tag-text">${tag}</span>
                        <div class="tag-actions">
                            <button class="tag-btn edit-btn" data-tag="${tag}" title="编辑标签">✏️</button>
                            <button class="tag-btn delete-btn" data-tag="${tag}" title="删除标签">×</button>
                        </div>
                    </div>
                `).join('');
            } else {
                tagContainer.innerHTML = '<div class="empty-state"><p>暂无标签</p></div>';
            }
        }

        // 更新组头部统计信息
        const groupSection = document.querySelector(`.group-section[data-group-id="${groupId}"]`);
        if (groupSection) {
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

    // ========== 显示编辑标签弹窗 ==========
    showEditModal(groupId, tag) {
        document.getElementById('editOldTag').value = tag;
        document.getElementById('editNewTag').value = tag;
        document.getElementById('editModal').dataset.groupId = groupId;
        document.getElementById('editModal').classList.add('show');
        document.getElementById('editNewTag').focus();
    }

    // ========== 保存编辑的标签 ==========
    async saveEditedTag() {
        const oldTag = document.getElementById('editOldTag').value;
        const newTag = document.getElementById('editNewTag').value.trim();
        const groupId = parseInt(document.getElementById('editModal').dataset.groupId);

        if (!newTag) {
            this.showToast('标签名称不能为空', 'warning');
            return;
        }

        if (oldTag === newTag) {
            document.getElementById('editModal').classList.remove('show');
            return;
        }

        try {
            const response = await fetch(`/api/groups/${groupId}/tags/edit`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_tag: oldTag, new_tag: newTag })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 已将"${oldTag}"修改为"${newTag}"`, 'success');
                this.updateGroupTags(groupId, result.tags);
                document.getElementById('editModal').classList.remove('show');
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('修改标签失败', 'error');
            console.error(error);
        }
    }


    // ========== 加载下一张图片 ==========
    loadNextImage() {
        const currentIndex = this.images.findIndex(img => img.id === this.currentImageId);

        let nextIndex = currentIndex + 1;
        if (nextIndex >= this.images.length) {
            nextIndex = 0; // 循环到第一张
        }

        const nextImage = this.images[nextIndex];
        if (nextImage) {
            this.loadImage(nextImage.id);
        }
    }


    // ========== 更新统计信息 ==========
    updateStatistics() {
        const total = this.groups.length;
        document.getElementById('totalCount').textContent = total;
    }

    // ========== 文件上传设置 ==========
    setupFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            this.handleFileUpload(e.target.files);
        });

        // 拖拽上传
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFileUpload(e.dataTransfer.files);
        });
    }

    // ========== 处理文件上传 ==========
    async handleFileUpload(files) {
        const formData = new FormData();
        let validFiles = 0;

        for (let file of files) {
            if (file.type.startsWith('image/')) {
                formData.append('files', file);
                validFiles++;
            }
        }

        if (validFiles === 0) {
            this.showToast('请选择图片文件', 'warning');
            return;
        }

        const progressDiv = document.getElementById('uploadProgress');
        progressDiv.style.display = 'block';
        progressDiv.innerHTML = '<p>上传中...</p>';

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ 成功上传 ${result.uploaded} 个文件`, 'success');
                progressDiv.innerHTML = `
                    <div class="progress-item success">
                        <span>✓ 上传完成: ${result.uploaded} 个文件</span>
                    </div>
                    ${result.errors.length > 0 ? `<p style="color: var(--danger-color); margin-top: 10px;">失败: ${result.errors.length} 个文件</p>` : ''}
                `;

                // 清空文件输入
                document.getElementById('fileInput').value = '';
            } else {
                this.showToast('上传失败', 'error');
            }
        } catch (error) {
            this.showToast('上传失败: ' + error.message, 'error');
            console.error(error);
        }
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

    // ========== 导出数据 ==========
    async exportData() {
        console.log('开始导出数据...');
        try {
            console.log('发送请求到 /api/export');
            const response = await fetch('/api/export');
            console.log('收到响应:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('数据获取成功:', data);

            const blob = new Blob([JSON.stringify(data, null, 2)],
                { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            console.log('Blob创建成功');

            const a = document.createElement('a');
            a.href = url;
            a.download = `annotations_${new Date().toISOString().slice(0,10)}.json`;
            console.log('准备下载文件...');
            a.click();

            URL.revokeObjectURL(url);
            console.log('显示成功提示');
            this.showToast('✓ 数据导出成功！文件已下载到默认下载文件夹', 'success');
        } catch (error) {
            console.error('导出过程中出错:', error);
            this.showToast('导出失败: ' + error.message, 'error');
        }
    }

    // ========== 显示导入弹窗 ==========
    showImportModal() {
        document.getElementById('importModal').classList.add('show');
    }

    // ========== 显示批量删除弹窗 ==========
    showBatchDeleteModal() {
        document.getElementById('batchDeleteModal').classList.add('show');
        document.getElementById('batchDeleteTag').value = '';
        document.getElementById('batchDeleteTag').focus();
    }

    // ========== 确认批量删除 ==========
    async confirmBatchDelete() {
        const tag = document.getElementById('batchDeleteTag').value.trim();

        if (!tag) {
            this.showToast('请输入要删除的标签名称', 'warning');
            return;
        }

        if (!confirm(`确定要从所有图片中删除标签 "${tag}" 吗？\n此操作不可撤销！`)) {
            return;
        }

        try {
            const response = await fetch('/api/batch/delete-tag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tag })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ ${result.message}`, 'success');
                await this.loadGroups();
                document.getElementById('batchDeleteModal').classList.remove('show');
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('批量删除失败', 'error');
            console.error(error);
        }
    }

    // ========== 显示批量替换弹窗 ==========
    showBatchReplaceModal() {
        document.getElementById('batchReplaceModal').classList.add('show');
        document.getElementById('batchReplaceOldTag').value = '';
        document.getElementById('batchReplaceNewTag').value = '';
        document.getElementById('batchReplaceOldTag').focus();
    }

    // ========== 确认批量替换 ==========
    async confirmBatchReplace() {
        const oldTag = document.getElementById('batchReplaceOldTag').value.trim();
        const newTag = document.getElementById('batchReplaceNewTag').value.trim();

        if (!oldTag || !newTag) {
            this.showToast('请输入标签名称', 'warning');
            return;
        }

        if (!confirm(`确定要将所有图片中的 "${oldTag}" 替换为 "${newTag}" 吗？`)) {
            return;
        }

        try {
            const response = await fetch('/api/batch/replace-tag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_tag: oldTag, new_tag: newTag })
            });

            const result = await response.json();

            if (response.ok) {
                this.showToast(`✓ ${result.message}`, 'success');
                await this.loadGroups();
                document.getElementById('batchReplaceModal').classList.remove('show');
            } else {
                this.showToast(result.error, 'error');
            }
        } catch (error) {
            this.showToast('批量替换失败', 'error');
            console.error(error);
        }
    }

    // ========== 显示统计信息弹窗 ==========
    async showStatsModal() {
        document.getElementById('statsModal').classList.add('show');
        document.getElementById('statsContent').innerHTML = '<p>加载中...</p>';

        try {
            const response = await fetch('/api/statistics');
            const stats = await response.json();

            let tagDistHtml = '';
            for (let [tag, count] of Object.entries(stats.tag_distribution)) {
                tagDistHtml += `
                    <div class="tag-dist-item">
                        <span class="tag-dist-name">${tag}</span>
                        <span class="tag-dist-count">${count}</span>
                    </div>
                `;
            }

            document.getElementById('statsContent').innerHTML = `
                <div class="stats-grid">
                    <div class="stat-box">
                        <h4>总图片数</h4>
                        <div class="value">${stats.total_images}</div>
                    </div>
                    <div class="stat-box">
                        <h4>已修改</h4>
                        <div class="value">${stats.modified_images}</div>
                    </div>
                    <div class="stat-box">
                        <h4>标签总数</h4>
                        <div class="value">${stats.total_tags}</div>
                    </div>
                </div>

                <div class="tag-distribution">
                    <h3>标签分布 (前20)</h3>
                    ${tagDistHtml}
                </div>
            `;
        } catch (error) {
            document.getElementById('statsContent').innerHTML =
                '<p style="color: var(--danger-color);">加载统计信息失败</p>';
            console.error(error);
        }
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

    // 测试toast功能
    setTimeout(() => {
        console.log('测试toast功能');
        window.app.showToast('系统已就绪', 'success');
    }, 1000);
});
