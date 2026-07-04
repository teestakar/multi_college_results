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

let chart = null;
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
        const data = await apiCall("/api/results/degrees");
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
        const data = await apiCall(`/api/results/branches?degree_id=${degreeId}`);
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

    document.getElementById("topStudentsContainer").innerHTML = "";

    document.getElementById("subjectFailuresContainer").innerHTML = "";

    if (chart) {
        chart.destroy();
        chart = null;
    }
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

        const data = await apiCall(url);

        renderStats(data);

    } catch(err){

      statsContainer.innerHTML = "";

      document.getElementById("topStudentsContainer").innerHTML = "";

      document.getElementById("subjectFailuresContainer").innerHTML = "";

      if(chart){
        chart.destroy();
        chart = null;
      }

      showMessage(err.message,"error");
    } finally {
        loadingDiv.style.display = "none";
    }
}

// ================= RENDER =================
function renderStats(data) {
    messageDiv.style.display = "none";
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
                <div class="stat-item">
                <h3>Lowest SGPA</h3>
                <div class="value">${data.lowest_sgpa}</div>
                </div>
            </div>
        </div>
    `;
    statsContainer.innerHTML += `
        <div class="stats-card">

        <h2>Result Summary</h2>

        <div class="stats-grid">

        <div class="stat-item">
        <h3>Passed</h3>
        <div class="value">${data.pass_count}</div>
        </div>

        <div class="stat-item">
        <h3>Failed</h3>
        <div class="value">${data.fail_count}</div>
        </div>

        <div class="stat-item">
        <h3>Pass with Backlog</h3>
        <div class="value">${data.pass_with_backlog}</div>
        </div>

        <div class="stat-item">
        <h3>Students with Backlogs</h3>
        <div class="value">${data.students_with_backlog}</div>
        </div>

        </div>

        </div>
    `;

    if (data.sgpa_distribution) {
        renderChart(data.sgpa_distribution);
    }
    
    if (data.top_10_students) {
        renderTopStudents(data.top_10_students);
    }

    renderSubjectFailures(data.subject_wise_failures);
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

    statsContainer.innerHTML += `
        <div class="stats-card">

        <h2>Extra Statistics</h2>

        <div class="stats-grid">

        <div class="stat-item">
        <h3>Average SGPA</h3>
        <div class="value">${data.avg_sgpa}</div>
        </div>

        <div class="stat-item">
        <h3>Highest SGPA</h3>
        <div class="value">${data.highest_sgpa}</div>
        </div>

        <div class="stat-item">
        <h3>Lowest SGPA</h3>
        <div class="value">${data.lowest_sgpa}</div>
        </div>

        <div class="stat-item">
        <h3>Pass with Backlogs</h3>
        <div class="value">${data.pass_with_backlog}</div>
        </div>

        <div class="stat-item">
        <h3>Students with Backlogs</h3>
        <div class="value">${data.with_backlog}</div>
        </div>

        </div>

        </div>
    `;

    if (data.sgpa_distribution) {
        renderChart(data.sgpa_distribution);
    }
    
    if (data.top_10_students) {
        renderTopStudents(data.top_10_students);
    }

    renderSubjectFailures(data.subject_wise_failures);
}

function renderChart(distribution){

    if(chart){
        chart.destroy();
    }

    const ctx = document
      .getElementById("sgpaChart")
      .getContext("2d");

    chart=new Chart(ctx,{

        type:"bar",

        data:{
            labels:Object.keys(distribution),

            datasets:[{

                label:"Students",

                data:Object.values(distribution)

            }]
        },

        options:{

          responsive:true,

          plugins:{
              title:{
                  display:true,
                  text:"SGPA Distribution"
              },
              legend:{
                  display:false
              }
          },

          scales:{
              y:{
                  beginAtZero:true
              }
          }
        }

    });

}



function renderTopStudents(students){

    const div=document.getElementById("topStudentsContainer");

    if(!students || students.length===0){

        div.innerHTML="";
        return;
    }

    let html=`

<div class="stats-card">

<h2>Top 10 Students</h2>

<table>

<tr>

<th>Rank</th>
<th>Roll No</th>
<th>SGPA</th>
<th>Status</th>

</tr>
`;

students.forEach((s,i)=>{

html+=`

<tr>

<td>${i+1}</td>

<td>${s.roll_no}</td>

<td>${s.sgpa}</td>

<td>${s.status}</td>

</tr>

`;

});

html+=`

</table>

</div>
`;

div.innerHTML=html;

}



// ================= MESSAGE =================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = "block";
}


function renderSubjectFailures(subjects){

    const div = document.getElementById("subjectFailuresContainer");

    if(!subjects || Object.keys(subjects).length===0){
        div.innerHTML="";
        return;
    }

    let html=`
    <div class="stats-card">

    <h2>Subject-wise Failures</h2>

    <table>

    <tr>
        <th>Subject</th>
        <th>Failures</th>
    </tr>
    `;

    Object.entries(subjects).forEach(([subject,count])=>{

        html+=`
        <tr>
            <td>${subject}</td>
            <td>${count}</td>
        </tr>
        `;

    });

    html+=`
    </table>
    </div>
    `;

    div.innerHTML=html;
}