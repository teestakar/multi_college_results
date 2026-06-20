// ==================== DOM ELEMENTS ====================
const csvUploadForm = document.getElementById('csvUploadForm');
const csvFile = document.getElementById('csvFile');
const uploadArea = document.getElementById('uploadArea');
const fileName = document.getElementById('fileName');
const uploadBtn = document.getElementById('uploadBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('CSV upload page loaded');
    
    // Check if logged in as teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
});

// ==================== FILE UPLOAD HANDLERS ====================
uploadArea.addEventListener('click', () => csvFile.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        csvFile.files = files;
        displayFileName(files[0].name);
    }
});

csvFile.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        displayFileName(e.target.files[0].name);
    }
});

function displayFileName(name) {
    fileName.textContent = `✅ Selected: ${name}`;
}

// ==================== FORM SUBMIT ====================
csvUploadForm.addEventListener('submit', handleUpload);

async function handleUpload(event) {
    event.preventDefault();
    
    const file = csvFile.files[0];
    
    
    
    if (!file) {
        showMessage('❌ Please select a CSV file', 'error');
        return;
    }
    
    if (!file.name.endsWith('.csv')) {
        showMessage('❌ Please upload a CSV file', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    uploadBtn.disabled = true;
    
    try {
        console.log('Uploading CSV:', file.name);
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('file', file);
        
        // Get token for Authorization header
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(`${API_BASE_URL}/api/results/upload-csv`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        console.log('Upload response status:', response.status);
        
        const data = await response.json();
        console.log('Upload response:', data);
        
        if (response.ok) {
            showMessage(`✅ ${data.message}`, 'success');
            
            // Clear form
            csvUploadForm.reset();
            fileName.textContent = '';
            
            // Show summary
            if (data.success_count) {
                showMessage(`✅ ${data.success_count} records uploaded successfully!`, 'info');
            }
            if (data.error_count) {
                showMessage(`⚠️ ${data.error_count} records had errors`, 'error');
            }
            
        } else {
            const errorMsg = data.detail || data.message || 'Upload failed';
            showMessage(`❌ ${errorMsg}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showMessage(`❌ Error: ${error.message}`, 'error');
    } finally {
        loadingDiv.style.display = 'none';
        uploadBtn.disabled = false;
    }
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}