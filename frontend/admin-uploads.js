const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');
const uploadsListDiv = document.getElementById('uploadsList');

document.addEventListener('DOMContentLoaded', loadUploads);

async function loadUploads() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/uploads/pending`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load uploads');
        
        const data = await response.json();
        console.log('Uploads:', data);
        
        loadingDiv.style.display = 'none';
        
        if (!data.uploads || data.uploads.length === 0) {
            uploadsListDiv.innerHTML = '<p style="color: #666; text-align: center;">No pending uploads</p>';
            return;
        }
        
        uploadsListDiv.innerHTML = data.uploads.map(upload => `
            <div class="upload-item">
                <div class="upload-info">
                    <p><strong>File:</strong> ${upload.file_name}</p>
                    <p><strong>Teacher:</strong> ${upload.teacher_name}</p>
                    <p><strong>Marks Count:</strong> ${upload.marks_count}</p>
                    <p><strong>Uploaded:</strong> ${new Date(upload.uploaded_at).toLocaleString()}</p>
                </div>
                <div class="upload-actions">
                    <button class="btn btn-download" onclick="downloadCSV('${upload.upload_id}')">Download</button>
                    <button class="btn btn-approve" onclick="approveUpload('${upload.upload_id}')">Approve</button>
                    <button class="btn btn-reject" onclick="rejectUpload('${upload.upload_id}')">Reject</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error:', error);
        showMessage(`❌ ${error.message}`, 'error');
        loadingDiv.style.display = 'none';
    }
}

async function downloadCSV(uploadId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/uploads/${uploadId}/download`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'upload.csv';
        a.click();
        
    } catch (error) {
        showMessage(`❌ ${error.message}`, 'error');
    }
}

async function approveUpload(uploadId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/uploads/${uploadId}/approve`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) throw new Error('Approval failed');
        
        showMessage('✅ Upload approved!', 'success');
        setTimeout(loadUploads, 2000);
        
    } catch (error) {
        showMessage(`❌ ${error.message}`, 'error');
    }
}

async function rejectUpload(uploadId) {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/uploads/${uploadId}/reject`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        });
        
        if (!response.ok) throw new Error('Rejection failed');
        
        showMessage('✅ Upload rejected!', 'success');
        setTimeout(loadUploads, 2000);
        
    } catch (error) {
        showMessage(`❌ ${error.message}`, 'error');
    }
}

function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}