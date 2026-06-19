// ==================== DOM ELEMENTS ====================
const welcomeNameEl = document.getElementById('welcomeName');
const teacherIdEl = document.getElementById('teacherId');
const collegeIdEl = document.getElementById('collegeId');
const collegeNameEl = document.getElementById('collegeName');
const roleEl = document.getElementById('role');
const userLabelEl = document.getElementById('userLabel');
const adminCardEl = document.getElementById('adminCard');
const messageDiv = document.getElementById('message');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    // Check if logged in as teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
    
    // Display teacher info
  //  const teacherId = localStorage.getItem('teacher_id');
    const userName = localStorage.getItem('user_name');
    //const collegeCode = localStorage.getItem('college_code');
   // const role = localStorage.getItem('teacher_role');
    
    welcomeNameEl.textContent = userName ? userName.split(' ')[0] : 'Teacher';
    //teacherIdEl.textContent = teacherId || 'Unknown';
    //collegeIdEl.textContent = collegeCode || 'Unknown';
  //  roleEl.textContent = role ? (role === 'admin' ? 'Admin' : 'Teacher') : 'Teacher';
    userLabelEl.textContent = `👨‍🏫 ${userName || 'Teacher'}`;

    loadTeacherProfile();
    
    // Show admin card if user is admin
   // if (role === 'admin') {
     //   adminCardEl.style.display = 'block';
    //}
});

// ==================== Teacher info fetch ====================
async function loadTeacherProfile() {
    try {
        const response = await apiCall('/api/auth/teacher/me');

        if (!response || !response.ok) {
            logout();
            return;
        }

        const data = await response.json();

        teacherIdEl.textContent = data.teacher_id;
        roleEl.textContent = data.role;
        collegeNameEl.textContent = data.college_name;
        collegeIdEl.textContent = data.college_id;

        if (data.role === 'admin') {
            adminCardEl.style.display = 'block';
        }

    } catch (error) {
        console.error(error);
        logout();
    }
}



// ==================== LOGOUT ====================
function logout() {
    localStorage.clear();
    window.location.href = 'teacher-login.html';
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}