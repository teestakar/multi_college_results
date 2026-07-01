const welcomeNameEl = document.getElementById('welcomeName');
const adminIdEl = document.getElementById('adminId');
const collegeNameEl = document.getElementById('collegeName');
const userLabelEl = document.getElementById('userLabel');

document.addEventListener('DOMContentLoaded', function() {
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'admin') {
        window.location.href = 'teacher-login.html';
        return;
    }
    
    const userName = localStorage.getItem('user_name');
    welcomeNameEl.textContent = userName ? userName.split(' ')[0] : 'Admin';
    userLabelEl.textContent = `👨‍💼 ${userName || 'Admin'}`;
    
    loadAdminProfile();
});

async function loadAdminProfile() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/teacher/me`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });
        
        if (!response.ok) throw new Error('Failed to load profile');
        
        const data = await response.json();
        adminIdEl.textContent = data.teacher_id || 'N/A';
        collegeNameEl.textContent = data.college_name || 'N/A';
        
    } catch (error) {
        console.error('Error:', error);
        logout();
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'teacher-login.html';
}