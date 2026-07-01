const pageTitle = document.getElementById('pageTitle');
const backBtn = document.getElementById('backBtn');
const degreeSelect = document.getElementById('degreeSelect');
const branchSelect = document.getElementById('branchSelect');
const branchGroup = document.getElementById('branchGroup');
const yearSelect = document.getElementById('yearSelect');
const semesterSelect = document.getElementById('semesterSelect');
const statsContainer = document.getElementById('statsContainer');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

let userRole = 'teacher';
let degreesList = [];

document.addEventListener('DOMContentLoaded', function () {
    const token = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    const role = localStorage.getItem('user_role');

    // ================= SAFE AUTH GUARD =================
    if (!token) {
        window.location.href = 'teacher-login.html';
        return;
    }

    // teacher OR admin allowed
    if (userType !== 'teacher' && userType !== 'admin') {
        window.location.href = 'teacher-login.html';
        return;
    }

    userRole = role || userType;

    setupUI();
    loadDegrees();
});

// ================= UI SETUP =================
function setupUI() {
    if (userRole === 'admin') {
        pageTitle.textContent = '📊 College Statistics';
        backBtn.href = 'admin-dashboard.html';
        branchGroup.style.display = 'flex';
    } else {
        pageTitle.textContent = '📊 My Upload Statistics';
        backBtn.href = 'teacher-dashboard.html';
        branchGroup.style.display = 'none';
    }
}

// ================= LOAD DEGREES =================
async function loadDegrees() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/results/degrees`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        const data = await res.json();
        degreesList = Array.isArray(data) ? data : [];

        degreeSelect.innerHTML = `<option value="">Select Degree</option>`;
        degreesList.forEach(d => {
            degreeSelect.innerHTML += `<option value="${d.id}">${d.name}</option>`;
        });

    } catch (err) {
        showMessage("Failed to load degrees", "error");
    }
}

// ================= DEGREE CHANGE =================
async function onDegreeChange() {
    const degreeId = degreeSelect.value;

    if (!degreeId) return;

    try {
        const res = await fetch(`${API_BASE_URL}/api/results/branches?degree_id=${degreeId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        const data = await res.json();
        const branches = Array.isArray(data) ? data : [];

        branchSelect.innerHTML = `<option value="all">All Branches</option>`;

        branches.forEach(b => {
            branchSelect.innerHTML += `<option value="${b.id}">${b.name}</option>`;
        });

    } catch (err) {
        showMessage("Failed to load branches", "error");
    }
}

// ================= LOAD STATS =================
async function loadStatistics() {
    const degreeId = degreeSelect.value;
    const branchId = branchSelect.value === "all" ? null : branchSelect.value;
    const year = yearSelect.value;
    const semester = semesterSelect.value;

    if (!degreeId || !year || !semester) {
        showMessage("Select all required filters", "error");
        return;
    }

    loadingDiv.style.display = "block";
    statsContainer.innerHTML = "";

    try {
        let url = "";

        // ================= ROLE BASED ENDPOINT =================
        if (userRole === "admin") {
            url = `/api/results/statistics?degree_id=${degreeId}&year=${year}&semester=${semester}`;
            if (branchId) url += `&branch_id=${branchId}`;
        } else {
            url = `/api/results/statistics/my-uploads?degree_id=${degreeId}&year=${year}&semester=${semester}`;
        }

        const res = await fetch(`${API_BASE_URL}${url}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || "Failed");

        renderStats(data);

    } catch (err) {
        showMessage(err.message, "error");
    } finally {
        loadingDiv.style.display = "none";
    }
}

// ================= RENDER =================
function renderStats(data) {
    if (userRole === "admin") renderAdmin(data);
    else renderTeacher(data);
}

// ================= ADMIN UI =================
function renderAdmin(data) {
    statsContainer.innerHTML = `
        <div class="stats-card">
            <h2>College Overview</h2>
            <div class="stats-grid">
                <div class="stat-item"><h3>Total Students</h3><div class="value">${data.total_students}</div></div>
                <div class="stat-item"><h3>Pass %</h3><div class="value">${data.pass_percentage}%</div></div>
                <div class="stat-item"><h3>Highest SGPA</h3><div class="value">${data.highest_sgpa}</div></div>
                <div class="stat-item"><h3>Avg SGPA</h3><div class="value">${data.average_sgpa}</div></div>
            </div>
        </div>
    `;
}

// ================= TEACHER UI =================
function renderTeacher(data) {
    statsContainer.innerHTML = `
        <div class="stats-card">
            <h2>My Upload Summary</h2>
            <div class="stats-grid">
                <div class="stat-item"><h3>Total</h3><div class="value">${data.total_students}</div></div>
                <div class="stat-item"><h3>Pass</h3><div class="value">${data.pass_count}</div></div>
                <div class="stat-item"><h3>Fail</h3><div class="value">${data.fail_count}</div></div>
                <div class="stat-item"><h3>Pass %</h3><div class="value">${data.pass_rate}%</div></div>
            </div>
        </div>
    `;
}

// ================= MESSAGE =================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = "block";
}