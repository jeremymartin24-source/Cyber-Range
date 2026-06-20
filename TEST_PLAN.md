# CyberOps Range — Test Plan

Check off each item as you verify it. Start the stack with `docker compose up` before beginning.

**Seed credentials:**
| Role | Email | Password |
|---|---|---|
| Admin | admin@bmg.example.com | Admin1234! |
| Instructor | instructor@bmg.example.com | Instructor1234! |
| Student | alice@bmg.example.com | Student1234! |
| Student | bob@bmg.example.com | Student1234! |

---

## 1. Authentication

- [x] Visit http://localhost:3000 — should redirect to `/login`
- [x] Submit with wrong password — should show `Invalid credentials` error (not a crash)
- [x] Submit with empty fields — browser should block submission (required fields)
- [x] Log in as Admin — should land on `/dashboard`
- [x] Refresh the page while logged in — should stay on dashboard (session persists)
- [x] Click **Sign out** — should redirect to `/login`
- [x] Try visiting http://localhost:3000/dashboard while logged out — should redirect to `/login`

---

## 2. Admin Role

Log in as `admin@bmg.example.com`.

### Sidebar
- [x] Sidebar shows: Dashboard, Incidents, Alerts, Scenarios, Campaigns, Courses, Users
- [x] Footer shows **System Admin** with role label `admin`

### Dashboard
- [ ] Page loads without errors
    - Still getting Hydration error
- [x] Four stat cards visible: Open Incidents, Total Incidents, Active Runs, Campaign Runs
- [x] "No active incidents" and "No active runs" placeholders visible (expected — nothing running yet)

### Users (`/admin/users`)
- [x] Table loads with 4 rows (admin, instructor, alice, bob)
      - 6 users are present. admin, instructor, and 4 other users
- [x] Roles are color-coded (admin=red, instructor=yellow, student=blue)
- [x] All 4 users show status `active`

### Courses (`/courses`)
- [ ] "BMG Foundations" course appears in the list
      - Course appears but is "Introduction to Cybersecurity Operations" instead
- [x] Click the course — detail page loads showing enrollment section
      - the buton said "manage" not de

### Scenarios (`/scenarios`)
- [x] Seeded scenarios appear in the list
- [x] Each scenario shows difficulty badge and estimated duration

### Campaigns (`/campaigns`)
- [ ] At least one seeded campaign appears
      - Selecting campaign takes me to login screen

### Incidents (`/incidents`)
- [x] Page loads (empty list is fine — no incidents created yet)

### Alerts (`/alerts`)
- [x] Page loads (empty list is fine)

---

## 3. Instructor Role

Sign out, then log in as `instructor@bmg.example.com`.

### Sidebar
- [ ] Sidebar shows: Dashboard, Incidents, Alerts, Scenarios, Campaigns, Courses
- [ ] **Users link is NOT visible** (admin-only)
- [ ] Footer shows **Jane Smith** with role label `instructor`

### Courses
- [ ] "BMG Foundations" course visible
- [ ] Click the course → detail page shows **Manage** button or enrollment controls
- [ ] Enroll `alice@bmg.example.com` as a student
- [ ] Enroll `bob@bmg.example.com` as a student
- [ ] Both students now appear in the enrollment list

### Scenarios & Campaigns
- [ ] Both pages load and show seeded content (same as admin view)

---

## 4. Student Role

Sign out, then log in as `alice@bmg.example.com`.

### Sidebar
- [ ] Sidebar shows: Dashboard, Incidents, Alerts, Courses
- [ ] **Scenarios link is NOT visible**
- [ ] **Campaigns link is NOT visible**
- [ ] **Users link is NOT visible**
- [ ] Footer shows **Alice Johnson** with role label `student`

### Courses
- [ ] "BMG Foundations" course is visible (alice was enrolled above)
- [ ] Course detail page loads
- [ ] **Manage/enrollment controls are NOT visible** (student view only)

### Dashboard
- [ ] Loads without errors

---

## 5. Backend API

Open a second terminal and run these directly against the API.

```powershell
# Health check — should return {"status":"ok","environment":"development"}
curl http://localhost:8000/api/health

# Login — should return 200 and set a cookie
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@bmg.example.com","password":"Admin1234!"}'

# Get current user — should return admin user object
curl -b cookies.txt http://localhost:8000/api/v1/auth/me

# List users — should return paginated response with 4 users
curl -b cookies.txt http://localhost:8000/api/v1/users

# List courses
curl -b cookies.txt http://localhost:8000/api/v1/courses
```

- [ ] Health check returns `{"status":"ok"}`
- [ ] Login returns 200 (no error)
- [ ] `/auth/me` returns correct admin user
- [ ] `/users` returns `{"items":[...],"total":4,...}`
- [ ] `/courses` returns array with BMG Foundations course

---

## 6. Role Enforcement (Security)

These should be **blocked**, not just hidden in the UI.

```powershell
# Log in as student and save cookie
curl -c student_cookies.txt -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"alice@bmg.example.com","password":"Student1234!"}'

# Try to list all users as a student — should return 403
curl -b student_cookies.txt http://localhost:8000/api/v1/users

# Try to access a scenario as a student — should return 403
curl -b student_cookies.txt http://localhost:8000/api/v1/scenarios
```

- [ ] Student cannot list users (403 Forbidden)
- [ ] Student cannot list scenarios (403 Forbidden)
- [ ] Unauthenticated request to `/auth/me` returns 401

---

## 7. Session Expiry

- [ ] Log in, note the time
- [ ] Leave the browser idle for 15+ minutes
- [ ] Refresh the page — should redirect to `/login` (JWT expires after 15 min by default)

---

## What to Record

If anything above fails, note:
- Which test step
- What you expected
- What actually happened (error message, wrong redirect, blank page, etc.)

Open an issue or drop the details in the chat.
