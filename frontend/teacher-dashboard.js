// ==================== DOM ELEMENTS ====================
const welcomeNameEl = document.getElementById('welcomeName');
const teacherIdEl = document.getElementById('teacherId');
const collegeIdEl = document.getElementById('collegeId');
const collegeNameEl = document.getElementById('collegeName');
const roleEl = document.getElementById('role');
const userLabelEl = document.getElementById('userLabel');
const studentRegisterCardEl = document.getElementById('studentRegisterCard');
const teacherRegisterCardEl = document.getElementById('teacherRegisterCard');
const messageDiv = document.getElementById('message');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Teacher dashboard loaded');
    
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
    
    const userName = localStorage.getItem('user_name');
    welcomeNameEl.textContent = userName ? userName.split(' ')[0] : 'Teacher';
    userLabelEl.textContent = `👨‍🏫 ${userName || 'Teacher'}`;
    
    loadTeacherProfile();
});

// ==================== LOAD TEACHER PROFILE ====================
async function loadTeacherProfile() {
    try {
        console.log('Loading profile...');
        
        const data = await apiCall("/api/auth/teacher/me");
        console.log('Profile:', data);
        
        // Update UI
        teacherIdEl.textContent = data.teacher_id || 'N/A';
        roleEl.textContent = data.role === 'admin' ? 'Admin' : 'Teacher';
        collegeNameEl.textContent = data.college_name || 'N/A';
        collegeIdEl.textContent = data.college_id || 'N/A';
        
        // Show admin-only cards if admin
        if (data.role === 'admin') {
            studentRegisterCardEl.style.display = 'block';
            teacherRegisterCardEl.style.display = 'block';
        }
    
    } catch (error) {
        console.error('Profile load error:', error);
        logout();
    }
}

// ==================== LOGOUT ====================
function logout() {
    localStorage.clear();
    window.location.href = 'teacher-login.html';
}