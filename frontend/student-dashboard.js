// ==================== CONFIGURATION ====================
const RESULTS_PER_PAGE = 20;

// ==================== STATE ====================
let currentPage = 0;
let allResults = [];
let filteredResults = [];

// ==================== DOM ELEMENTS ====================
const userNameEl = document.getElementById('userName');
const userRollNoEl = document.getElementById('userRollNo');
const userCollegeEl = document.getElementById('userCollege');
const welcomeNameEl = document.getElementById('welcomeName');
const userLabelEl = document.getElementById('userLabel');
const semesterSelect = document.getElementById('semesterSelect');
const resultsContainer = document.getElementById('resultsContainer');
const messageDiv = document.getElementById('message');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    // Check if logged in
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'student') {
        window.location.href = 'index.html';
        return;
    }
    
    // Display user info
    const userName = localStorage.getItem('user_name');
    const rollNo = localStorage.getItem('user_roll_no');
    const collegeCode = localStorage.getItem('college_code');
    
    userNameEl.textContent = userName;
    userRollNoEl.textContent = rollNo;
    userCollegeEl.textContent = collegeCode;
    welcomeNameEl.textContent = userName.split(' ')[0];  // First name only
    userLabelEl.textContent = `👨‍🎓 ${userName}`;
    
    // Load results
    
});

// ==================== FETCH RESULTS ====================
async function fetchResults() {
    const semester = semesterSelect.value;

    if (!semester) {
        showMessage(
            "Please select a semester first",
            "error"
        );
        return;
    }

    try {
        // Build query
        let query = '/api/results/me?limit=100';  // Get all results at once
        
        const response = await apiCall(query);

        console.log("Response object:", response);

        if (response) {
            console.log("Status:", response.status);

            const clone = response.clone();
            console.log("Body:", await clone.json());
        }
        
        if (!response) {
            showMessage('Session expired. Please login again.', 'error');
            setTimeout(() => {
                logout();
            }, 2000);
            return;
        }
        
        if (!response.ok) {
            if (response.status === 401) {
                logout();
                return;
            }
            const error = await response.json();
            showMessage(`Error: ${error.detail}`, 'error');
            return;
        }
        
        messageDiv.style.display = 'none';
        
        const data = await response.json();
        allResults = data.results || [];
        
        // Reset pagination and filter
        currentPage = 0;
        applyFilters();
        
    } catch (error) {
        console.error('Error fetching results:', error);
        showMessage(`Error: ${error.message}`, 'error');
    }
}

// ==================== APPLY SEMESTER FILTER ====================
function applyFilters() {
    const semester = semesterSelect.value;
    
    if (semester) {
        filteredResults = allResults.filter(r => r.semester === parseInt(semester));
    } else {
        filteredResults = allResults;
    }
    
    currentPage = 0;
    displayResults();
}

// ==================== HANDLE SEMESTER CHANGE ====================

// ==================== DISPLAY RESULTS ====================
function displayResults() {
    if (!filteredResults || filteredResults.length === 0) {
        resultsContainer.innerHTML = `
            <div class="no-results">
                <h4>No results found</h4>
                <p>Your results will appear here once they are published.</p>
            </div>
        `;
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredResults.length / RESULTS_PER_PAGE);
    const startIdx = currentPage * RESULTS_PER_PAGE;
    const endIdx = startIdx + RESULTS_PER_PAGE;
    const pageResults = filteredResults.slice(startIdx, endIdx);
    
    // Create table
    let html = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>Semester</th>
                    <th>Subject Code</th>
                    <th>Subject Name</th>
                    <th>Grade</th>
                    <th>Points</th>
                    <th>Credits</th>
                    <th>Credit Points</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    pageResults.forEach(result => {
        const pointsClass = result.points >= 5.0 ? 'pass' : 'fail';
        html += `
            <tr>
                <td>${result.semester}</td>
                <td>${result.subject_code}</td>
                <td>${result.subject_name}</td>
                <td class="grade">${result.grade}</td>
                <td class="points ${pointsClass}">${result.points.toFixed(1)}</td>
                <td>${result.credits.toFixed(1)}</td>
                <td>${result.credit_points.toFixed(1)}</td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    // Add pagination if needed
    if (totalPages > 1) {
        html += `
            <div class="pagination">
                <button onclick="previousPage()" ${currentPage === 0 ? 'disabled' : ''}>← Previous</button>
                <span class="page-info">Page ${currentPage + 1} of ${totalPages}</span>
                <button onclick="nextPage()" ${currentPage === totalPages - 1 ? 'disabled' : ''}>Next →</button>
            </div>
        `;
    }
    
    resultsContainer.innerHTML = html;
}

// ==================== PAGINATION ====================
function nextPage() {
    const totalPages = Math.ceil(filteredResults.length / RESULTS_PER_PAGE);
    if (currentPage < totalPages - 1) {
        currentPage++;
        displayResults();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function previousPage() {
    if (currentPage > 0) {
        currentPage--;
        displayResults();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}