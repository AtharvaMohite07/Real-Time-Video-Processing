// Real-time Video Processing Frontend JavaScript

class VideoProcessor {
    constructor() {
        this.isProcessing = false;
        this.currentFilters = [];
        this.advancedFeaturesEnabled = false;
        this.cloudConnected = false;
        this.stats = {
            fps: 0,
            latency: 0,
            objects: 0,
            faces: 0,
            frames_processed: 0,
            motion_events: 0
        };
        this.initialize();
    }

    initialize() {
        this.setupEventListeners();
        this.startStatsUpdate();
        this.connectWebSocket();
        this.checkSystemStatus();
    }

    setupEventListeners() {
        // Processing controls
        document.getElementById('startBtn')?.addEventListener('click', () => this.startProcessing());
        document.getElementById('stopBtn')?.addEventListener('click', () => this.stopProcessing());
        document.getElementById('resetBtn')?.addEventListener('click', () => this.resetFilters());

        // Filter controls
        document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.toggleFilter(e.target.value, e.target.checked));
        });

        // File upload
        document.getElementById('videoUpload')?.addEventListener('change', (e) => this.handleFileUpload(e));

        // Camera controls
        document.getElementById('cameraBtn')?.addEventListener('click', () => this.startCamera());
        document.getElementById('webcamSelect')?.addEventListener('change', (e) => this.switchCamera(e.target.value));

        // Settings
        document.querySelectorAll('.setting-slider').forEach(slider => {
            slider.addEventListener('input', (e) => this.updateSetting(e.target.name, e.target.value));
        });
        
        // Advanced features
        document.getElementById('advanced-analysis-toggle')?.addEventListener('change', (e) => {
            this.toggleAdvancedAnalysis(e.target.checked);
        });
        
        document.getElementById('cloud-upload-btn')?.addEventListener('click', () => {
            this.uploadToCloud();
        });
        
        document.getElementById('cloud-view-btn')?.addEventListener('click', () => {
            this.viewCloudUploads();
        });

        // New API endpoints
        document.getElementById('download-models-btn')?.addEventListener('click', () => {
            this.downloadModels();
        });

        document.getElementById('export-data-btn')?.addEventListener('click', () => {
            this.exportData();
        });

        document.getElementById('health-check-btn')?.addEventListener('click', () => {
            this.checkSystemHealth();
        });
        
        // Check for advanced features availability
        this.checkAdvancedFeaturesAvailability();
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            this.updateSystemStatusUI(data);
            this.advancedFeaturesEnabled = data.advanced_analyzer_available;
            this.cloudConnected = data.cloud_config_complete;
            
        } catch (error) {
            console.error('System status check failed:', error);
            this.showNotification('System status check failed', 'error');
        }
    }

    updateSystemStatusUI(healthData) {
        // Update various status indicators in the UI
        const statusElements = {
            'api-status': healthData.status === 'healthy' ? 'Online' : 'Offline',
            'advanced-status': healthData.advanced_analyzer_available ? 'Available' : 'Unavailable',
            'cloud-connection-status': healthData.cloud_config_complete ? 'Connected' : 'Not Configured'
        };

        Object.entries(statusElements).forEach(([id, status]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = status;
                element.className = `badge ${this.getStatusBadgeClass(status)}`;
            }
        });
    }

    getStatusBadgeClass(status) {
        const statusMap = {
            'Online': 'bg-success',
            'Available': 'bg-success',
            'Connected': 'bg-success',
            'Offline': 'bg-danger',
            'Unavailable': 'bg-warning',
            'Not Configured': 'bg-warning'
        };
        return statusMap[status] || 'bg-secondary';
    }

    async startProcessing() {
        if (this.isProcessing) return;

        try {
            this.isProcessing = true;
            this.updateUI();

            const response = await fetch('/start_processing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filters: this.currentFilters,
                    settings: this.getSettings()
                })
            });

            if (response.ok) {
                this.showNotification('Processing started', 'success');
            } else {
                throw new Error('Failed to start processing');
            }
        } catch (error) {
            this.showNotification(`Error: ${error.message}`, 'error');
            this.isProcessing = false;
            this.updateUI();
        }
    }

    async stopProcessing() {
        if (!this.isProcessing) return;

        try {
            const response = await fetch('/stop_processing', { method: 'POST' });
            if (response.ok) {
                this.isProcessing = false;
                this.updateUI();
                this.showNotification('Processing stopped', 'info');
            }
        } catch (error) {
            this.showNotification(`Error stopping: ${error.message}`, 'error');
        }
    }

    resetFilters() {
        this.currentFilters = [];
        document.querySelectorAll('.filter-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateFilterDisplay();
    }

    toggleFilter(filter, enabled) {
        if (enabled) {
            if (!this.currentFilters.includes(filter)) {
                this.currentFilters.push(filter);
            }
        } else {
            this.currentFilters = this.currentFilters.filter(f => f !== filter);
        }
        this.updateFilterDisplay();
        
        if (this.isProcessing) {
            this.updateProcessingFilters();
        }
    }

    async updateProcessingFilters() {
        try {
            await fetch('/update_filters', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filters: this.currentFilters })
            });
        } catch (error) {
            console.error('Failed to update filters:', error);
        }
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('video', file);

        try {
            this.showNotification('Uploading video...', 'info');
            const response = await fetch('/upload_video', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                this.showNotification('Video uploaded successfully', 'success');
                this.loadVideo(result.video_path);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            this.showNotification(`Upload error: ${error.message}`, 'error');
        }
    }

    async startCamera() {
        try {
            const response = await fetch('/start_camera', { method: 'POST' });
            if (response.ok) {
                this.showNotification('Camera started', 'success');
                document.getElementById('videoFeed').src = '/video_feed';
            }
        } catch (error) {
            this.showNotification(`Camera error: ${error.message}`, 'error');
        }
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'stats':
                this.updateStats(data.stats);
                break;
            case 'detection':
                this.updateDetections(data.detections);
                break;
            case 'error':
                this.showNotification(data.message, 'error');
                break;
        }
    }

    updateStats(stats) {
        this.stats = { ...this.stats, ...stats };
        document.getElementById('fpsValue').textContent = stats.fps?.toFixed(1) || '0.0';
        document.getElementById('latencyValue').textContent = `${stats.avg_processing_time_ms?.toFixed(0) || '0'}ms`;
        document.getElementById('objectsValue').textContent = stats.objects || '0';
        document.getElementById('facesValue').textContent = stats.faces_detected || '0';

        // Update performance bars
        this.updatePerformanceBar('fpsBar', stats.fps, 30);
        this.updatePerformanceBar('latencyBar', 100 - (stats.avg_processing_time_ms / 10), 100);
        
        // Update advanced metrics if available
        this.updateAdvancedMetrics(stats);
    }

    updatePerformanceBar(barId, value, max) {
        const bar = document.getElementById(barId);
        if (bar) {
            const percentage = Math.min((value / max) * 100, 100);
            bar.style.width = `${percentage}%`;
        }
    }

    updateDetections(detections) {
        const container = document.getElementById('detectionsContainer');
        if (!container) return;

        container.innerHTML = '';
        detections.forEach(detection => {
            const item = document.createElement('div');
            item.className = 'detection-item';
            item.innerHTML = `
                <span class="detection-type">${detection.type}</span>
                <span class="detection-confidence">${(detection.confidence * 100).toFixed(1)}%</span>
            `;
            container.appendChild(item);
        });
    }

    updateFilterDisplay() {
        const display = document.getElementById('activeFilters');
        if (display) {
            display.innerHTML = this.currentFilters.map(filter => 
                `<span class="badge bg-primary me-1">${filter}</span>`
            ).join('');
        }
    }

    updateUI() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusIndicator = document.getElementById('statusIndicator');

        if (startBtn) startBtn.disabled = this.isProcessing;
        if (stopBtn) stopBtn.disabled = !this.isProcessing;
        
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${this.isProcessing ? 'status-processing' : 'status-offline'}`;
        }
    }

    getSettings() {
        const settings = {};
        document.querySelectorAll('.setting-slider').forEach(slider => {
            settings[slider.name] = parseFloat(slider.value);
        });
        return settings;
    }

    updateSetting(name, value) {
        const display = document.getElementById(`${name}Value`);
        if (display) {
            display.textContent = value;
        }

        if (this.isProcessing) {
            // Update settings in real-time
            fetch('/update_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [name]: parseFloat(value) })
            }).catch(console.error);
        }
    }

    startStatsUpdate() {
        setInterval(() => {
            if (this.isProcessing) {
                this.fetchStats();
            }
        }, 1000);
    }

    async fetchStats() {
        try {
            const response = await fetch('/stats');
            if (response.ok) {
                const stats = await response.json();
                this.updateStats(stats);
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    loadVideo(videoPath) {
        const videoElement = document.getElementById('videoFeed');
        if (videoElement) {
            videoElement.src = videoPath;
        }
    }

    async checkAdvancedFeaturesAvailability() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            this.advancedFeaturesEnabled = data.advanced_analyzer_available;
            this.cloudConnected = data.cloud_config_complete;
            
            // Update UI based on availability
            this.updateFeatureAvailability();
            
        } catch (error) {
            console.error('Failed to check advanced features:', error);
            this.advancedFeaturesEnabled = false;
            this.cloudConnected = false;
        }
    }

    updateFeatureAvailability() {
        const advancedToggle = document.getElementById('advanced-analysis-toggle');
        const cloudButtons = document.querySelectorAll('#cloud-upload-btn, #cloud-view-btn');
        
        if (advancedToggle) {
            advancedToggle.disabled = !this.advancedFeaturesEnabled;
            if (!this.advancedFeaturesEnabled) {
                advancedToggle.parentElement.parentElement.style.opacity = '0.5';
            }
        }
        
        cloudButtons.forEach(btn => {
            if (btn) {
                btn.disabled = !this.cloudConnected;
                if (!this.cloudConnected) {
                    btn.style.opacity = '0.5';
                }
            }
        });
    }

    async toggleAdvancedAnalysis(enabled) {
        if (!this.advancedFeaturesEnabled) {
            this.showNotification('Advanced analysis not available', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/update_options', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ advanced_analysis: enabled })
            });

            if (response.ok) {
                this.showNotification(`Advanced analysis ${enabled ? 'enabled' : 'disabled'}`, 'success');
            } else {
                throw new Error('Failed to toggle advanced analysis');
            }
        } catch (error) {
            this.showNotification(`Error: ${error.message}`, 'error');
        }
    }

    async uploadToCloud() {
        if (!this.cloudConnected) {
            this.showNotification('Cloud not configured', 'warning');
            return;
        }

        try {
            this.showNotification('Uploading to cloud...', 'info');
            const response = await fetch('/api/cloud_upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame_type: 'current' })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Upload successful', 'success');
                this.updateCloudStatus('Upload completed');
            } else {
                throw new Error(data.message || 'Upload failed');
            }
        } catch (error) {
            this.showNotification(`Upload error: ${error.message}`, 'error');
            this.updateCloudStatus('Upload failed');
        }
    }

    async viewCloudUploads() {
        try {
            const response = await fetch('/api/cloud_uploads');
            const data = await response.json();

            if (data.success && data.uploads.length > 0) {
                const uploadsList = data.uploads.slice(0, 5).map(upload => 
                    `• ${upload.filename} (${upload.timestamp})`
                ).join('\n');
                
                this.showNotification(`Recent uploads:\n${uploadsList}`, 'info');
            } else {
                this.showNotification('No recent uploads found', 'info');
            }
        } catch (error) {
            this.showNotification(`Error fetching uploads: ${error.message}`, 'error');
        }
    }

    async downloadModels() {
        try {
            this.showNotification('Starting model download...', 'info');
            const response = await fetch('/api/download_models', { method: 'POST' });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Models downloaded successfully', 'success');
            } else {
                throw new Error(data.message || 'Download failed');
            }
        } catch (error) {
            this.showNotification(`Download error: ${error.message}`, 'error');
        }
    }

    async exportData() {
        try {
            const response = await fetch('/api/export_data', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ format: 'json' })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `video_analysis_${Date.now()}.json`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification('Data exported successfully', 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            this.showNotification(`Export error: ${error.message}`, 'error');
        }
    }

    async checkSystemHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            this.updateSystemStatusUI(data);
            this.showNotification('Health check completed', 'success');
            
        } catch (error) {
            this.showNotification('Health check failed', 'error');
            // Set error states
            this.updateSystemStatusUI({
                status: 'error',
                advanced_analyzer_available: false,
                cloud_config_complete: false
            });
        }
    }

    updateCloudStatus(message) {
        const statusElement = document.getElementById('cloud-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    updateAdvancedMetrics(stats) {
        if (stats.advanced_analytics) {
            const analytics = stats.advanced_analytics;
            
            // Update quality score
            const qualityBar = document.getElementById('quality-score');
            if (qualityBar) {
                const score = analytics.quality_score || 0;
                qualityBar.style.width = `${score}%`;
                qualityBar.textContent = `${score}%`;
            }
            
            // Update object and face counts
            const objectsCount = document.getElementById('objects-count');
            const facesCount = document.getElementById('faces-count');
            const fpsCount = document.getElementById('fps-count');
            
            if (objectsCount) objectsCount.textContent = analytics.objects_detected || 0;
            if (facesCount) facesCount.textContent = analytics.faces_detected || 0;
            if (fpsCount) fpsCount.textContent = Math.round(stats.fps || 0);
        }
    }

    switchCamera(cameraIndex) {
        this.startCamera(cameraIndex);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.videoProcessor = new VideoProcessor();
});

// Export for global access
window.VideoProcessor = VideoProcessor;
